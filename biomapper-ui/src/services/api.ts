import axios from 'axios';

// Create axios instance with base configuration
export const apiClient = axios.create({
  baseURL: 'http://localhost:8000/api',
  headers: {
    'Content-Type': 'application/json',
  },
  // Add timeout and better response handling
  timeout: 30000,
  // Important - don't transform the response when uploading files
  transformResponse: [(data) => {
    try {
      // Only parse JSON if it's a string
      return typeof data === 'string' ? JSON.parse(data) : data;
    } catch (error) {
      // If parsing fails, just return the raw data
      console.warn('Failed to parse response as JSON, returning raw data');
      return data;
    }
  }],
});

// Add response interceptor to handle network errors better
apiClient.interceptors.response.use(
  response => response,
  error => {
    console.error('API request failed:', error);
    if (error.response) {
      // The request was made and the server responded with a status code
      // that falls out of the range of 2xx
      console.error('Response error data:', error.response.data);
      console.error('Response error status:', error.response.status);
      console.error('Response error headers:', error.response.headers);
    } else if (error.request) {
      // The request was made but no response was received
      console.error('No response received:', error.request);
    } else {
      // Something happened in setting up the request that triggered an Error
      console.error('Request setup error:', error.message);
    }
    return Promise.reject(error);
  }
);

// File related API calls
export const fileApi = {
  // List files available on the server in a specified directory
  listServerFiles: async (directoryPath: string, extensions?: string[]) => {
    try {
      console.log('API Service: Listing server files in directory:', directoryPath);
      
      const response = await apiClient.post('/files/server/list', {
        directory_path: directoryPath,
        extensions: extensions || ['.csv', '.tsv']
      });
      
      console.debug('Server files response:', response.data);
      return response.data;
    } catch (error) {
      console.error('Error listing server files:', error);
      throw error;
    }
  },

  // Load a file from the server filesystem
  loadServerFile: async (filePath: string) => {
    try {
      console.log('API Service: Loading server file:', filePath);
      
      // Log detailed request for debugging
      console.debug('Request payload:', { file_path: filePath });
      
      const response = await apiClient.post('/files/server/load', {
        file_path: filePath
      });
      
      console.debug('Load server file response:', response.data);
      return response.data;
    } catch (error: any) {
      // Enhanced error logging
      console.error('Error loading server file:', error);
      if (error.response) {
        console.error('Server response:', error.response.data);
        console.error('Status code:', error.response.status);
      }
      throw error;
    }
  },
  
  // Upload a file to the server with progress tracking
  uploadFile: async (file: File, onProgress?: (progressEvent: ProgressEvent) => void) => {
    try {
      console.log('API Service: Uploading file:', file.name, 'size:', file.size);
      
      const formData = new FormData();
      formData.append('file', file);
      
      console.log('API Service: Making API request to /files/upload...');
      
      // If progress callback provided, use XMLHttpRequest for better progress tracking
      if (onProgress) {
        // Return a promise that wraps XMLHttpRequest for progress reporting
        return new Promise((resolve, reject) => {
          const xhr = new XMLHttpRequest();
          
          // Set up progress handler
          xhr.upload.addEventListener('progress', onProgress);
          
          xhr.addEventListener('load', () => {
            if (xhr.status >= 200 && xhr.status < 300) {
              try {
                const data = JSON.parse(xhr.responseText);
                console.log('API Service: Upload response data:', data);
                
                // Validate the response data
                if (!data || !data.session_id) {
                  console.error('API Service: Invalid response data:', data);
                  reject(new Error('Invalid response data from server'));
                } else {
                  resolve(data);
                }
              } catch (e) {
                reject(new Error('Failed to parse server response'));
              }
            } else {
              reject(new Error(`Upload failed with status: ${xhr.status}`));
            }
          });
          
          xhr.addEventListener('error', () => reject(new Error('Network error during upload')));
          xhr.addEventListener('abort', () => reject(new Error('Upload aborted')));
          
          xhr.open('POST', 'http://localhost:8000/api/files/upload');
          xhr.send(formData);
        });
      } else {
        // Fall back to fetch API when no progress tracking needed
        const response = await fetch('http://localhost:8000/api/files/upload', {
          method: 'POST',
          body: formData,
          // Don't set Content-Type header - fetch will set it with the correct boundary
        });
        
        if (!response.ok) {
          throw new Error(`Upload failed with status: ${response.status}`);
        }
        
        // Parse the JSON response
        const data = await response.json();
        console.log('API Service: Upload response data:', data);
        
        // Validate the response data
        if (!data || !data.session_id) {
          console.error('API Service: Invalid response data:', data);
          throw new Error('Invalid response data from server');
        }
        
        return data;
      }

    } catch (error) {
      console.error('API Service: Upload error details:', error);
      // Re-throw the error for the component to handle
      throw error;
    }
  },
  
  // Get columns from an uploaded file
  getColumns: async (sessionId: string) => {
    // Keep console logs but remove visible debug element
    const logDebug = (msg: string) => {
      console.debug(`API Debug: ${msg}`);
    };
    
    try {
      console.log('API Service: Getting columns for session', sessionId);
      logDebug(`Making request to columns API`);
      
      // Use fetch directly instead of axios for more direct control
      const url = `http://localhost:8000/api/files/${sessionId}/columns`;
      console.log('API Service: Making request to', url);
      logDebug(`URL: ${url}`);
      
      const response = await fetch(url);
      console.log('API Service: Column response status:', response.status);
      logDebug(`Response status: ${response.status}`);
      
      if (!response.ok) {
        logDebug(`Error: ${response.status} ${response.statusText}`);
        throw new Error(`Failed to retrieve columns: ${response.status} ${response.statusText}`);
      }
      
      const responseText = await response.text();
      logDebug(`Raw response: ${responseText.substring(0, 50)}...`);
      
      // Manually parse to better handle errors
      let data;
      try {
        data = JSON.parse(responseText);
        console.log('API Service: Column data received:', data);
        logDebug(`Data parsed successfully`);
      } catch (parseError: unknown) {
        const errorMessage = parseError instanceof Error ? parseError.message : String(parseError);
        logDebug(`JSON parse error: ${errorMessage}`);
        throw new Error(`Invalid JSON response: ${errorMessage}`);
      }
      
      if (!data || !data.columns) {
        console.error('API Service: Column data is missing expected format:', data);
        logDebug(`Missing columns in response: ${JSON.stringify(data)}`);
        throw new Error('Invalid column data format');
      }
      
      logDebug(`Success! Found ${data.columns.length} columns`);
      return data;
    } catch (error: unknown) {
      console.error('API Service: Error getting columns:', error);
      const errorMessage = error instanceof Error ? error.message : String(error);
      logDebug(`Critical error: ${errorMessage}`);
      throw error;
    }
  },
  
  // Get a preview of the CSV data
  getPreview: async (sessionId: string) => {
    try {
      console.log('API Service: Getting preview for session', sessionId);
      
      // Use fetch directly instead of axios for more direct control
      const url = `http://localhost:8000/api/files/${sessionId}/preview`;
      console.log('API Service: Making preview request to', url);
      
      const response = await fetch(url);
      console.log('API Service: Preview response status:', response.status);
      
      if (!response.ok) {
        throw new Error(`Failed to retrieve preview: ${response.status} ${response.statusText}`);
      }
      
      const data = await response.json();
      console.log('API Service: Preview data received:', data);
      
      return data;
    } catch (error) {
      console.error('API Service: Error getting preview:', error);
      throw error;
    }
  },
};

