const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const API_CONFIG = {
    BASE_URL,
    ENDPOINTS: {
        STREAM: '/api/stream',
        STOP_STREAM: '/api/stop-stream'
    }
}; 