import cv2
from celery import Celery
from celery.utils.log import get_task_logger
from config import Config

logger = get_task_logger(__name__)
app = Celery('tasks', broker=Config.CELERY_BROKER_URL)

@app.task(name='tasks.get_frame')
def get_frame(rtsp_url):
    # Set OpenCV capture properties for better RTSP handling
    cap = cv2.VideoCapture(rtsp_url)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize buffer size
    
    # Set timeouts
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M','J','P','G'))
    cap.set(cv2.CAP_PROP_FPS, 30)
    
    try:
        success, frame = cap.read()
        if not success:
            return None
            
        # Encode frame to bytes before returning
        _, buffer = cv2.imencode('.jpg', frame)
        return buffer.tobytes()
    except Exception as e:
        logger.error(f"Error capturing frame: {e}")
        return None
    finally:
        cap.release() 