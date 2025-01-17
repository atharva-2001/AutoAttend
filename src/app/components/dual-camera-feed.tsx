'use client'

import { useState, useEffect } from 'react'
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

          <div className="aspect-video bg-gray-200 rounded-lg overflow-hidden">
            {imageUrl ? (
              <Image
                key={imageUrl}
                src={imageUrl}
                alt="RTSP Stream"
                className="w-full h-full object-cover"
                width={1280}
                height={720}
                unoptimized
                onError={handleImageError}
                onLoad={handleImageLoad}
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center text-gray-500">
                {imageError ? "Stream failed to load" : "Stream is stopped"}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

