from celery import Celery
import redis
from config import Config
from ultralytics import YOLO
import cv2
import numpy as np
import logging
import time
import json
import onnxruntime as ort
from pathlib import Path
from face_matcher import FaceMatcher

logger = logging.getLogger(__name__)

app = Celery('tasks')
app.config_from_object(Config)

redis_client = redis.from_url(Config.CELERY_RESULT_BACKEND)

# Load YOLO model once when module loads
# model = YOLO("models/yolo11n.pt")
face_model = YOLO("models/yolov11l-face.pt")

# Initialize FaceMatcher once at module level
face_matcher = FaceMatcher(
    model_path='models/insightface_R50_Glint360K.onnx',
    threshold=0.2
)

# Load known faces once at startup
known_faces_dir = Path("known_faces")
for face_path in known_faces_dir.glob("*.jpg"):
    name = face_path.stem
    face_img = cv2.imread(str(face_path))
    if face_img is not None:
        face_matcher.add_face(name, face_img)
    else:
        logger.error(f"Failed to load face image: {face_path}")

@app.task(name='tasks.process_stream', bind=True)
def process_stream(self, rtsp_url):
    """Process RTSP stream with YOLO face detection and face matching"""
    task_id = self.request.id
    last_processed_time = 0
    FRAME_INTERVAL = 0.5
    
    try:
        redis_client.hset("active_streams", task_id, "1")
        results = face_model(rtsp_url, stream=True)
        
        for result in results:
            frame = result.orig_img
            
            # Process each face detection
            if len(result.boxes) > 0:
                for box in result.boxes:
                    # Get coordinates and confidence
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    conf = box.conf[0].cpu().numpy()
                    
                    if conf > 0.5:  # Confidence threshold
                        # Extract face crop
                        face_crop = frame[int(y1):int(y2), int(x1):int(x2)]
                        
                        # Find match using InsightFace
                        name, score = face_matcher.find_match(face_crop)
                        
                        # Draw results on frame
                        cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 3)
                        if name:
                            label = f"{name} ({score:.2f})"
                            cv2.putText(frame, label, (int(x1), int(y1)-20), 
                                      cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 3)
                            logger.info(f"Face matched: {name} with confidence {score:.2f}")
            
            # Convert to bytes and save to Redis
            _, frame_bytes = cv2.imencode('.jpg', frame)
            redis_client.xadd(
                f"stream:{task_id}",
                {"frame": frame_bytes.tobytes()},
                maxlen=10
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
            
            # Run face detection
            results = face_model(frame, stream=False)
            
            # Process each face detection
            if len(results[0].boxes) > 0:
                for box in results[0].boxes:
                    # Get coordinates and confidence
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    conf = box.conf[0].cpu().numpy()
                    
                    if conf > 0.5:  # Confidence threshold
                        # Extract face crop
                        face_crop = frame[int(y1):int(y2), int(x1):int(x2)]
                        
                        # Find match using InsightFace
                        name, score = face_matcher.find_match(face_crop)
                        
                        # Draw results on frame
                        cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 3)
                        if name:
                            label = f"{name} ({score:.2f})"
                            cv2.putText(frame, label, (int(x1), int(y1)-20), 
                                      cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 3)
                            logger.info(f"Face matched: {name} with confidence {score:.2f}")
            
            # Convert processed frame to bytes and save to Redis stream
            _, frame_bytes = cv2.imencode('.jpg', frame)
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