from fastapi import FastAPI, HTTPException, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from ultralytics import YOLO
import cv2
from typing import Dict
import asyncio

router = APIRouter()

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

# Create instance of StreamManager
stream_manager = StreamManager()

@router.get("/stream")
async def stream_video(rtsp_url: str):
    print(f"Received stream request for URL: {rtsp_url}")
    
    stream_id = rtsp_url
    
    # Initialize video capture
    cap = cv2.VideoCapture(rtsp_url)
    if not cap.isOpened():
        print(f"Failed to open stream: {rtsp_url}")
        raise HTTPException(status_code=400, detail="Could not open RTSP stream")

    return StreamingResponse(
        stream_manager.generate_frames(stream_id, cap),
        media_type="multipart/x-mixed-replace;boundary=frame"
    )

@router.post("/stop-stream")
async def stop_stream(rtsp_url: str):
    stream_id = rtsp_url
    if stream_manager.stop_stream(stream_id):
        return {"message": f"Stream {stream_id} stopped successfully"}
    raise HTTPException(status_code=404, detail="Stream not found")

@router.get("/active-streams")
async def get_active_streams():
    active_streams = [
        stream_id 
        for stream_id, is_active in stream_manager.active_streams.items() 
        if is_active
    ]
    return {"streams": active_streams}

# Create FastAPI app
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include router with prefix
API_PREFIX = "/api"
app.include_router(router, prefix=API_PREFIX)

        