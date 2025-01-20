from celery import Celery
import redis
from config import Config
import time
import logging

logger = logging.getLogger(__name__)

class StreamManager:
    def __init__(self):
        self.celery = Celery('tasks')
        self.redis_client = redis.from_url(Config.CELERY_RESULT_BACKEND)
        self.active_tasks = {}  # Track active tasks
        
    def start_stream(self, rtsp_url: str):
        # Start celery task and return task_id
        task = self.celery.send_task(
            'tasks.process_stream',
            args=[rtsp_url]
        )
        return {"task_id": task.id}
        
    def stop_stream(self, task_id: str):
        # Revoke the celery task with signal to force termination
        self.celery.control.revoke(task_id, terminate=True, signal='SIGTERM')
        # Clean up Redis
        self.redis_client.hdel("active_streams", task_id)
        self.redis_client.delete(f"stream:{task_id}")  # Also clean up the stream
        return True

    def process_webcam_frame(self, frame_bytes: bytes, task_id: str = None):
        """Process a webcam frame"""
        if task_id is None:
            # Start new stream task
            task = self.celery.send_task('tasks.process_webcam_stream')
            task_id = task.id
            self.active_tasks[task_id] = True
            # Wait briefly for task to start
            time.sleep(0.1)
        
        # Update current frame in Redis
        if self.redis_client.hexists("active_webcams", task_id):
            self.redis_client.set(f"current_frame:{task_id}", frame_bytes)
            return {"task_id": task_id}
        else:
            raise ValueError("Task not found or inactive")

    def stop_webcam(self, task_id: str):
        """Stop webcam processing and clean up"""
        if task_id in self.active_tasks:
            self.redis_client.hdel("active_webcams", task_id)
            self.redis_client.delete(f"current_frame:{task_id}")
            self.celery.control.revoke(task_id, terminate=True, signal='SIGTERM')
            self.redis_client.delete(f"webcam:{task_id}")
            del self.active_tasks[task_id]
        return True

    def get_frame(self, task_id: str, prefix: str = "stream"):
        """Get frames from Redis stream with configurable prefix"""
        last_id = "$"
        stream_key = f"{prefix}:{task_id}"
        active_key = "active_streams" if prefix == "stream" else "active_webcams"
        
        while True:
            # Check if stream is still active
            if not self.redis_client.hexists(active_key, task_id):
                break
                
            # Get latest frame from stream
            messages = self.redis_client.xread(
                {stream_key: last_id},
                count=1,
                block=1000
            )
            
            if messages:
                stream_name, stream_messages = messages[0]
                last_id = stream_messages[0][0]
                frame_bytes = stream_messages[0][1][b"frame"]
                yield (b'--frame\r\n'
                      b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
