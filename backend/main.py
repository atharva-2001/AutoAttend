from fastapi import FastAPI, HTTPException, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from ultralytics import YOLO
import cv2
from typing import Dict
import asyncio
from config import Config
from celery import Celery
from stream_manager import StreamManager
from __init__ import app

router = APIRouter(prefix=Config.API_PREFIX)
stream_manager = StreamManager()

@router.get("/stream")
async def stream_video(rtsp_url: str):
    print(f"Received stream request for URL: {rtsp_url}")
    stream_id = rtsp_url
    
    if not stream_manager.start_stream(stream_id, rtsp_url):
        raise HTTPException(status_code=400, detail="Stream already exists")

    return StreamingResponse(
        stream_manager.get_frame(stream_id),
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
    active_streams = stream_manager.redis_client.hkeys("active_streams")
    return {"streams": [s.decode() for s in active_streams]}

app.include_router(router)
