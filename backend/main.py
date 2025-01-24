from fastapi import FastAPI, HTTPException, APIRouter, WebSocket
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from config import Config
from stream_manager import StreamManager
import redis
import base64
from fastapi import WebSocketDisconnect
import asyncio

# Add this class for request validation
class StreamRequest(BaseModel):
    rtsp_url: str

class WebcamFrame(BaseModel):
    frame: str  # Base64 encoded frame

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

router = APIRouter(prefix=Config.API_PREFIX)
stream_manager = StreamManager()
redis_client = redis.from_url(Config.CELERY_RESULT_BACKEND)
redis_client.flushall()
print("Redis cache cleared on startup")

@router.post("/stream/start")
def start_stream(request: StreamRequest):
    """Start a new stream and return the task_id"""
    result = stream_manager.start_stream(request.rtsp_url)
    return result

@router.post("/stop-stream/{task_id}")
def stop_stream(task_id: str):
    """Stop a stream using its task_id"""
    if stream_manager.stop_stream(task_id):
        return {"message": f"Stream {task_id} stopped successfully"}
    raise HTTPException(status_code=404, detail="Stream not found")

@router.get("/stream/{task_id}")
async def get_stream(task_id: str):
    """Get video stream for a task_id"""
    if not redis_client.hexists("active_streams", task_id):
        raise HTTPException(status_code=404, detail="Stream not found")
        
    return StreamingResponse(
        stream_manager.get_frame(task_id),
        media_type="multipart/x-mixed-replace;boundary=frame"
    )

@router.get("/active-streams")
def get_active_streams():
    """List all active stream task_ids"""
    active_streams = redis_client.hkeys("active_streams")
    return {"streams": [s.decode() for s in active_streams]}

@router.websocket("/webcam-stream")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for webcam streaming"""
    print("WebSocket connection attempt...")
    await websocket.accept()
    print("WebSocket connection accepted")
    task_id = None
    
    try:
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=5.0
                )
                frame_base64 = data.get('frame')
                
                if not frame_base64:
                    continue
                
                frame_bytes = base64.b64decode(frame_base64)
                
                try:
                    if not task_id:
                        result = stream_manager.process_webcam_frame(frame_bytes)
                        task_id = result['task_id']
                        await websocket.send_json({"task_id": task_id})
                        print(f"New webcam task created: {task_id}")
                    else:
                        stream_manager.process_webcam_frame(frame_bytes, task_id)
                except Exception as e:
                    print(f"Error processing frame: {e}")
                    break
                    
            except asyncio.TimeoutError:
                if task_id:
                    # Check if task is still active
                    if not redis_client.hexists("active_webcams", task_id):
                        print(f"Task {task_id} is no longer active")
                        break
                continue
                
    finally:
        if task_id:
            print(f"Stopping webcam task: {task_id}")
            stream_manager.stop_webcam(task_id)

@router.get("/webcam/{task_id}")
async def get_webcam_stream(task_id: str):
    """Get processed webcam stream for a task_id"""
    if not redis_client.hexists("active_webcams", task_id):
        raise HTTPException(status_code=404, detail="Webcam stream not found")
        
    return StreamingResponse(
        stream_manager.get_frame(task_id, prefix="webcam"),
        media_type="multipart/x-mixed-replace;boundary=frame"
    )

@router.get("/active-webcams")
def get_active_webcams():
    """List all active webcam task_ids"""
    active_webcams = redis_client.hkeys("active_webcams")
    return {"webcams": [w.decode() for w in active_webcams]}

@router.get("/logs/{task_id}")
def get_logs(task_id: str):
    """Get face detection logs for a task"""
    logs = stream_manager.get_logs(task_id)
    return {"logs": logs}

app.include_router(router)