// Mapping related API calls
export const mappingApi = {
  // Create a new mapping job
  createMappingJob: async (
    sessionId: string, 
    idColumn: string, 
    targetOntology: string,
    mappingOptions?: Record<string, any>
  ) => {
    const response = await apiClient.post('/mapping/jobs', {
      session_id: sessionId,
      id_column: idColumn,
      target_ontology: targetOntology,
      mapping_options: mappingOptions || {},
    });
    
    return response.data;
  },
  
  // Check job status
  getJobStatus: async (jobId: string) => {
    const response = await apiClient.get(`/mapping/jobs/${jobId}/status`);
    return response.data;
  },
  
  // Get mapping results
  getResults: async (jobId: string) => {
    const response = await apiClient.get(`/mapping/jobs/${jobId}/results`);
    return response.data;
  },
  
  // Get download URL for results
  getDownloadUrl: (jobId: string) => {
    return `${apiClient.defaults.baseURL}/mapping/jobs/${jobId}/download`;
  },
};

// Health check
export const healthApi = {
  checkHealth: async () => {
    try {
      console.log('Making health check request...');
      const response = await apiClient.get('/health/');
      console.log('Health check response:', response.data);
      return response.data;
    } catch (error) {
      console.error('Health check error:', error);
      throw error;
    }
  },
};

export default {
  fileApi,
  mappingApi,
  healthApi,
};
