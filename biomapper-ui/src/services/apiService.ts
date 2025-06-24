import axios, { AxiosInstance, AxiosError } from 'axios';

// Types for API responses
interface HealthCheckResponse {
  status: string;
  version?: string;
  timestamp?: string;
}

interface UploadResponse {
  session_id: string;
  filename: string;
}

interface MappingJobResponse {
  job_id: string;
}

interface MappingStatusResponse {
  status: string;
  results?: any;
  error?: string;
}

// Create axios instance with base configuration
const apiClient: AxiosInstance = axios.create({
  baseURL: process.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for debugging
apiClient.interceptors.request.use(
  (config) => {
    console.log(`Making ${config.method?.toUpperCase()} request to ${config.url}`);
    return config;
  },
  (error) => {
    console.error('Request error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  (error: AxiosError) => {
    if (error.response) {
      // Server responded with error status
      console.error('Response error:', error.response.data);
      console.error('Status:', error.response.status);
    } else if (error.request) {
      // Request was made but no response received
      console.error('No response received:', error.request);
    } else {
      // Something else happened
      console.error('Error:', error.message);
    }
    return Promise.reject(error);
  }
);

// API service functions

/**
 * Check the health status of the API
 * @returns Promise with health status information
 */
export async function healthCheck(): Promise<HealthCheckResponse> {
  try {
    const response = await apiClient.get<HealthCheckResponse>('/api/health');
    return response.data;
  } catch (error) {
    console.error('Health check failed:', error);
    throw error;
  }
}

/**
 * Upload a file to create a new session
 * @param file - The file to upload
 * @returns Promise with session ID and filename
 */
export async function uploadFile(file: File): Promise<UploadResponse> {
  try {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post<UploadResponse>('/api/sessions/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    
    return response.data;
  } catch (error) {
    console.error('File upload failed:', error);
    throw error;
  }
}

/**
 * Get available columns from an uploaded file
 * @param sessionId - The session ID from file upload
 * @returns Promise with array of column names
 */
export async function getColumns(sessionId: string): Promise<string[]> {
  try {
    const response = await apiClient.get<string[]>(`/api/sessions/${sessionId}/columns`);
    return response.data;
  } catch (error) {
    console.error('Failed to get columns:', error);
    throw error;
  }
}

/**
 * Start a mapping job with the provided configuration
 * @param sessionId - The session ID from file upload
 * @param config - The mapping configuration (strategy, parameters, etc.)
 * @returns Promise with job ID
 */
export async function startMapping(sessionId: string, config: any): Promise<MappingJobResponse> {
  try {
    const response = await apiClient.post<MappingJobResponse>('/api/strategies/execute', {
      session_id: sessionId,
      ...config,
    });
    
    return response.data;
  } catch (error) {
    console.error('Failed to start mapping:', error);
    throw error;
  }
}

/**
 * Get the status and results of a mapping job
 * @param jobId - The job ID from startMapping
 * @returns Promise with job status and results
 */
export async function getMappingStatus(jobId: string): Promise<MappingStatusResponse> {
  try {
    const response = await apiClient.get<MappingStatusResponse>(`/api/mappings/${jobId}`);
    return response.data;
  } catch (error) {
    console.error('Failed to get mapping status:', error);
    throw error;
  }
}

// Export the axios instance for advanced usage
export { apiClient };