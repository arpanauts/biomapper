import { useState, useEffect, ChangeEvent } from 'react';
import axios from 'axios';

export default function TestApp() {
  const [healthStatus, setHealthStatus] = useState<string>('Checking...');
  const [error, setError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadStatus, setUploadStatus] = useState<string>('');
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);

  useEffect(() => {
    // Test the API connection
    axios.get('http://localhost:8000/api/health/check')
      .then(response => {
        console.log('Health check response:', response.data);
        setHealthStatus('API Connected: ' + JSON.stringify(response.data));
      })
      .catch(err => {
        console.error('Health check error:', err);
        setError(err.message || 'Unknown error');
        setHealthStatus('Failed to connect to API');
      });
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

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const response = await axios.post('http://localhost:8000/api/files/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      console.log('Upload response:', response.data);
      setUploadStatus('Upload successful!');
      setSessionId(response.data.session_id);
    } catch (err: any) {
      console.error('Upload error:', err);
      setUploadError(err.message || 'Unknown error');
      setUploadStatus('Upload failed');
    }
  };

  return (
    <div style={{ padding: '20px', maxWidth: '800px', margin: '0 auto' }}>
      <h1>Biomapper Test Page</h1>
      <p>This is a simple test component to verify React rendering and API connectivity.</p>
      
      <div style={{ border: '1px solid #ccc', padding: '10px', margin: '20px 0' }}>
        <p>If you can see this, basic React rendering is working correctly.</p>
      </div>

      <div style={{ marginTop: '20px', padding: '15px', background: '#f5f5f5', borderRadius: '4px' }}>
        <h3>API Connection Test</h3>
        <p><strong>Status:</strong> {healthStatus}</p>
        {error && (
          <div style={{ color: 'red', marginTop: '10px' }}>
            <p><strong>Error:</strong> {error}</p>
            <p>This could be a CORS issue or the API server might not be running.</p>
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
          Upload File
        </button>
        
        {uploadStatus && <p><strong>{uploadStatus}</strong></p>}
        {uploadError && <p style={{ color: 'red' }}><strong>Error:</strong> {uploadError}</p>}
        {sessionId && <p><strong>Session ID:</strong> {sessionId}</p>}
      </div>
    </div>
  );
}
