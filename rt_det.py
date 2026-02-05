import cv2
import os
import csv
import threading
import queue
from datetime import datetime
from collections import deque
from ultralytics import YOLO
import subprocess

# ---------------- CONFIG ----------------
MODEL_PATH = "best_ncnn_model"
VIDEO_PATH = 0
CONF_THRESH = 0.4
PRE_BUFFER_SECONDS = 2   
POST_BUFFER_SECONDS = 3  
ANOMALY_CLASSES = [2, 3, 4, 5] 
SHOW_PREVIEW = True
# ----------------------------------------

os.makedirs("logs", exist_ok=True)
os.makedirs("clips", exist_ok=True)
log_file = "logs/anomaly_log.csv"

if not os.path.exists(log_file):
    with open(log_file, "w", newline="") as f:
        csv.writer(f).writerow(["timestamp", "class", "confidence", "clip"])

model = YOLO(MODEL_PATH)
cap = cv2.VideoCapture(VIDEO_PATH)

if not cap.isOpened():
    print("❌ Could not open video")
    exit()

fps = cap.get(cv2.CAP_PROP_FPS)
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

pre_buffer_max = int(fps * PRE_BUFFER_SECONDS)
post_buffer_max = int(fps * POST_BUFFER_SECONDS)
frame_buffer = deque(maxlen=pre_buffer_max) 

save_queue = queue.Queue()
def file_writer_worker():
    while True:
        item = save_queue.get()
        if item is None:
            save_queue.task_done()
            break

        mp4_path, frames, fps, size = item
        if fps <= 1:
            fps = 25

        width, height = size

        # FFmpeg: raw frames → MP4 (H.264 / avc1)
        proc = subprocess.Popen(
            [
                "ffmpeg",
                "-y",

                # input from stdin
                "-f", "rawvideo",
                "-pix_fmt", "bgr24",
                "-s", f"{width}x{height}",
                "-r", str(fps),
                "-i", "-",

                # output codec
                "-c:v", "libx264",
                "-profile:v", "baseline",
                "-level", "3.0",
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",

                mp4_path
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        for f in frames:
            proc.stdin.write(f.tobytes())

        proc.stdin.close()
        proc.wait()

        print("✅ MP4 (avc1) saved:", mp4_path)
        save_queue.task_done()



worker_thread = threading.Thread(target=file_writer_worker, daemon=True)
worker_thread.start()

recording = False
post_event_frames = []
current_clip_name = ""

print("🚀 System Live (No Cooldown, All Fixes Applied)")

try:
    while True:
        ret, frame = cap.read()
        if not ret: 
            # If video ends while recording, push the final frames to the queue
            if recording and post_event_frames:
                full_clip = list(frame_buffer) + post_event_frames
                clip_path = os.path.join("clips", current_clip_name)
                save_queue.put((clip_path, full_clip, fps, (width, height)))
            break

        results = model(frame, conf=CONF_THRESH, verbose=False)
        raw_detections = results[0].boxes if len(results) > 0 else []
        
        anomaly_detections = [box for box in raw_detections if int(box.cls[0]) in ANOMALY_CLASSES]
        anomaly_this_frame = len(anomaly_detections) > 0
        
        # Draw boxes
        for box in anomaly_detections:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            label = model.names[int(box.cls[0])]
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
            cv2.putText(frame, label, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

        # Trigger Logic
        if anomaly_this_frame and not recording:
            recording = True
            post_event_frames = []
            current_clip_name = f"event_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
            
            with open(log_file, "a", newline="") as f:
                best_label = model.names[int(anomaly_detections[0].cls[0])]
                csv.writer(f).writerow([datetime.now(), best_label, float(anomaly_detections[0].conf[0]), current_clip_name])

        if recording:
            post_event_frames.append(frame.copy())
            if len(post_event_frames) >= post_buffer_max:
                full_clip = list(frame_buffer) + post_event_frames
                clip_path = os.path.join("clips", current_clip_name)
                save_queue.put((clip_path, full_clip, fps, (width, height)))
                recording = False
                post_event_frames = []
        else:
            frame_buffer.append(frame.copy())

        if SHOW_PREVIEW:
            cv2.imshow("Detection", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'): break

finally:
    print("⏳ Closing... waiting for clips to finish writing to disk.")
    save_queue.put(None) # Sentinel to stop worker
    save_queue.join()    # BLOCK until queue is empty
    cap.release()
    cv2.destroyAllWindows()
    print("🛑 Done.")
