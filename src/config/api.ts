export const API_CONFIG = {
    BASE_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
    WS_URL: process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000',
    ENDPOINTS: {
        STREAM: '/stream',
        STOP_STREAM: '/stop-stream',
        ACTIVE_STREAMS: '/active-streams',
        WEBCAM: '/webcam'
    }
}; 