import cv2
import time
from config import INTRO_VIDEO_PATH

def play_intro():
    cap = cv2.VideoCapture(INTRO_VIDEO_PATH)
    if not cap.isOpened():
        return

    cv2.namedWindow("AI Booting...", cv2.WND_PROP_FULLSCREEN)
    cv2.setWindowProperty("AI Booting...", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        cv2.imshow("AI Booting...", frame)

        if cv2.waitKey(25) & 0xFF == 27:
            break

    cap.release()
    cv2.destroyAllWindows()
    time.sleep(0.3)
