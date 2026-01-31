import cv2
from threading import Thread
import time

class RTSPVideoStream:
    def __init__(self, src):
        self.src = src
        self.stream = cv2.VideoCapture(src, cv2.CAP_FFMPEG)
        self.ret, self.frame = self.stream.read()
        self.stopped = False
        self.last_read_time = time.time()

    def start(self):
        Thread(target=self.update, daemon=True).start()
        return self

    def update(self):
        while True:
            if self.stopped:
                break

            if self.stream.isOpened():
                ret, frame = self.stream.read()

                if ret:
                    self.ret = True
                    self.frame = frame
                    self.last_read_time = time.time()
                else:
                    if time.time() - self.last_read_time > 2:
                        self.stream.release()
                        time.sleep(1)
                        self.stream = cv2.VideoCapture(self.src, cv2.CAP_FFMPEG)
            else:
                time.sleep(1)
                self.stream = cv2.VideoCapture(self.src, cv2.CAP_FFMPEG)

        try:
            self.stream.release()
        except:
            pass

    def read(self):
        return self.frame if self.ret else None

    def stop(self):
        self.stopped = True
