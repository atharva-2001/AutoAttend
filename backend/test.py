from ultralytics import YOLO

# Load a pretrained YOLO11n model
model = YOLO("yolo11n.pt")

# Single stream with batch-size 1 inference
source = "rtsp://admin:IRMAXS@192.168.31.131:554/ch1/main"  # RTSP, RTMP, TCP, or IP streaming address

# Run inference on the source
results = model(source, stream=True)  # generator of Results objects

for result in results:
    print(result)
    print(type(result))
    print(dir(result))
    break
