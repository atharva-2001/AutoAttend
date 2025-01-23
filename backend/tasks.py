from celery import Celery
import redis
from config import Config
from ultralytics import YOLO
import cv2
import numpy as np
import logging
import time
import json

logger = logging.getLogger(__name__)

app = Celery('tasks')
app.config_from_object(Config)

redis_client = redis.from_url(Config.CELERY_RESULT_BACKEND)

# Load YOLO model once when module loads
model = YOLO("models/yolo11n.pt")

@app.task(name='tasks.process_stream', bind=True)
def process_stream(self, rtsp_url):
    """Process RTSP stream with YOLO and save frames to Redis"""
    task_id = self.request.id
    redis_client.hset("active_streams", task_id, "1")
    
    try:
        # Run inference on the source directly using YOLO
        results = model(rtsp_url, stream=True)  # generator of Results objects
        
        for result in results:
            # Plot the result and convert to bytes
            frame = result.plot()
            _, frame_bytes = cv2.imencode('.jpg', frame)
            
            # Add frame to Redis stream
            redis_client.xadd(
                f"stream:{task_id}",
                {"frame": frame_bytes.tobytes()},
                maxlen=10  # Keep only recent frames
            )
            
    finally:
        redis_client.hdel("active_streams", task_id) 

@app.task(name='tasks.process_webcam_stream', bind=True)
def process_webcam_stream(self):
    """Process webcam stream with YOLO and save frames to Redis"""
    task_id = self.request.id
    redis_client.hset("active_webcams", task_id, "1")
    
    try:
        while redis_client.hexists("active_webcams", task_id):
            # Get latest frame from Redis
            frame_bytes = redis_client.get(f"current_frame:{task_id}")
            if not frame_bytes:
                time.sleep(0.03)  # Small sleep if no new frame
                continue
                
            # Convert bytes to frame for YOLO
            nparr = np.frombuffer(frame_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is None:
                logger.error("Failed to decode frame")
                continue
            
            # Run inference and plot results
            results = model(frame, stream=False)
            frame = results[0].plot()  # Plot detections just like RTSP stream
            _, frame_bytes = cv2.imencode('.jpg', frame)
            
            # Add frame to Redis stream
            redis_client.xadd(
                f"webcam:{task_id}",
                {"frame": frame_bytes.tobytes()},
                maxlen=10
            )
            
            # Clear current frame
            redis_client.delete(f"current_frame:{task_id}")
            
    finally:
        redis_client.hdel("active_webcams", task_id)
        redis_client.delete(f"current_frame:{task_id}")
        redis_client.delete(f"webcam:{task_id}") 