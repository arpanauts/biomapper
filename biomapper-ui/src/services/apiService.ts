// Mock API Service - to be implemented in Prompt 02
// This is a temporary implementation for testing the MappingConfig component

interface MappingConfig {
  sessionId: string;
  sourceColumn: string;
  targetDataSource: string;
  strategy: string;
  parameters?: Record<string, any>;
}

interface MappingResult {
  jobId: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  message?: string;
}

export const apiService = {
  // Start a mapping process with the given configuration
  startMapping: async (config: MappingConfig): Promise<MappingResult> => {
    console.log('Mock apiService.startMapping called with:', config);
    
    // Simulate API call delay
    await new Promise(resolve => setTimeout(resolve, 500));
    
    // Mock validation
    if (!config.sessionId || !config.sourceColumn || !config.targetDataSource) {
      throw new Error('Missing required configuration parameters');
    }
    
    // Return mock successful response
    return {
      jobId: `job-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      status: 'pending',
      message: 'Mapping job created successfully'
    };
  },
  
  // Other API methods to be implemented in Prompt 02
  uploadFile: async (_file: File) => {
    throw new Error('Not implemented - see Prompt 02');
  },
  
  getColumns: async (sessionId: string) => {
    console.log('Mock apiService.getColumns called with sessionId:', sessionId);
    
    // Simulate API call delay
    await new Promise(resolve => setTimeout(resolve, 300));
    
    // Mock validation
    if (!sessionId) {
      throw new Error('Session ID is required');
    }
    
    // Return mock columns data
    return {
      columns: ['id', 'name', 'email', 'age', 'city', 'country', 'protein_id', 'gene_symbol', 'expression_level']
    };
  },
  
  getJobStatus: async (_jobId: string) => {
    throw new Error('Not implemented - see Prompt 02');
  },
  
  getResults: async (_jobId: string) => {
    throw new Error('Not implemented - see Prompt 02');
  }
};