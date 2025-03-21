import { useState } from 'react';
import { 
  Button, 
  Card, 
  Group, 
  Paper, 
  Text, 
  Title, 
  Stack,
  Code 
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { fileApi } from './services/api';

export default function DiagnosticApp() {
  const [sessionId, setSessionId] = useState<string>('');
  const [logs, setLogs] = useState<string[]>([]);
  const [columns, setColumns] = useState<string[] | null>(null);
  const [columnError, setColumnError] = useState<string | null>(null);
  const [step, setStep] = useState<'input' | 'test'>('input');

  const addLog = (message: string) => {
    console.log(message);
    setLogs(prev => [...prev, `[${new Date().toISOString()}] ${message}`]);
  };

  // Function to test column retrieval
  const testColumnSelection = async () => {
    if (!sessionId) {
      notifications.show({
        title: 'Error',
        message: 'Please enter a session ID',
        color: 'red',
      });
      return;
    }

    setStep('test');
    addLog(`Starting test with session ID: ${sessionId}`);
    
    // Test that the session ID is in the expected format (UUID)
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    if (!uuidRegex.test(sessionId)) {
      addLog(`⚠️ Warning: Session ID doesn't look like a valid UUID`);
    } else {
      addLog(`✅ Session ID format looks valid`);
    }

    try {
      addLog('Attempting to retrieve columns from API...');
      const response = await fileApi.getColumns(sessionId);
      addLog(`API Response: ${JSON.stringify(response)}`);
      
      if (response?.columns) {
        setColumns(response.columns);
        addLog(`✅ Successfully retrieved ${response.columns.length} columns`);
      } else {
        setColumnError('No columns returned from API');
        addLog('⚠️ Response did not contain columns array');
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      setColumnError(errorMessage);
      addLog(`❌ Error retrieving columns: ${errorMessage}`);
      
      // Suggest potential solutions
      if (errorMessage.includes('404')) {
        addLog('This may indicate the session ID is invalid or expired');
      } else if (errorMessage.includes('CORS')) {
        addLog('This may indicate a CORS issue - check browser console for details');
      } else if (errorMessage.includes('Failed to fetch')) {
        addLog('This may indicate network connectivity issues or that the API server is down');
      }
    }
  };

  // Alternative method to try fetching columns directly
  const tryDirectFetch = async () => {
    addLog('Trying direct fetch to API endpoint...');
    try {
      // Try to fetch column data directly
      const url = `http://localhost:8000/api/files/${sessionId}/columns`;
      addLog(`Fetching from: ${url}`);
      
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Accept': 'application/json'
        }
      });
      
      addLog(`Fetch status: ${response.status}`);
      addLog(`Response headers: ${JSON.stringify(Object.fromEntries(response.headers.entries()))}`);
      
      if (!response.ok) {
        addLog(`Error response: ${response.status} ${response.statusText}`);
        return;
      }

      // Get response text first to check format
      const text = await response.text();
      addLog(`Raw response text: ${text.length > 500 ? text.substring(0, 500) + '...' : text}`);
      
      try {
        const data = JSON.parse(text);
        addLog(`Parsed JSON data: ${JSON.stringify(data)}`);
        
        // Test for proper structure
        if (data && data.columns) {
          addLog(`✅ Success: Found ${data.columns.length} columns`)
        } else {
          addLog(`⚠️ Warning: Response does not contain expected 'columns' field`)
        }
      } catch (parseError) {
        addLog(`❌ Failed to parse response as JSON: ${parseError instanceof Error ? parseError.message : 'Unknown error'}`)
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      addLog(`❌ Direct fetch error: ${errorMessage}`);
    }
  };

  return (
    <Paper p="xl" radius="md">
      <Title order={2} mb="lg">Biomapper Diagnostic Tool</Title>
      
      {step === 'input' && (
        <Card withBorder mb="xl">
          <Text mb="md">Enter a session ID from a previous file upload to test column selection:</Text>
          <Group>
            <input 
              value={sessionId}
              onChange={(e) => setSessionId(e.target.value)}
              style={{ flex: 1, padding: '10px' }}
              placeholder="e.g., e36b6a49-9157-4ca3-9cf1-de5390c7ea1c"
            />
            <Button 
              onClick={testColumnSelection}
              disabled={!sessionId}
            >
              Test Column Selection
            </Button>
          </Group>
        </Card>
      )}
      
      {step === 'test' && (
        <>
          <Card withBorder mb="md">
            <Title order={3}>Test Results</Title>
            {columnError ? (
              <Text color="red" mt="md">Error: {columnError}</Text>
            ) : columns ? (
              <>
                <Text color="green" mt="md">Successfully retrieved {columns.length} columns</Text>
                <Text mt="sm">Columns: {columns.join(', ')}</Text>
              </>
            ) : (
              <Text mt="md">Testing in progress...</Text>
            )}
            <Button 
              onClick={tryDirectFetch}
              mt="md"
              variant="outline"
            >
              Try Direct Fetch
            </Button>
          </Card>
          
          <Card withBorder>
            <Title order={3} mb="md">Logs</Title>
            <Stack 
              style={{ 
                backgroundColor: '#f5f5f5', 
                padding: '10px', 
                borderRadius: '5px',
                maxHeight: '300px',
                overflowY: 'auto'
              }}
            >
              {logs.map((log, i) => (
                <Code key={i} block>{log}</Code>
              ))}
            </Stack>
          </Card>
          
          <Button 
            mt="xl"
            onClick={() => {
              setStep('input');
              setLogs([]);
              setColumns(null);
              setColumnError(null);
            }}
            variant="subtle"
          >
            Reset
          </Button>
        </>
      )}
    </Paper>
  );
}
