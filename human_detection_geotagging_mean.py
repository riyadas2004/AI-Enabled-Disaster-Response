import os
os.environ["ULTRALYTICS_OFFLINE"] = "1"

import cv2
import threading
import time
import csv
import math
from pymavlink import mavutil
from ultralytics import YOLO

RTSP_URL = "rtsp://192.168.144.25:8554/main.264"
MODEL_PATH = "yolov8n.pt"
CSV_FILE = "survivors_final.csv"
KML_FILE = "survivors_final.kml"

FOV_X = 81
FOV_Y = 60

FRAME_W = 640
FRAME_H = 480

state_lock = threading.Lock()

drone = {
    "lat": None,
    "lon": None,
    "alt": None,
    "yaw": 0,
    "pitch": 0,
    "roll": 0,
    "cam_pitch": -90
}

def mavlink_thread():
    try:
        master = mavutil.mavlink_connection("COM1", baud=115200)
        master.wait_heartbeat()
    except:
        return

    while True:
        try:
            msg = master.recv_match(
                type=["GLOBAL_POSITION_INT", "ATTITUDE"],
                blocking=True
            )

            if msg.get_type() == "GLOBAL_POSITION_INT":
                with state_lock:
                    drone["lat"] = msg.lat / 1e7
                    drone["lon"] = msg.lon / 1e7
                    drone["alt"] = msg.relative_alt / 1000.0

            elif msg.get_type() == "ATTITUDE":
                with state_lock:
                    drone["yaw"] = math.degrees(msg.yaw)
                    drone["pitch"] = math.degrees(msg.pitch)
                    drone["roll"] = math.degrees(msg.roll)

        except:
            pass

def get_drone():
    with state_lock:
        return drone.copy()

class RTSP:
    def __init__(self, url):
        self.cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
        self.frame = None
        threading.Thread(target=self.update, daemon=True).start()

    def update(self):
        while True:
            ret, frame = self.cap.read()
            if ret:
                self.frame = frame

    def read(self):
        return None if self.frame is None else self.frame.copy()

trackers = {}
global_id = 1
MAX_LOST_TIME = 3
logged_ids = set()

def get_id(cx, cy):
    global global_id
    best_id = None
    min_dist = 9999

    for tid in list(trackers.keys()):
        px, py, last_seen = trackers[tid]

        if time.time() - last_seen > MAX_LOST_TIME:
            del trackers[tid]
            continue

        dist = math.hypot(cx - px, cy - py)

        if dist < 60 and dist < min_dist:
            min_dist = dist
            best_id = tid

    if best_id is not None:
        trackers[best_id] = (cx, cy, time.time())
        return best_id

    trackers[global_id] = (cx, cy, time.time())
    global_id += 1
    return global_id - 1

def pixel_to_gps(cx, cy, d):
    lat = d["lat"]
    lon = d["lon"]
    alt = d["alt"]
    yaw = d["yaw"]
    cam_pitch = d["cam_pitch"]

    fov_x = math.radians(FOV_X)
    fov_y = math.radians(FOV_Y)

    dx = cx - FRAME_W / 2
    dy = cy - FRAME_H / 2

    angle_x = (dx / FRAME_W) * fov_x
    angle_y = (dy / FRAME_H) * fov_y

    total_pitch = math.radians(cam_pitch) + angle_y

    ground_dist = alt * math.tan(-total_pitch)

    offset_x = ground_dist * math.tan(angle_x)
    offset_y = ground_dist

    yaw_rad = math.radians(yaw)

    north = offset_y * math.cos(yaw_rad) - offset_x * math.sin(yaw_rad)
    east  = offset_y * math.sin(yaw_rad) + offset_x * math.cos(yaw_rad)

    dlat = north / 111111
    dlon = east / (111111 * math.cos(math.radians(lat)))

    return lat + dlat, lon + dlon

def append_csv(pid, lat, lon):
    file_exists = os.path.exists(CSV_FILE)
    with open(CSV_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["ID", "Latitude", "Longitude"])
        writer.writerow([pid, lat, lon])

def write_kml():
    if not os.path.exists(CSV_FILE):
        return

    with open(KML_FILE, "w") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<kml xmlns="http://www.opengis.net/kml/2.2">\n<Document>\n')

        with open(CSV_FILE, "r") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                f.write(f"""
<Placemark>
<name>ID {row['ID']}</name>
<Point>
<coordinates>{row['Longitude']},{row['Latitude']},0</coordinates>
</Point>
</Placemark>
""")

        f.write('</Document>\n</kml>')

def main():
    threading.Thread(target=mavlink_thread, daemon=True).start()

    model = YOLO(MODEL_PATH)
    stream = RTSP(RTSP_URL)

    cv2.namedWindow("Detection", cv2.WINDOW_NORMAL)

    while True:
        frame = stream.read()
        if frame is None:
            continue

        frame = cv2.resize(frame, (FRAME_W, FRAME_H))

        results = model.predict(frame, conf=0.6, classes=[0], verbose=False)

        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])

                cx = (x1 + x2) // 2
                cy = (y1 + y2) // 2

                pid = get_id(cx, cy)

                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 255), 2)
                cv2.putText(frame, f"ID {pid}", (x1, y1 - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

                d = get_drone()

                if d["lat"] is not None and pid not in logged_ids:
                    lat, lon = pixel_to_gps(cx, cy, d)
                    append_csv(pid, round(lat, 6), round(lon, 6))
                    logged_ids.add(pid)

        cv2.imshow("Detection", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            write_kml()
            break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()

def start_detection():
    main()
