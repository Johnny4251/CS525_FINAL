#!/usr/bin/env python3
"""
gpu_receiver.py
---------------
Receive an MJPEG stream from a Raspberry Pi (see pi_stream.py),
detect vehicles with YOLO, measure their speed between two virtual
lines X ft apart, classify color, and log results.

Features
--------
• Horizontal  *or*  vertical boundaries (choose with BOUNDARY_ORIENTATION)
• Click‑to‑calibrate preview window – prints pixel coordinates on click
• Plain‑text speed log:  [timestamp] Car Color: <color>, Speed: <mph> mph
"""

import cv2
import socket
import struct
import numpy as np
from datetime import datetime
from ultralytics import YOLO

# For the webserver
import sqlite3
import json

SPEED_LIMIT_MPH   = 15.0
UDP_BCAST_IP      = "255.255.255.255"
UDP_BCAST_PORT    = 6000

udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

db = sqlite3.connect("vehicle_status.db", check_same_thread=False)
db.execute("""
CREATE TABLE IF NOT EXISTS vehicle_status(
    color       TEXT PRIMARY KEY,
    speed_mph   REAL,
    status      TEXT,
    updated_at  TEXT DEFAULT (datetime('now'))
)
""")
db.commit()

LISTEN_PORT        = 5000

YOLO_WEIGHTS       = "yolov8n.pt"
VEHICLE_CLASSES    = [2, 3, 5, 7]

BOUNDARY_ORIENTATION = "vertical"

LINE1_POS = 250
LINE2_POS = 875
DISTANCE_FT        = 50
MATCH_TOL          = 100
LOG_FILE           = "speed_log.txt"
ENABLE_PREVIEW     = True

MARGIN = 20

# Using HSV color palette => get the center color
# Used to classify vehicles on the database
def get_dominant_color(roi: np.ndarray) -> str:
    if roi.size == 0:
        return "Unknown"
    avg_bgr = cv2.mean(roi)[:3]
    avg_bgr = np.array(avg_bgr, dtype=np.uint8).reshape(1, 1, 3)
    h, s, v = cv2.cvtColor(avg_bgr, cv2.COLOR_BGR2HSV)[0, 0]
    if s < 50:
        if v < 50:   return "Black"
        if v > 100:  return "White"
        return "Gray"
    if   h < 10 or h >= 170: return "Red"
    elif h < 25:             return "Orange"
    elif h < 35:             return "Yellow"
    elif h < 85:             return "Green"
    elif h < 130:            return "Blue"
    elif h < 170:            return "Purple"
    return "Unknown"

"""
Draws start and end boundaries to measure from.
"""
def draw_boundaries(frame, line_pos1, line_pos2, orientation):
    h, w = frame.shape[:2]
    if orientation == "horizontal":
        cv2.line(frame, (0, line_pos1), (w, line_pos1), (0, 255, 255), 2)
        cv2.line(frame, (0, line_pos2), (w, line_pos2), (0, 255, 255), 2)
    else:
        cv2.line(frame, (line_pos1, 0), (line_pos1, h), (0, 255, 255), 2)
        cv2.line(frame, (line_pos2, 0), (line_pos2, h), (0, 255, 255), 2)

# Helper function to read if boundaries have been crossed
def crossed_boundary(coord_prev, coord_curr, boundary_pos):
    return coord_prev < boundary_pos <= coord_curr

def update_db(color: str, speed: float, status: str) -> None:
    db.execute("""
    INSERT INTO vehicle_status(color, speed_mph, status)
    VALUES(?,?,?)
    ON CONFLICT(color) DO UPDATE
      SET speed_mph=excluded.speed_mph,
          status   =excluded.status,
          updated_at = datetime('now')
    """, (color, speed, status))
    db.commit()

