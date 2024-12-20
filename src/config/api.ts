const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const API_CONFIG = {
    BASE_URL,
    ENDPOINTS: {
        STREAM: '/stream',
        STOP_STREAM: '/stop-stream',
        ACTIVE_STREAMS: '/active-streams'
    }
}; 