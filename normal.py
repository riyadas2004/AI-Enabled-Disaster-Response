import cv2
from threading import Thread
import time

class RTSPVideoStream:
    def __init__(self, src):
        self.stream = cv2.VideoCapture(src, cv2.CAP_FFMPEG)  # use FFmpeg backend for better RTSP handling
        if not self.stream.isOpened():
            raise Exception(f"❌ Unable to open RTSP stream: {src}")
        self.ret, self.frame = self.stream.read()
        self.stopped = False
        self.last_read_time = time.time()

    def start(self):
        Thread(target=self.update, daemon=True).start()
        return self

    def update(self):
        while not self.stopped:
            if self.stream.isOpened():
                self.ret, frame = self.stream.read()
                if self.ret:
                    self.frame = frame
                    self.last_read_time = time.time()
                else:
                    # handle stream drop — try reconnecting
                    if time.time() - self.last_read_time > 3:
                        print("⚠️ Stream lost. Attempting to reconnect...")
                        self.stream.release()
                        time.sleep(2)
                        self.stream = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
            else:
                print("⚠️ Stream not open, retrying...")
                time.sleep(2)
                self.stream = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)

    def read(self):
        return self.frame if self.ret else None

    def stop(self):
        self.stopped = True
        self.stream.release()


# Your RTSP stream URL
rtsp_url = "rtsp://192.168.144.25:8554/main.264"

# Start threaded stream
try:
    vs = RTSPVideoStream(rtsp_url).start()
    print("✅ RTSP stream started successfully")
except Exception as e:
    print(e)
    exit()

# Display the video
while True:
    frame = vs.read()
    if frame is None:
        continue

    cv2.imshow("RTSP Stream (Threaded)", frame)

    # Press 'q' to exit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

vs.stop()
cv2.destroyAllWindows()
