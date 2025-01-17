from fastapi import FastAPI, HTTPException, APIRouter
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from config import Config
from stream_manager import StreamManager
import redis

# Add this class for request validation
class StreamRequest(BaseModel):
    rtsp_url: str

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

@router.post("/stream/stop/{task_id}")
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

app.include_router(router)
