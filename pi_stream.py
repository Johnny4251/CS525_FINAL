#!/usr/bin/env python3
"""
pi_stream.py
------------
If no argument is given, capture live video from a PiCam / USB webcam.
If a path/URL is supplied, stream that video file instead.

Usage
-----
Live camera   : python3 pi_stream.py
From a video  : python3 pi_stream.py /path/to/video.mp4
"""

import cv2
import socket
import struct
import time
import argparse
import os

SERVER_IP   = "127.0.0.1"   # GPU machine’s IP
SERVER_PORT = 5000
CAM_INDEX   = 0
WIDTH, HEIGHT = 640, 480
FPS_TARGET  = 30            # camera target FPS
JPEG_QUALITY = 80

def open_capture(source: str | None):
    """
    Return an opened cv2.VideoCapture.
    If source is None → open camera (CAM_INDEX).
    Else               → open video file / URL.
    """
    if source is None:
        cap = cv2.VideoCapture(CAM_INDEX)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)
        cap.set(cv2.CAP_PROP_FPS, FPS_TARGET)
    else:
        if not os.path.exists(source):
            print(f"[Pi] Warning: '{source}' not found, trying to open anyway…")
        cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video source: {source if source else 'camera'}")
    return cap

def main():
    parser = argparse.ArgumentParser(description="Pi video streamer")
    parser.add_argument("source", nargs="?", default=None,
                        help="Optional path/URL to a video file. Omit for live camera.")
    args = parser.parse_args()

    cap = open_capture(args.source)
    # Frame delay for video files to mimic real‑time playback
    video_fps = cap.get(cv2.CAP_PROP_FPS)
    delay = (1.0 / video_fps) if video_fps > 0 else 0

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((SERVER_IP, SERVER_PORT))
    print(f"[Pi] Connected to {SERVER_IP}:{SERVER_PORT}")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("[Pi] End of stream or camera error")
                cap = open_capture(args.source)
                continue
            ts = time.time()

            # overlay
            cv2.putText(frame,
                        time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts)),
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1,
                        (0, 255, 0), 2)

            # JPEG encode 
            ok, jpg = cv2.imencode(".jpg", frame,
                                   [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
            if not ok:
                continue
            payload = jpg.tobytes()
            header  = struct.pack("dI", ts, len(payload))
            sock.sendall(header + payload)

            # For video files, wait so we don’t send faster than real‑time
            if args.source and delay > 0:
                time.sleep(delay)
            # For camera, you could limit FPS:
            # elif not args.source:
            #     time.sleep(max(0, 1/FPS_TARGET - (time.time()-ts)))
    finally:
        cap.release()
        sock.close()
        print("[Pi] Streaming stopped.")

if __name__ == "__main__":
    main()