def main():

    # Create model
    model = YOLO(YOLO_WEIGHTS)

    # Create & Bind & Listen on Socket
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.bind(("127.0.0.1", LISTEN_PORT))
    srv.listen(1)
    print(f"[GPU] Listening on port {LISTEN_PORT} …")
    conn, addr = srv.accept()
    print(f"[GPU] Connected by {addr}")


    # Enable preview shows window
    if ENABLE_PREVIEW:
        cv2.namedWindow("Stream")
        def on_mouse(event, x, y, flags, _):
            if event == cv2.EVENT_LBUTTONDOWN:
                print(f"[CAL] Clicked  x={x:4d},  y={y:4d}")
        cv2.setMouseCallback("Stream", on_mouse)

    buffer = b""
    HEADER = 12
    next_id = 0
    tracks = {}
    try:
        while True:
            while len(buffer) < HEADER:
                chunk = conn.recv(8192)
                if not chunk:
                    raise ConnectionAbortedError
                buffer += chunk
            ts_ns, size = struct.unpack("dI", buffer[:HEADER])
            ts = ts_ns / 1e9                # Time @ Nanosecond resolution
            buffer = buffer[HEADER:]

            # Pass through the buffer
            while len(buffer) < size:
                chunk = conn.recv(8192)
                if not chunk:
                    raise ConnectionAbortedError
                buffer += chunk
            jpg = buffer[:size]
            buffer = buffer[size:]

            # Decode frame for Model
            frame = cv2.imdecode(np.frombuffer(jpg, np.uint8), cv2.IMREAD_COLOR)
            if frame is None:
                continue

            # Get model results
            result = model.predict(frame, classes=VEHICLE_CLASSES,
                                   conf=0.25, verbose=False)[0]
            detections = []
            if result.boxes:
                for box in result.boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                    detections.append((cx, cy, x1, y1, x2, y2))

            # filter to ROI: within boundaries ± margin
            roi_detections = []
            for cx, cy, x1, y1, x2, y2 in detections:
                coord = cx if BOUNDARY_ORIENTATION == "vertical" else cy
                if LINE1_POS - MARGIN <= coord <= LINE2_POS + MARGIN:
                    roi_detections.append((cx, cy, x1, y1, x2, y2))
            detections = roi_detections

            # Call draw boundaries to read from
            draw_boundaries(frame, LINE1_POS, LINE2_POS, BOUNDARY_ORIENTATION)

            updated = {}
            for cx, cy, x1, y1, x2, y2 in detections:
                match = None
                for tid, info in tracks.items():
                    px, py = info["center"]
                    if abs(cx - px) < MATCH_TOL and abs(cy - py) < MATCH_TOL:
                        match = tid
                        break
                if match is None:
                    match = next_id
                    next_id += 1
                    tracks[match] = {
                        "center": (cx, cy),
                        "bbox": (x1, y1, x2, y2),
                        "started": False,
                        "start_ts": None,
                        "color": None,
                        "logged": False
                    }
                info = tracks[match]
                coord_prev = info["center"][0] if BOUNDARY_ORIENTATION == "vertical" else info["center"][1]
                coord_curr = cx if BOUNDARY_ORIENTATION == "vertical" else cy
                info["center"] = (cx, cy)
                info["bbox"] = (x1, y1, x2, y2)
                updated[match] = info

                if (not info["started"] and
                        crossed_boundary(coord_prev, coord_curr, LINE1_POS)):
                    info["started"]  = True
                    info["start_ts"] = ts
                    roi = frame[y1:y2, x1:x2]
                    info["color"]    = get_dominant_color(roi)

                if (info["started"] and not info["logged"] and
                        crossed_boundary(coord_prev, coord_curr, LINE2_POS)):
                    dt = ts - info["start_ts"]
                    if dt > 0:
                        fps  = DISTANCE_FT / dt
                        mph  = fps * 3600 / 5280
                        color = info["color"] or "Unknown"
                        status = "OKAY" if mph <= SPEED_LIMIT_MPH else "SLOW DOWN!!"
                        tstr   = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
                        log   = f"{tstr} Car Color: {color}, Speed: {mph:.1f} mph"
                        print("[GPU]", log)
                        with open(LOG_FILE, "a") as f:
                            f.write(log + "\n")
                        update_db(color, mph, status)
                        if status != "OKAY":
                            alert = json.dumps({"color": color,
                                                "speed": mph,
                                                "msg":   status})
                            udp_sock.sendto(alert.encode(), (UDP_BCAST_IP, UDP_BCAST_PORT))
                    info["logged"] = True

            tracks = updated

            # Draws the rectangle and shows window if preview is enabled
            if ENABLE_PREVIEW:
                for tid, inf in tracks.items():
                    x1, y1, x2, y2 = inf["bbox"]
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(frame, str(tid), (x1, y1 - 5),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                cv2.imshow("Stream", frame)
                key = cv2.waitKey(1) & 0xFF
                if key in (27, ord('q')):
                    break

    except ConnectionAbortedError:
        print("[GPU] Connection closed.")
    finally:    # Safely close socket
        conn.close()
        srv.close()
        cv2.destroyAllWindows()

if __name__ == "__main__":

    # Using a while true so socket reopens when client disconnects
    # probably should use a multithreaded approach.. but oh well
    while True:
        main()
