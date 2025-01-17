from celery import Celery
import redis
from config import Config

class StreamManager:
    def __init__(self):
        self.celery = Celery('tasks')
        self.redis_client = redis.from_url(Config.CELERY_RESULT_BACKEND)
        
    def start_stream(self, rtsp_url: str):
        # Start celery task and return task_id
        task = self.celery.send_task(
            'tasks.process_stream',
            args=[rtsp_url]
        )
        return {"task_id": task.id}
        
    def stop_stream(self, task_id: str):
        # Revoke the celery task
        self.celery.control.revoke(task_id, terminate=True)
        self.redis_client.hdel("active_streams", task_id)
        return True

    def get_frame(self, task_id: str):
        last_id = "$"
        while True:
            # Check if stream is still active
            if not self.redis_client.hexists("active_streams", task_id):
                break
                
            # Get latest frame from stream
            messages = self.redis_client.xread(
                {f"stream:{task_id}": last_id},
                count=1,
                block=1000
            )
            
            if messages:
                stream_name, stream_messages = messages[0]
                last_id = stream_messages[0][0]
                frame_bytes = stream_messages[0][1][b"frame"]
                yield (b'--frame\r\n'
                      b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
