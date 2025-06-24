import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import axios from 'axios';
import {
  healthCheck,
  uploadFile,
  getColumns,
  startMapping,
  getMappingStatus,
  apiClient,
} from './apiService';

// Mock axios
vi.mock('axios');

describe('API Service', () => {
  let mockAxiosInstance: any;

  beforeEach(() => {
    // Create a mock axios instance
    mockAxiosInstance = {
      get: vi.fn(),
      post: vi.fn(),
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() },
      },
    };

    // Mock axios.create to return our mock instance
    (axios.create as any).mockReturnValue(mockAxiosInstance);

    // Re-import the module to get fresh instance
    vi.resetModules();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('healthCheck', () => {
    it('should return health status on success', async () => {
      const mockResponse = {
        data: { status: 'healthy', version: '1.0.0', timestamp: '2024-01-01T00:00:00Z' },
      };
      mockAxiosInstance.get.mockResolvedValue(mockResponse);

      const result = await healthCheck();

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/api/health');
      expect(result).toEqual(mockResponse.data);
    });

    it('should throw error on failure', async () => {
      const mockError = new Error('Network error');
      mockAxiosInstance.get.mockRejectedValue(mockError);

      await expect(healthCheck()).rejects.toThrow('Network error');
      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/api/health');
    });
  });

  describe('uploadFile', () => {
    it('should upload file and return session info', async () => {
      const mockFile = new File(['test content'], 'test.csv', { type: 'text/csv' });
      const mockResponse = {
        data: { session_id: 'session-123', filename: 'test.csv' },
      };
      mockAxiosInstance.post.mockResolvedValue(mockResponse);

      const result = await uploadFile(mockFile);

      expect(mockAxiosInstance.post).toHaveBeenCalledWith(
        '/api/sessions/upload',
        expect.any(FormData),
        expect.objectContaining({
          headers: { 'Content-Type': 'multipart/form-data' },
        })
      );
      expect(result).toEqual(mockResponse.data);
    });

    it('should handle upload errors', async () => {
      const mockFile = new File(['test content'], 'test.csv', { type: 'text/csv' });
      const mockError = new Error('Upload failed');
      mockAxiosInstance.post.mockRejectedValue(mockError);

      await expect(uploadFile(mockFile)).rejects.toThrow('Upload failed');
    });
  });

  describe('getColumns', () => {
    it('should return column names for a session', async () => {
      const sessionId = 'session-123';
      const mockResponse = {
        data: ['column1', 'column2', 'column3'],
      };
      mockAxiosInstance.get.mockResolvedValue(mockResponse);

      const result = await getColumns(sessionId);

      expect(mockAxiosInstance.get).toHaveBeenCalledWith(`/api/sessions/${sessionId}/columns`);
      expect(result).toEqual(mockResponse.data);
    });

    it('should handle errors when getting columns', async () => {
      const sessionId = 'session-123';
      const mockError = new Error('Session not found');
      mockAxiosInstance.get.mockRejectedValue(mockError);

      await expect(getColumns(sessionId)).rejects.toThrow('Session not found');
    });
  });

  describe('startMapping', () => {
    it('should start mapping and return job ID', async () => {
      const sessionId = 'session-123';
      const config = {
        strategy: 'protein_mapping',
        source_column: 'protein_ids',
        target_type: 'uniprot',
      };
      const mockResponse = {
        data: { job_id: 'job-456' },
      };
      mockAxiosInstance.post.mockResolvedValue(mockResponse);

      const result = await startMapping(sessionId, config);

      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/api/strategies/execute', {
        session_id: sessionId,
        ...config,
      });
      expect(result).toEqual(mockResponse.data);
    });

    it('should handle mapping start errors', async () => {
      const sessionId = 'session-123';
      const config = { strategy: 'invalid' };
      const mockError = new Error('Invalid strategy');
      mockAxiosInstance.post.mockRejectedValue(mockError);

      await expect(startMapping(sessionId, config)).rejects.toThrow('Invalid strategy');
    });
  });

  describe('getMappingStatus', () => {
    it('should return mapping status and results', async () => {
      const jobId = 'job-456';
      const mockResponse = {
        data: {
          status: 'completed',
          results: { mapped: 100, unmapped: 5 },
        },
      };
      mockAxiosInstance.get.mockResolvedValue(mockResponse);

      const result = await getMappingStatus(jobId);

      expect(mockAxiosInstance.get).toHaveBeenCalledWith(`/api/mappings/${jobId}`);
      expect(result).toEqual(mockResponse.data);
    });

    it('should return error status when mapping fails', async () => {
      const jobId = 'job-456';
      const mockResponse = {
        data: {
          status: 'failed',
          error: 'Mapping process failed',
        },
      };
      mockAxiosInstance.get.mockResolvedValue(mockResponse);

      const result = await getMappingStatus(jobId);

      expect(result.status).toBe('failed');
      expect(result.error).toBe('Mapping process failed');
    });

    it('should handle network errors', async () => {
      const jobId = 'job-456';
      const mockError = new Error('Network timeout');
      mockAxiosInstance.get.mockRejectedValue(mockError);

      await expect(getMappingStatus(jobId)).rejects.toThrow('Network timeout');
    });
  });

  describe('axios interceptors', () => {
    it('should set up request and response interceptors', () => {
      expect(mockAxiosInstance.interceptors.request.use).toHaveBeenCalled();
      expect(mockAxiosInstance.interceptors.response.use).toHaveBeenCalled();
    });
  });
});