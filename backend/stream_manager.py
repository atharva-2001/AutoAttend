import redis
from typing import Dict
from stream_process import StreamProcess
from config import Config
import asyncio

class StreamManager:
    def __init__(self):
        self.redis_client = redis.from_url(Config.CELERY_RESULT_BACKEND)
        self.processes: Dict[str, StreamProcess] = {}
        
    def start_stream(self, stream_id: str, rtsp_url: str):
        if stream_id in self.processes:
            return False
            
        self.redis_client.hset("active_streams", stream_id, "1")
        process = StreamProcess(stream_id, rtsp_url)
        process.start()
        self.processes[stream_id] = process
        return True
        
    def stop_stream(self, stream_id: str):
        if stream_id not in self.processes:
            return False
            
        self.redis_client.hdel("active_streams", stream_id)
        process = self.processes[stream_id]
        process.stop()  # Signal the process to stop
        process.join(timeout=5)  # Wait up to 5 seconds for clean shutdown
        
        if process.is_alive():
            process.terminate()  # Force terminate if it doesn't stop cleanly
            process.join()
            
        del self.processes[stream_id]
        return True

    async def get_frame(self, stream_id: str):
        last_id = "$"  # Start with '$' to get only new messages
        while True:
            try:
                # Get the latest frame from Redis stream
                messages = self.redis_client.xread(
                    {f"stream:{stream_id}": last_id}, 
                    count=1,
                    block=1000  # Block for 1 second
                )
                if messages:
                    # Update last_id to the ID of the message we just received
                    stream_name, stream_messages = messages[0]
                    last_id = stream_messages[0][0]  # Get the message ID
                    frame_bytes = stream_messages[0][1][b"frame"]
                    yield (b'--frame\r\n'
                          b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            except Exception as e:
                print(f"Error reading frame: {e}")
                await asyncio.sleep(0.1)  # Add small delay on error
