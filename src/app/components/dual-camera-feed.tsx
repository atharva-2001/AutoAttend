'use client'

import { useState, useEffect } from 'react'
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { API_CONFIG } from '@/config/api'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"

export default function DualCameraFeed() {
  const [isStreaming, setIsStreaming] = useState(false)
  const [rtspUrl, setRtspUrl] = useState("rtsp://admin:IRMAXS@192.168.31.131:554/ch1/main")
  const [imageUrl, setImageUrl] = useState("")
  const [activeStreams, setActiveStreams] = useState<string[]>([])

  const fetchActiveStreams = async () => {
    try {
      const response = await fetch(`${API_CONFIG.BASE_URL}/api/active-streams`)
      if (response.ok) {
        const data = await response.json()
        setActiveStreams(data.streams)
      }
    } catch (error) {
      console.error("Error fetching active streams:", error)
    }
  }

  useEffect(() => {
    // Fetch active streams every 5 seconds
    const interval = setInterval(fetchActiveStreams, 5000)
    return () => clearInterval(interval)
  }, [])

  const startStream = async () => {
    try {
      const response = await fetch(
        `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.STREAM}?rtsp_url=${encodeURIComponent(rtspUrl)}`
      )
      if (response.ok) {
        const streamUrl = `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.STREAM}?rtsp_url=${encodeURIComponent(rtspUrl)}`
        setImageUrl(streamUrl)
        setIsStreaming(true)
        fetchActiveStreams() // Refresh the list immediately
      }
    } catch (error) {
      console.error("Error starting stream:", error)
    }
  }

  const stopStream = async (streamUrl: string) => {
    try {
      const response = await fetch(
        `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.STOP_STREAM}?rtsp_url=${encodeURIComponent(streamUrl)}`,
        { method: 'POST' }
      )
      if (response.ok) {
        if (streamUrl === rtspUrl) {
          setImageUrl("")
          setIsStreaming(false)
        }
        fetchActiveStreams() // Refresh the list immediately
      }
    } catch (error) {
      console.error("Error stopping stream:", error)
    }
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
                  <TableHead>Stream URL</TableHead>
                  <TableHead className="w-[100px]">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {activeStreams.map((stream) => (
                  <TableRow key={stream}>
                    <TableCell className="font-mono text-sm">{stream}</TableCell>
                    <TableCell>
                      <Button
                        onClick={() => stopStream(stream)}
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
              <img
                src={imageUrl}
                alt="RTSP Stream"
                className="w-full h-full object-cover"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center text-gray-500">
                Stream is stopped
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

