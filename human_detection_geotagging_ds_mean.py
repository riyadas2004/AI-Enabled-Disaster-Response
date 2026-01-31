# ================= OFFLINE MODE (MUST BE FIRST) =================
import os
os.environ["ULTRALYTICS_OFFLINE"] = "1"

# ================= IMPORTS =================
import cv2
import threading
import time
import math
import csv
from pymavlink import mavutil
from ultralytics import YOLO

# ================= CONFIG =================
RTSP_URL = "rtsp://192.168.144.25:8554/main.264"

MAVLINK_DEVICE = "COM11"
MAVLINK_BAUD = 115200

YOLO_MODEL = r"./yolo11s.pt"   # <-- YOUR TRAINED MODEL
CONF_THRESHOLD = 0.4

MAX_PERSONS = 10
MATCH_DIST_PX = 80
PERSON_TIMEOUT = 1.0
GPS_SAMPLES_REQUIRED = 5

CSV_FILE = "persons_final_mean_ds.csv"
KML_FILE = "persons_final_mean_ds.kml"

CAMERA_HFOV = 81.0
CAMERA_DIAGFOV = 93.0
CAMERA_PITCH_DEG = -90.0   # camera pointing straight down

# ================= SANITY CHECK =================
if not os.path.isfile(YOLO_MODEL):
    raise RuntimeError(f"YOLO model not found: {YOLO_MODEL}")

# ================= FOV =================
def compute_vfov(hfov, diag):
    h = math.radians(hfov)
    d = math.radians(diag)
    return math.degrees(
        2 * math.atan(math.sqrt(max(0, math.tan(d/2)**2 - math.tan(h/2)**2)))
    )

CAMERA_VFOV = compute_vfov(CAMERA_HFOV, CAMERA_DIAGFOV)

# ================= DRONE STATE =================
state_lock = threading.Lock()
drone = {"lat": None, "lon": None, "alt": None, "yaw": None}

def mavlink_thread():
    master = mavutil.mavlink_connection(MAVLINK_DEVICE, baud=MAVLINK_BAUD)
    master.wait_heartbeat()
    print("[MAVLINK] Connected")

    while True:
        msg = master.recv_match(type=["GLOBAL_POSITION_INT", "ATTITUDE"], blocking=True)
        if not msg:
            continue

        with state_lock:
            if msg.get_type() == "GLOBAL_POSITION_INT":
                drone["lat"] = msg.lat / 1e7
                drone["lon"] = msg.lon / 1e7
                drone["alt"] = msg.relative_alt / 1000.0
            elif msg.get_type() == "ATTITUDE":
                drone["yaw"] = msg.yaw

def get_drone():
    with state_lock:
        return drone.copy()

# ================= RTSP VIDEO =================
class RTSP:
    def __init__(self, url):
        self.cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.frame = None
        self.lock = threading.Lock()
        threading.Thread(target=self.update, daemon=True).start()

    def update(self):
        while True:
            ret, frame = self.cap.read()
            if ret:
                with self.lock:
                    self.frame = frame
            else:
                time.sleep(0.01)

    def read(self):
        with self.lock:
            return None if self.frame is None else self.frame.copy()

# ================= GEO =================
def pixel_to_angles(cx, cy, w, h):
    ax = (cx - w / 2) / (w / 2) * (CAMERA_HFOV / 2)
    ay = (h / 2 - cy) / (h / 2) * (CAMERA_VFOV / 2)
    return math.radians(ax), math.radians(ay)

def meters_to_gps(lat, lon, east, north):
    return (
        lat + north / 111320,
        lon + east / (111320 * math.cos(math.radians(lat)))
    )

