import cv2
import redis
from ultralytics import YOLO
import multiprocessing
from config import Config
from celery import Celery
import subprocess
import signal
import numpy as np
from multiprocessing import Event

class StreamProcess(multiprocessing.Process):
    def __init__(self, stream_id, rtsp_url):
        super().__init__()
        self.stream_id = stream_id
        self.rtsp_url = rtsp_url
        self.celery = Celery('tasks', broker=Config.CELERY_BROKER_URL)
        self.stop_event = Event()
        
    def stop(self):
        self.stop_event.set()
        
    def run(self):
        # Set up signal handlers
        signal.signal(signal.SIGTERM, lambda signo, frame: self.stop())
        signal.signal(signal.SIGINT, lambda signo, frame: self.stop())
        
        redis_client = redis.from_url(Config.CELERY_RESULT_BACKEND)
        model = YOLO("yolo11n.pt")
        
        try:
            consecutive_failures = 0
            while not self.stop_event.is_set() and redis_client.hget("active_streams", self.stream_id):
                try:
                    # Use async_result to avoid blocking indefinitely
                    task = self.celery.send_task('tasks.get_frame', args=[self.rtsp_url])
                    frame_bytes = task.get(timeout=2.0)  # Increased timeout
                    
                    if frame_bytes is None:
                        consecutive_failures += 1
                        if consecutive_failures > 5:  # Reset stream after 5 consecutive failures
                            print(f"Too many consecutive failures for stream {self.stream_id}, resetting...")
                            break
                        continue
                    
                    consecutive_failures = 0  # Reset counter on success
                    
                    frame = cv2.imdecode(np.frombuffer(frame_bytes, np.uint8), cv2.IMREAD_COLOR)
                    results = model(frame, verbose=False)
                    annotated_frame = results[0].plot()
                    _, buffer = cv2.imencode('.jpg', annotated_frame)
                    frame_bytes = buffer.tobytes()
                    
                    redis_client.xadd(f"stream:{self.stream_id}", {"frame": frame_bytes}, maxlen=10)  # Limit stream length
                    
                except TimeoutError:
                    consecutive_failures += 1
                    print(f"Timeout error for stream {self.stream_id}")
                    continue
                except Exception as e:
                    consecutive_failures += 1
                    print(f"Error processing frame: {e}")
                    if consecutive_failures > 5:
                        print(f"Too many consecutive failures for stream {self.stream_id}, resetting...")
                        break
                    continue

        finally:
            redis_client.hdel("active_streams", self.stream_id)
            print(f"Stream {self.stream_id} ended")

