import { useState, useEffect, ChangeEvent } from 'react';
import axios from 'axios';
import { fileApi, healthApi } from './services/api';

export default function TestAPI() {
  const [healthStatus, setHealthStatus] = useState<string>('Checking...');
  const [error, setError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadStatus, setUploadStatus] = useState<string>('');
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);

  // Test direct axios call to backend
  const testDirectCall = async (endpoint: string) => {
    try {
      console.log(`Testing direct call to ${endpoint}`);
      const response = await axios.get(endpoint);
      console.log('Direct call response:', response.data);
      return { success: true, data: response.data };
    } catch (err: any) {
      console.error('Direct call error:', err);
      return { success: false, error: err.message };
    }
  };

  useEffect(() => {
    const runTests = async () => {
      try {
        // Test the API connection using our service
        const healthResult = await healthApi.checkHealth();
        setHealthStatus(`API Connected: ${JSON.stringify(healthResult)}`);
      } catch (err: any) {
        setError(err.message || 'Unknown error');
        setHealthStatus('Failed to connect to API via service');
        
        // Try direct calls as fallback
        const directHealthResult = await testDirectCall('http://localhost:8000/api/health/');
        if (directHealthResult.success) {
          setHealthStatus(`Direct API connection working: ${JSON.stringify(directHealthResult.data)}`);
        }
      }
    };
    
    runTests();
  }, []);

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setSelectedFile(e.target.files[0]);
      setUploadStatus('');
      setUploadError(null);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setUploadError('Please select a file first');
      return;
    }

    setUploadStatus('Uploading...');
    setUploadError(null);

    try {
      // Test with direct axios call first
      const formData = new FormData();
      formData.append('file', selectedFile);
      
      // First try direct upload
      try {
        setUploadStatus('Testing direct upload...');
        const directResponse = await axios.post('http://localhost:8000/api/files/upload', formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        });
        console.log('Direct upload response:', directResponse.data);
        setUploadStatus('Direct upload successful!');
        setSessionId(directResponse.data.session_id);
      } catch (directErr: any) {
        console.error('Direct upload failed:', directErr);
        setUploadStatus('Direct upload failed, trying through service...');
        
        // Try through service
        const response = await fileApi.uploadFile(selectedFile);
        console.log('Service upload response:', response);
        setUploadStatus('Upload successful through service!');
        setSessionId(response.session_id);
      }
    } catch (err: any) {
      console.error('All upload attempts failed:', err);
      setUploadError(err.message || 'Unknown error');
      setUploadStatus('Upload failed');
    }
  };

  return (
    <div style={{ padding: '20px', maxWidth: '800px', margin: '0 auto' }}>
      <h1>Biomapper API Test</h1>
      <p>This is a test component to debug API connectivity issues.</p>
      
      <div style={{ marginTop: '20px', padding: '15px', background: '#f5f5f5', borderRadius: '4px' }}>
        <h3>API Connection Test</h3>
        <p><strong>Status:</strong> {healthStatus}</p>
        {error && (
          <div style={{ color: 'red', marginTop: '10px' }}>
            <p><strong>Error:</strong> {error}</p>
          </div>
        )}
      </div>

      <div style={{ marginTop: '20px', padding: '15px', border: '1px solid #ddd', borderRadius: '4px' }}>
        <h3>File Upload Test</h3>
        <div style={{ marginBottom: '15px' }}>
          <input type="file" onChange={handleFileChange} accept=".csv" />
          {selectedFile && <p>Selected: {selectedFile.name}</p>}
        </div>
        
        <button 
          onClick={handleUpload}
          style={{
            padding: '8px 16px',
            backgroundColor: '#4CAF50',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer'
          }}
        >
          Test Upload
        </button>
        
        {uploadStatus && <p><strong>{uploadStatus}</strong></p>}
        {uploadError && <p style={{ color: 'red' }}><strong>Error:</strong> {uploadError}</p>}
        {sessionId && <p><strong>Session ID:</strong> {sessionId}</p>}
      </div>
    </div>
  );
}
