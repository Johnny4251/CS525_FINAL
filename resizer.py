#!/usr/bin/env python3
"""
resize_school_video.py
----------------------
Reads 'school_edit.mp4', resizes each frame to 1280×720, and writes out 'school.mp4'.
Usage:
    python3 resize_school_video.py [input_path] [output_path]
If no arguments are given, defaults to 'school_edit.mp4' → 'school.mp4'.
"""

import cv2
import sys

# Parse command-line arguments
def parse_args():
    import argparse
    parser = argparse.ArgumentParser(description="Resize a video to 1280x720 using OpenCV.")
    parser.add_argument('input', nargs='?', default='school_edit.mp4',
                        help='Input video file path (default: school_edit.mp4)')
    parser.add_argument('output', nargs='?', default='school.mp4',
                        help='Output video file path (default: school.mp4)')
    return parser.parse_args()


def main():
    args = parse_args()
    cap = cv2.VideoCapture(args.input)
    if not cap.isOpened():
        print(f"Error: Could not open input file '{args.input}'")
        sys.exit(1)

    # Get original properties
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    width, height = 1280, 720

    out = cv2.VideoWriter(args.output, fourcc, fps, (width, height))
    if not out.isOpened():
        print(f"Error: Could not open output file '{args.output}' for writing")
        cap.release()
        sys.exit(1)

    print(f"Resizing '{args.input}' → '{args.output}' at {width}x{height}, {fps:.2f} FPS...")
    frame_count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        # Resize frame
        resized = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)
        out.write(resized)
        frame_count += 1

    cap.release()
    out.release()
    print(f"Done: {frame_count} frames processed.")


if __name__ == '__main__':
    main()
