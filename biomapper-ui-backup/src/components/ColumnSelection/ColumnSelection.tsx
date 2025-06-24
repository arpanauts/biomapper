import { useState, useEffect } from 'react';
import { 
  Button, 
  Card, 
  Group, 
  Loader, 
  Paper, 
  Select, 
  Text, 
  TextInput,
  Title,
  ScrollArea
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { useQuery } from '@tanstack/react-query';
import { fileApi } from '../../services/api';

interface ColumnSelectionProps {
  sessionId: string;
  onColumnsSelected: () => void;
}

interface ColumnsResponse {
  columns: string[];
}

interface CSVPreviewResponse {
  columns: string[];
  rows: string[][];
  total_rows: number;
  preview_rows: number;
}

// This interface will be needed if we restore preview functionality
/* interface PreviewData {
  headers: string[];
  data: string[][];
} */

export default function ColumnSelection({ sessionId, onColumnsSelected }: ColumnSelectionProps) {
  console.log('ColumnSelection component mounted with sessionId:', sessionId);
  
  // 1. All useState hooks first
  const [selectedColumn, setSelectedColumn] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  
  // 2. All useQuery hooks next
  // Query to get columns from the uploaded file
  const columnsQuery = useQuery<ColumnsResponse>({
    queryKey: ['columns', sessionId],
    queryFn: async () => {
      console.log('ColumnSelection: Starting queryFn execution');
      console.log('ColumnSelection: Fetching columns for session', sessionId);
      
      // Verify session ID exists
      if (!sessionId) {
        console.error('ColumnSelection: No sessionId provided to columnsQuery');
        // Try to recover from sessionStorage
        const storedSessionId = sessionStorage.getItem('biomapper_current_session');
        if (storedSessionId) {
          console.log('ColumnSelection: Recovered sessionId from storage:', storedSessionId);
          // Continue with the recovered session ID
          const result = await fileApi.getColumns(storedSessionId);
          console.log('ColumnSelection: Received columns result using recovered sessionId:', result);
          return result;
        } else {
          throw new Error('No session ID available');
        }
      }
      
      try {
        console.log('ColumnSelection: About to call fileApi.getColumns with sessionId:', sessionId);
        const result = await fileApi.getColumns(sessionId);
        console.log('ColumnSelection: Received columns result:', result);
        return result;
      } catch (error) {
        console.error('ColumnSelection: Error fetching columns:', error);
        console.error('ColumnSelection: Error details:', error instanceof Error ? error.message : 'Unknown error');
        
        // Try to recover if the error looks like a session expiration
        const errorMessage = error instanceof Error ? error.message : String(error);
        if (errorMessage.includes('not found') || errorMessage.includes('404')) {
          console.warn('ColumnSelection: Session appears to be expired or invalid');
          notifications.show({
            title: 'Session Error',
            message: 'Your session has expired. Please try uploading your file again.',
            color: 'red',
          });
        } else {
          notifications.show({
            title: 'Error',
            message: `Failed to load columns: ${errorMessage}`,
            color: 'red',
          });
        }
        throw error;
      }
    },
    staleTime: 0, // Always consider data stale to force refetch when needed
    enabled: true, // Always enable the query, we'll handle missing sessionId in the queryFn
    retry: 3, // Retry failed requests 3 times
    retryDelay: 1000, // Wait 1 second between retries
    refetchOnMount: 'always' // Always refetch when component mounts
  });

  // Query to get a preview of the data
  const previewQuery = useQuery<CSVPreviewResponse>({
    queryKey: ['preview', sessionId],
    queryFn: async () => {
      console.log('ColumnSelection: Fetching preview for session', sessionId);
      try {
        return await fileApi.getPreview(sessionId);
      } catch (error) {
        console.error('ColumnSelection: Error fetching preview:', error);
        notifications.show({
          title: 'Warning',
          message: `Failed to load data preview: ${error instanceof Error ? error.message : 'Unknown error'}`,
          color: 'yellow',
        });
        throw error;
      }
    },
    staleTime: Infinity, // Don't refresh this data
    retry: 3,
    enabled: columnsQuery.isSuccess // Only fetch preview after columns are loaded
  });
  
  // Compute derived values before useEffect hooks
  const columns = columnsQuery.data && columnsQuery.data.columns ? columnsQuery.data.columns : [];
  // Keep the preview data for future use (currently not displayed)
  // This variable is commented out to avoid linting errors but can be reactivated when needed
  /*const preview: PreviewData = {
    headers: previewQuery.data ? previewQuery.data.columns : [],
    data: previewQuery.data ? previewQuery.data.rows : []
  };*/
  
  // Filter columns based on search term for large datasets
  const filteredColumns = columns
    .filter(col => col.toLowerCase().includes(searchTerm.toLowerCase()))
    .slice(0, 200); // Limit to 200 visible items for performance

  // 3. All useEffect hooks
  // Basic debug log for sessionId
  useEffect(() => {
    console.log('ColumnSelection: sessionId changed or component mounted, sessionId =', sessionId);
  }, [sessionId]);
  
  // Select first column when data loads
  useEffect(() => {
    if (columnsQuery.data && columnsQuery.data.columns && columnsQuery.data.columns.length > 0 && !selectedColumn) {
      setSelectedColumn(columnsQuery.data.columns[0]);
      console.log('ColumnSelection: Auto-selected first column:', columnsQuery.data.columns[0]);
    }
  }, [columnsQuery.data, selectedColumn]);
  
  // Debug and refetch effect
  useEffect(() => {
    // Debug logging
    if (columns.length > 0) {
      console.log(`ColumnSelection: Successfully loaded ${columns.length} columns`);
    }
    
    // Data refetching when sessionId changes
    if (sessionId) {
      console.log('ColumnSelection: sessionId detected, ensuring data is fetched');
      console.log('ColumnSelection: Current sessionId value is:', sessionId);
      try {
        // Using a try-catch to handle any potential errors with the refetch promises
        columnsQuery.refetch()
          .then(result => console.log('ColumnSelection: columnsQuery refetch result:', result))
          .catch(err => console.error('ColumnSelection: columnsQuery refetch error:', err));
          
        previewQuery.refetch()
          .then(result => console.log('ColumnSelection: previewQuery refetch result:', result))
          .catch(err => console.error('ColumnSelection: previewQuery refetch error:', err));
      } catch (error) {
        console.error('ColumnSelection: Error triggering refetch:', error);
      }
    } else if (sessionId === null || sessionId === undefined) {
      console.warn('ColumnSelection: sessionId is falsy, skipping refetch:', sessionId);
    }
  }, [columns, sessionId, columnsQuery.refetch, previewQuery.refetch]);

  // 4. Event handlers after all hooks
  const handleContinue = () => {
    if (selectedColumn) {
      // Store the selected column in session storage for the next step
      sessionStorage.setItem(`biomapper_${sessionId}_idColumn`, selectedColumn);
      onColumnsSelected();
    } else {
      notifications.show({
        title: 'Warning',
        message: 'Please select an ID column to continue',
        color: 'yellow',
      });
    }
  };

  // 5. Conditional rendering based on query states
  if (columnsQuery.isPending || previewQuery.isPending) {
    return (
      <Paper p="xl" radius="md" style={{ textAlign: 'center' }}>
        <Loader size="lg" />
        <Text mt="md">Loading file data for session {sessionId}...</Text>
        <Text size="xs" mt="sm" c="dimmed">This may take a moment if retrieving a large file</Text>
      </Paper>
    );
  }

  if (columnsQuery.isError || previewQuery.isError) {
    const error = columnsQuery.error || previewQuery.error;
    const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
    const is404 = errorMessage.includes('404') || errorMessage.toLowerCase().includes('not found');
    
    return (
      <Paper p="xl" radius="md">
        <Title order={2} mb="md" c="red">Error Loading Data</Title>
        <Text mb="md">{errorMessage}</Text>
        
        {is404 && (
          <>
            <Text mb="md" fw="bold">This usually happens when:</Text>
            <Text component="ul">
              <Text component="li">The session has expired or is invalid</Text>
              <Text component="li">The file upload was incomplete or corrupted</Text>
              <Text component="li">The API server restarted after your upload</Text>
            </Text>
            <Text mt="md" mb="lg" c="dimmed">
              Session ID: {sessionId}
            </Text>
          </>
        )}
        
        <Group>
          <Button color="blue" onClick={() => {
            columnsQuery.refetch();
            previewQuery.refetch();
          }}>
            Try Again
          </Button>
          <Button variant="light" component="a" href="/">
            Return to Upload Page
          </Button>
        </Group>
      </Paper>
    );
  }
  // Keep minimal debugging in console but not UI
  console.log('ColumnSelection state:', {
    sessionId,
    columnsCount: columns.length,
    filteredCount: filteredColumns.length,
    selectedColumn,
    searchActive: searchTerm.length > 0
  });
  

  return (
    <Paper p="xl" radius="md">
      <Title order={2} mb="md">Select ID Column</Title>
      <Text mb="lg" c="dimmed">
        Choose the column containing biological identifiers that you want to map.
      </Text>

      <Select
        label="ID Column"
        description="Select the column that contains the identifiers you want to map"
        placeholder="Select a column"
        data={columns.map((col: string) => ({ value: col, label: col }))}
        value={selectedColumn}
        onChange={(value) => {
          console.log('ColumnSelection: Column selected:', value);
          setSelectedColumn(value);
        }}
        searchable
        mb="xl"
        required
      />
      
      <TextInput
        label="Search Columns"
        placeholder="Type to filter columns..."
        value={searchTerm}
        onChange={(event) => setSearchTerm(event.currentTarget.value)}
        mb="md"
      />

      <Card withBorder p="md" radius="md" mb="xl">
        <Group justify="space-between" mb="md">
          <Title order={4}>Column Summary</Title>
          <Text size="sm">
            {filteredColumns.length} of {columns.length} columns
            {searchTerm && ` (filtered by "${searchTerm}")`}
          </Text>
        </Group>
        
        <ScrollArea h={200} offsetScrollbars scrollbarSize={6}>
          <div style={{display: 'flex', flexWrap: 'wrap', gap: '8px'}}>
            {filteredColumns.map((col, index) => (
              <Paper 
                key={index} 
                p="xs" 
                withBorder 
                style={{
                  backgroundColor: col === selectedColumn ? 'var(--mantine-color-blue-1)' : undefined,
                  fontWeight: col === selectedColumn ? 'bold' : undefined,
                  cursor: 'pointer'
                }}
                onClick={() => setSelectedColumn(col)}
              >
                {col}
              </Paper>
            ))}
          </div>
        </ScrollArea>
        <Text size="xs" c="dimmed" mt="lg">Click a column name to select it as your ID column</Text>
      </Card>

      <Group justify="center">
        <Button 
          size="lg" 
          onClick={handleContinue}
          disabled={!selectedColumn}
        >
          Continue to Mapping
        </Button>
      </Group>
    </Paper>
  );
}
