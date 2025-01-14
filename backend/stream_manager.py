import cv2
import asyncio
from typing import Dict
from ultralytics import YOLO

class StreamManager:
    def __init__(self):
        self.model = YOLO("yolo11n.pt")
        self.active_streams: Dict[str, bool] = {}
        
    def stop_stream(self, stream_id: str):
        if stream_id in self.active_streams:
            self.active_streams[stream_id] = False
            return True
        return False

    async def process_frame(self, frame):
        """Process a single frame with YOLO"""
        results = self.model(frame, verbose=False)
        annotated_frame = results[0].plot()
        _, buffer = cv2.imencode('.jpg', annotated_frame)
        return buffer.tobytes()

    async def generate_frames(self, stream_id: str, cap):
        """Generate frames asynchronously"""
        self.active_streams[stream_id] = True
        
        try:
            while self.active_streams.get(stream_id, False):
                success, frame = cap.read()
                if not success:
                    break

                # Process frame asynchronously
                frame_bytes = await self.process_frame(frame)
                
                yield (b'--frame\r\n'
                      b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                
                # Small delay to control frame rate
                await asyncio.sleep(0.033)  # ~30 FPS
                
        finally:
            cap.release()
            if stream_id in self.active_streams:
                self.active_streams.pop(stream_id)
            print(f"Stream {stream_id} ended")
