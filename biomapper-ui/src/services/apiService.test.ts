import { apiService } from './apiService';

describe('API Service', () => {
  describe('startMapping', () => {
    it('should successfully start a mapping with valid configuration', async () => {
      const mockConfig = {
        sessionId: 'test-session-123',
        sourceColumn: 'protein_ids',
        targetDataSource: 'uniprot',
        strategy: 'direct_mapping',
        parameters: { timeout: 30 }
      };

      const result = await apiService.startMapping(mockConfig);

      expect(result).toHaveProperty('jobId');
      expect(result).toHaveProperty('status', 'pending');
      expect(result).toHaveProperty('message', 'Mapping job created successfully');
      expect(result.jobId).toMatch(/^job-\d+-[a-z0-9]+$/);
    });

    it('should throw error for missing required parameters', async () => {
      const invalidConfig = {
        sessionId: '',
        sourceColumn: 'protein_ids',
        targetDataSource: 'uniprot',
        strategy: 'direct_mapping'
      };

      await expect(apiService.startMapping(invalidConfig)).rejects.toThrow(
        'Missing required configuration parameters'
      );
    });

    it('should throw error for missing source column', async () => {
      const invalidConfig = {
        sessionId: 'test-session-123',
        sourceColumn: '',
        targetDataSource: 'uniprot',
        strategy: 'direct_mapping'
      };

      await expect(apiService.startMapping(invalidConfig)).rejects.toThrow(
        'Missing required configuration parameters'
      );
    });

    it('should throw error for missing target data source', async () => {
      const invalidConfig = {
        sessionId: 'test-session-123',
        sourceColumn: 'protein_ids',
        targetDataSource: '',
        strategy: 'direct_mapping'
      };

      await expect(apiService.startMapping(invalidConfig)).rejects.toThrow(
        'Missing required configuration parameters'
      );
    });
  });

  describe('uploadFile', () => {
    it('should throw not implemented error', async () => {
      const mockFile = new File(['test'], 'test.csv', { type: 'text/csv' });
      
      await expect(apiService.uploadFile(mockFile)).rejects.toThrow(
        'Not implemented - see Prompt 02'
      );
    });
  });

  describe('getColumns', () => {
    it('should throw not implemented error', async () => {
      await expect(apiService.getColumns('test-session')).rejects.toThrow(
        'Not implemented - see Prompt 02'
      );
    });
  });

  describe('getJobStatus', () => {
    it('should throw not implemented error', async () => {
      await expect(apiService.getJobStatus('test-job')).rejects.toThrow(
        'Not implemented - see Prompt 02'
      );
    });
  });

  describe('getResults', () => {
    it('should throw not implemented error', async () => {
      await expect(apiService.getResults('test-job')).rejects.toThrow(
        'Not implemented - see Prompt 02'
      );
    });
  });
});