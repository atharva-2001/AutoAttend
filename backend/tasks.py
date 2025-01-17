from celery import Celery
import redis
from config import Config
from ultralytics import YOLO
import cv2

app = Celery('tasks')
app.config_from_object(Config)

redis_client = redis.from_url(Config.CELERY_RESULT_BACKEND)

# Load YOLO model once when module loads
model = YOLO("yolo11n.pt")

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