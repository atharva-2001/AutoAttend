'use client'

import { useState, useEffect, useRef } from 'react'
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { API_CONFIG } from '@/config/api'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import Image from 'next/image'

export default function DualCameraFeed() {
  const [rtspUrl, setRtspUrl] = useState("rtsp://admin:IRMAXS@192.168.31.131:554/ch1/main")
  const [imageUrl, setImageUrl] = useState("")
  const [activeStreams, setActiveStreams] = useState<string[]>([])
  const [imageError, setImageError] = useState(false)
  const [retryCount, setRetryCount] = useState(0)
  const [webcamStream, setWebcamStream] = useState<MediaStream | null>(null)
  const [showWebcam, setShowWebcam] = useState(false)
  const [websocket, setWebsocket] = useState<WebSocket | null>(null)
  const [webcamTaskId, setWebcamTaskId] = useState<string | null>(null)
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)

  const fetchActiveStreams = async () => {
    try {
      const response = await fetch(`${API_CONFIG.BASE_URL}/api${API_CONFIG.ENDPOINTS.ACTIVE_STREAMS}`)
      if (response.ok) {
        const data = await response.json()
        setActiveStreams(data.streams)
      }
    } catch (error) {
      console.error("Error fetching active streams:", error)
    }
  }

  useEffect(() => {
    const interval = setInterval(fetchActiveStreams, 5000)
    return () => clearInterval(interval)
  }, [])

  const startStream = async () => {
    try {
      const response = await fetch(
        `${API_CONFIG.BASE_URL}/api${API_CONFIG.ENDPOINTS.STREAM}/start`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ rtsp_url: rtspUrl })
        }
      )
      if (response.ok) {
        const data = await response.json()
        const streamUrl = `${API_CONFIG.BASE_URL}/api${API_CONFIG.ENDPOINTS.STREAM}/${data.task_id}`
        setImageUrl(streamUrl)
        fetchActiveStreams()
      }
    } catch (error) {
      console.error("Error starting stream:", error)
    }
  }

  const stopStream = async (taskId: string) => {
    try {
      const response = await fetch(
        `${API_CONFIG.BASE_URL}/api${API_CONFIG.ENDPOINTS.STOP_STREAM}/${taskId}`,
        { method: 'POST' }
      )
      if (response.ok) {
        setImageUrl("")
        fetchActiveStreams()
      }
    } catch (error) {
      console.error("Error stopping stream:", error)
    }
  }

  const handleImageError = () => {
    console.error("Image failed to load")
    if (retryCount < 1) {  // Only retry once
      console.log("Retrying image load...")
      setRetryCount(prev => prev + 1)
      // Force re-render of Image component
      setImageUrl(prev => prev + "?retry=" + new Date().getTime())
    } else {
      setImageError(true)
    }
  }

  const handleImageLoad = () => {
    setImageError(false)
    setRetryCount(0)  // Reset retry count on successful load
  }

  const startWebcam = async () => {
    try {
        console.log("Starting webcam...");
        if (!videoRef.current) {
            console.error("Video element not found - aborting");
            return;
        }
        console.log("Video ref found");

        const stream = await navigator.mediaDevices.getUserMedia({ 
            video: true,
            audio: false 
        });
        console.log("Webcam stream obtained");
        
        videoRef.current.srcObject = stream;
        console.log("Stream set to video element");

        await videoRef.current.play();
        console.log("Video playback started");
        
        // Set webcam state first
        setShowWebcam(true);
        setWebcamStream(stream);

        // Wait for state to update
        await new Promise(resolve => setTimeout(resolve, 100));

        // Create WebSocket connection
        const ws = new WebSocket(`${API_CONFIG.WS_URL}/api/webcam-stream`);
        console.log("WebSocket created");

        // Set up WebSocket handlers
        ws.onopen = () => {
            console.log("WebSocket connection opened");
            setWebsocket(ws);
            // Start capture with local showWebcam value
            startFrameCapture(ws, true); // Pass showWebcam state directly
        };
        
        ws.onerror = (error) => {
            console.error("WebSocket error:", error);
        };
        
        ws.onclose = () => {
            console.log("WebSocket closed");
            setWebsocket(null);
        };
        
        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.task_id) {
                    console.log("Got task ID:", data.task_id);
                    setWebcamTaskId(data.task_id);
                }
            } catch (error) {
                console.error("Error parsing WebSocket message:", error);
            }
        };
        
    } catch (error) {
        console.error("Error in startWebcam:", error);
        if (webcamStream) {
            webcamStream.getTracks().forEach(track => track.stop());
        }
        setShowWebcam(false);
        setWebsocket(null);
    }
  };

  // Modified to accept WebSocket and showWebcam state directly
  const startFrameCapture = (ws: WebSocket, isWebcamActive: boolean) => {
    console.log("startFrameCapture called, checking refs...");
    
    if (!canvasRef.current || !videoRef.current) {
        console.error("Missing refs:", {
            canvas: !!canvasRef.current,
            video: !!videoRef.current
        });
        return;
    }

    const canvas = canvasRef.current;
    const video = videoRef.current;
    const context = canvas.getContext('2d');
    
    if (!context) {
        console.error("Failed to get canvas context");
        return;
    }

    console.log("All refs ready, starting capture loop");
    
    let frameCount = 0;
    let isActive = isWebcamActive;
    const CAPTURE_INTERVAL = 500;

    const captureFrame = () => {
        if (!isActive || ws.readyState !== WebSocket.OPEN) {
            console.log("Capture stopped:", {
                isActive,
                wsState: ws.readyState
            });
            return;
        }

        try {
            context.drawImage(video, 0, 0, canvas.width, canvas.height);
            const frame = canvas.toDataURL('image/jpeg', 0.5);
            const base64Data = frame.split(',')[1];
            
            frameCount++;
            console.log(`Sending frame #${frameCount}, size: ${base64Data.length} bytes`);
            
            ws.send(JSON.stringify({
                frame: base64Data,
                frameNumber: frameCount
            }));

            // Continue capture loop
            setTimeout(captureFrame, CAPTURE_INTERVAL);
        } catch (error) {
            console.error("Error in frame capture:", error);
            isActive = false;
        }
    };

    // Start the capture loop
    captureFrame();
  };

  const stopWebcam = () => {
    console.log("Stopping webcam...");
    if (webcamStream) {
        webcamStream.getTracks().forEach(track => {
            console.log("Stopping track:", track.kind);
            track.stop();
        });
        setWebcamStream(null);
    }
    if (websocket) {
        console.log("Closing WebSocket...");
        websocket.close();
        setWebsocket(null);
    }
    setShowWebcam(false);
    setWebcamTaskId(null);
    console.log("Webcam stopped");
  }

  return (
    <div className="p-8">
      <div className="max-w-3xl mx-auto bg-white rounded-xl shadow-2xl overflow-hidden">
        <div className="p-8">
          <h1 className="text-4xl font-semibold text-center mb-8 text-gray-800">RTSP Stream</h1>
          
          <div className="flex gap-4 mb-4">
            <Input
              type="text"
              value={rtspUrl}
              onChange={(e) => setRtspUrl(e.target.value)}
              placeholder="Enter RTSP URL"
              className="flex-1"
            />
            <Button 
              onClick={startStream}
              className="min-w-[100px] bg-blue-500 hover:bg-blue-600"
            >
              Start
            </Button>
            <Button
              onClick={showWebcam ? stopWebcam : startWebcam}
              className={`min-w-[100px] ${showWebcam ? 'bg-red-500 hover:bg-red-600' : 'bg-green-500 hover:bg-green-600'}`}
            >
              {showWebcam ? 'Stop Webcam' : 'Start Webcam'}
            </Button>
          </div>

          <div className="aspect-video bg-gray-200 rounded-lg overflow-hidden relative">
            <video
                ref={videoRef}
                autoPlay
                playsInline
                className="hidden"
            />
            <canvas
                ref={canvasRef}
                width={1280}
                height={720}
                className="hidden"
            />
            
            {webcamTaskId && (
                <Image
                    src={`${API_CONFIG.BASE_URL}/api/webcam/${webcamTaskId}`}
                    alt="Processed Webcam"
                    className="w-full h-full object-cover"
                    width={1280}
                    height={720}
                    unoptimized
                    priority
                />
            )}
            
            {!showWebcam && imageUrl && (
                <Image
                    src={imageUrl}
                    alt="RTSP Stream"
                    className="w-full h-full object-cover"
                    width={1280}
                    height={720}
                    unoptimized
                    onError={handleImageError}
                    onLoad={handleImageLoad}
                />
            )}
          </div>

          <div className="mb-4">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Task ID</TableHead>
                  <TableHead className="w-[100px]">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {activeStreams.map((taskId) => (
                  <TableRow key={taskId}>
                    <TableCell className="font-mono text-sm">{taskId}</TableCell>
                    <TableCell>
                      <Button
                        onClick={() => stopStream(taskId)}
                        variant="destructive"
                        size="sm"
                      >
                        Stop
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </div>
      </div>
    </div>
  )
}

