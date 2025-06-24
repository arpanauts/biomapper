import { useState } from 'react';
import { Button, Paper, Text, Title } from '@mantine/core';
import { notifications } from '@mantine/notifications';

export default function TestAppSimple() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [status, setStatus] = useState<string>('Ready to test');
  const [error, setError] = useState<string | null>(null);
  
  const handleUploadTest = async () => {
    try {
      setStatus('Preparing test file...');
      setError(null);
      
      // Create a test CSV file
      const csvContent = 'ID,Name,Value\n1,Test1,100\n2,Test2,200';
      const blob = new Blob([csvContent], { type: 'text/csv' });
      const file = new File([blob], 'test.csv', { type: 'text/csv' });
      
      // Create form data
      const formData = new FormData();
      formData.append('file', file);
      
      setStatus('Uploading test file...');
      
      // Make a direct fetch request with the correct API URL
      const apiUrl = 'http://localhost:8000/api/files/upload';
      console.log('Sending upload request to backend:', apiUrl);
      const response = await fetch(apiUrl, {
        method: 'POST',
        body: formData
      });
      
      console.log('Response received:', response);
      console.log('Response status:', response.status);
      console.log('Response headers:', [...response.headers.entries()]);
      
      if (!response.ok) {
        throw new Error(`Upload failed with status: ${response.status}`);
      }
      
      console.log('Reading response body...');
      const responseText = await response.text();
      console.log('Raw response text:', responseText);
      setStatus(`Got response (${responseText.length} chars)`)
      
      // Check if response is empty
      if (!responseText.trim()) {
        console.error('Empty response received from server');
        setError('Server returned an empty response');
        setStatus('Test failed - empty response');
        return;
      }
      
      // Try parsing as JSON, but handle the case where it's not valid JSON
      let jsonData;
      try {
        console.log('Attempting to parse response as JSON...');
        jsonData = JSON.parse(responseText);
        console.log('Parsed JSON data:', jsonData);
      } catch (parseError) {
        console.error('Failed to parse response as JSON:', parseError);
        setError(`Response is not valid JSON: ${responseText}`);
        setStatus('Test failed - invalid JSON response');
        return;
      }
      
      // Validate and extract the session ID
      if (!jsonData || !jsonData.session_id) {
        setError(`Response missing session_id: ${JSON.stringify(jsonData)}`);
        setStatus('Test failed - missing session ID');
        return;
      }
      
      setSessionId(jsonData.session_id);
      setStatus(`Test passed! Session ID: ${jsonData.session_id}`);
      
      notifications.show({
        title: 'Success',
        message: 'File uploaded and session ID received',
        color: 'green',
      });
    } catch (error) {
      console.error('Test error:', error);
      setError(error instanceof Error ? error.message : 'Unknown error');
      setStatus('Test failed');
      
      notifications.show({
        title: 'Error',
        message: `Test failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
        color: 'red',
      });
    }
  };
  
  return (
    <Paper p="xl" radius="md">
      <Title order={2} mb="lg">Biomapper Upload Test</Title>
      
      <Text mb="md">Status: {status}</Text>
      
      {error && (
        <Text mb="md" color="red">Error: {error}</Text>
      )}
      
      {sessionId && (
        <Text mb="md" color="green">Session ID: {sessionId}</Text>
      )}
      
      <Button 
        onClick={handleUploadTest}
        variant="filled"
        color="blue"
        size="lg"
        mt="md"
      >
        Run Upload Test
      </Button>
    </Paper>
  );
}
