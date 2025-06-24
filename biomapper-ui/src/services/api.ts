import axios from 'axios';

// Create axios instance with base configuration
export const apiClient = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

// Add response interceptor for error handling
apiClient.interceptors.response.use(
  response => response,
  error => {
    console.error('API request failed:', error);
    return Promise.reject(error);
  }
);

// API service methods
export const apiService = {
  // Get columns from an uploaded file
  getColumns: async (sessionId: string) => {
    const response = await apiClient.get(`/sessions/${sessionId}/columns`);
    return response.data;
  },

  // Get session information
  getSession: async (sessionId: string) => {
    const response = await apiClient.get(`/sessions/${sessionId}`);
    return response.data;
  },

  // Create mapping job
  createMappingJob: async (sessionId: string, columns: string[], config: any) => {
    const response = await apiClient.post('/mapping/jobs', {
      session_id: sessionId,
      columns,
      config,
    });
    return response.data;
  },

  // Get job status
  getJobStatus: async (jobId: string) => {
    const response = await apiClient.get(`/mapping/jobs/${jobId}/status`);
    return response.data;
  },

  // Get mapping results
  getResults: async (jobId: string) => {
    const response = await apiClient.get(`/mapping/jobs/${jobId}/results`);
    return response.data;
  },
};

export default apiService;