def estimate_person(d, cx, cy, w, h):
    if None in d.values():
        return None, None

    ax, ay = pixel_to_angles(cx, cy, w, h)
    pitch = math.radians(CAMERA_PITCH_DEG)

    vx, vy, vz = math.tan(ax), math.tan(ay), 1.0
    mag = math.sqrt(vx*vx + vy*vy + vz*vz)
    vx, vy, vz = vx/mag, vy/mag, vz/mag

    vy2 = vy * math.cos(pitch) + vz * math.sin(pitch)
    vz2 = -vy * math.sin(pitch) + vz * math.cos(pitch)

    east = vx * math.cos(d["yaw"]) - vy2 * math.sin(d["yaw"])
    north = vx * math.sin(d["yaw"]) + vy2 * math.cos(d["yaw"])

    if vz2 >= 0:
        return None, None

    t = d["alt"] / (-vz2)
    return meters_to_gps(d["lat"], d["lon"], east * t, north * t)

# ================= PERSON STORAGE =================
active_persons = {}
logged_persons = {}
next_id = 1
persons_lock = threading.Lock()

# ================= CSV + KML =================
def write_csv_kml():
    with open(CSV_FILE, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["PersonID", "Latitude", "Longitude"])
        for p in logged_persons.values():
            w.writerow([p["id"], p["lat"], p["lon"]])

    with open(KML_FILE, "w") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<kml xmlns="http://www.opengis.net/kml/2.2"><Document>\n')
        for p in logged_persons.values():
            f.write(
                f"<Placemark><name>Person {p['id']}</name>"
                f"<Point><coordinates>{p['lon']},{p['lat']},0</coordinates></Point>"
                f"</Placemark>\n"
            )
        f.write('</Document></kml>')

# ================= MAIN =================
def main():
    global next_id

    threading.Thread(target=mavlink_thread, daemon=True).start()
    model = YOLO(YOLO_MODEL)
    stream = RTSP(RTSP_URL)

    while True:
        frame = stream.read()
        if frame is None:
            continue

        h, w = frame.shape[:2]
        d = get_drone()
        now = time.time()

        results = model(frame, verbose=False)
        detections = []

        for r in results:
            for b in r.boxes:
                if int(b.cls[0]) == 0 and float(b.conf[0]) >= CONF_THRESHOLD:
                    detections.append(tuple(map(int, b.xyxy[0])))

        with persons_lock:
            for p in active_persons.values():
                p["seen"] = False

            for x1, y1, x2, y2 in detections:
                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                match = None

                for p in active_persons.values():
                    if math.hypot(cx - p["cx"], cy - p["cy"]) < MATCH_DIST_PX:
                        match = p
                        break

                if match:
                    match.update({"cx": cx, "cy": cy, "bbox": (x1, y1, x2, y2), "seen": True, "t": now})

                    if not match["gps_locked"]:
                        lat, lon = estimate_person(d, cx, cy, w, h)
                        if lat:
                            match["gps_samples"].append((lat, lon))
                            if len(match["gps_samples"]) == GPS_SAMPLES_REQUIRED:
                                lats = [x[0] for x in match["gps_samples"]]
                                lons = [x[1] for x in match["gps_samples"]]
                                logged_persons[match["id"]] = {
                                    "id": match["id"],
                                    "lat": sum(lats)/len(lats),
                                    "lon": sum(lons)/len(lons)
                                }
                                match["gps_locked"] = True
                                write_csv_kml()

                elif next_id <= MAX_PERSONS:
                    lat, lon = estimate_person(d, cx, cy, w, h)
                    if lat:
                        active_persons[next_id] = {
                            "id": next_id,
                            "cx": cx,
                            "cy": cy,
                            "bbox": (x1, y1, x2, y2),
                            "gps_samples": [(lat, lon)],
                            "gps_locked": False,
                            "seen": True,
                            "t": now
                        }
                        next_id += 1

            for pid in list(active_persons.keys()):
                if not active_persons[pid]["seen"] and now - active_persons[pid]["t"] > PERSON_TIMEOUT:
                    del active_persons[pid]

        for p in active_persons.values():
            x1, y1, x2, y2 = p["bbox"]
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, f"Person {p['id']}", (x1, y1 - 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        if d["lat"]:
            cv2.putText(frame,
                        f"DRONE {d['lat']:.6f},{d['lon']:.6f} ALT {d['alt']:.1f}m",
                        (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        cv2.imshow("Survivor Detection", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cv2.destroyAllWindows()

# ================= ENTRY =================
if __name__ == "__main__":
    main()