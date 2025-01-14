import cv2
from celery import Celery
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)
app = Celery('tasks')

@app.task(name='tasks.get_frame')
def get_frame(rtsp_url):
    cap = cv2.VideoCapture(rtsp_url)
    success, frame = cap.read()
    cap.release()
    return frame if success else None 