# CS525 Internet of Things Final Project
### Instructor: Dr. Priyangshu Sen
### John Pertell 04.07.25

![Poster Example](imgs/IotPoster.png)

# Vehicle Speed Detection & Dashboard System

This project is a complete pipeline for detecting vehicles using a camera feed (e.g. Raspberry Pi), measuring their speed using YOLO object detection and virtual boundaries, classifying vehicle color, and providing real-time speed status on a web dashboard.

---

## Features

- **Vehicle detection** using YOLOv8 (cars, trucks, motorcycles, buses)
- **Speed measurement** between two configurable virtual lines
- **Dominant color classification**
- **Live dashboard** for drivers to view their current speed/status
- **Click-to-calibrate** live preview for setting virtual lines
- **UDP alert broadcasting** for over-speeding vehicles

---

## Components

### 1. `gpu_receiver.py`

- Runs on a machine with a GPU.
- Receives MJPEG stream from Raspberry Pi over TCP.
- Detects vehicles using YOLOv8.
- Tracks movement across virtual lines to compute speed.
- Classifies dominant color of vehicles.
- Logs speed data to a file and SQLite database.
- Sends UDP alerts for over-speeding vehicles.
- Displays a live annotated video preview with bounding boxes and calibration clicks.

### 2. `pi_stream.py`

- Runs on a Raspberry Pi or camera-capable machine.
- Captures frames from a PiCam or webcam.
- Optionally streams from a video file instead.
- Sends JPEG-compressed frames with timestamps over TCP to the GPU machine.

### 3. `vehicle_server.py`

- A lightweight Flask web app.
- Lets users select their vehicle color.
- Displays their current speed and status (OKAY / SLOW DOWN!!) in real-time.
- Auto-refreshes every second.

---

## Installation

### Prerequisites

- Python 3.8+
- OpenCV
- Ultralytics YOLOv8 (via `ultralytics`)
- Flask

### Setup Instructions

```bash
# Clone the repo
git clone https://github.com/yourusername/vehicle-speed-dashboard.git
cd vehicle-speed-dashboard

# Run setup script
bash install.sh
