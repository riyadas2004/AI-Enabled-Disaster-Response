import tkinter as tk
from tkinter import messagebox
from human_detection_geotagging_mean import start_detection
from intro import play_intro
from config import ACCESS_PASSWORD, RTSP_SOURCE, AI_PRIMARY_COLOR, AI_TEXT_COLOR, RTSP_TIMEOUT
import threading
import time
import cv2

class RTSPStreamerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("E.Y.E.S - AI RTSP Streamer")
        self.root.geometry("1000x700")
        self.root.configure(bg="black")
        self.root.resizable(False, False)

        border = tk.Frame(root, bg=AI_PRIMARY_COLOR, bd=4)
        border.place(relx=0.5, rely=0.5, anchor="center", width=600, height=400)

        self.inner = tk.Frame(border, bg="black")
        self.inner.pack(expand=True, fill="both", padx=5, pady=5)

        self.label_title = tk.Label(
            self.inner,
            text="E.Y.E.S AI VISION STREAMER",
            fg=AI_PRIMARY_COLOR,
            bg="black",
            font=("Consolas", 20, "bold")
        )
        self.label_title.pack(pady=20)

        self.label_status = tk.Label(
            self.inner,
            text="System Idle...",
            fg=AI_TEXT_COLOR,
            bg="black",
            font=("Consolas", 15)
        )
        self.label_status.pack(pady=10)

        tk.Label(
            self.inner,
            text="Access Password Required:",
            fg="white",
            bg="black",
            font=("Consolas", 14)
        ).pack(pady=(20,5))

        self.entry_pass = tk.Entry(
            self.inner,
            show="*",
            font=("Consolas", 16),
            width=25,
            justify="center",
            bg="#101010",
            fg=AI_PRIMARY_COLOR,
            insertbackground=AI_PRIMARY_COLOR,
            relief="flat"
        )
        self.entry_pass.pack(pady=10)

        self.btn_start = tk.Button(
            self.inner,
            text="AUTHENTICATE",
            command=self.verify_password,
            font=("Consolas", 14, "bold"),
            bg=AI_PRIMARY_COLOR,
            fg="black",
            relief="flat",
            width=18
        )
        self.btn_start.pack(pady=20)

    def show_status(self, txt):
        self.label_status.config(text=txt)
        self.root.update_idletasks()

    def verify_password(self):
        if self.entry_pass.get() == ACCESS_PASSWORD:
            self.show_status("Access Granted — Booting System...")
            self.entry_pass.config(state="disabled")
            self.btn_start.config(state="disabled")
            threading.Thread(target=self.start_intro, daemon=True).start()
        else:
            messagebox.showerror("Access Denied", "Incorrect Password")

    def start_intro(self):
        play_intro()
        self.check_rtsp()

    def check_rtsp(self):
        self.show_status("Checking RTSP stream...")

        cap = cv2.VideoCapture(RTSP_SOURCE, cv2.CAP_FFMPEG)
        time.sleep(1)

        ok = cap.isOpened()
        if ok:
            ret, _ = cap.read()
            if ret:
                cap.release()
                self.show_status("Stream Found — Launching AI...")
                self.root.after(300, self.launch_ai)
                return

        cap.release()
        self.show_status("RTSP Stream Unavailable")
        messagebox.showerror("Connection Failed", "Cannot access RTSP stream.")

    def launch_ai(self):
        self.root.destroy()
        start_detection()
