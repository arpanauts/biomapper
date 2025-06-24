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
  ScrollArea,
  Checkbox,
  Stack,
  MultiSelect
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { useQuery } from '@tanstack/react-query';
import { apiService } from '../../services/api';
import { useAppStore } from '../../store/appStore';

export default function ColumnSelection() {
  const { sessionId, setActiveStep } = useAppStore();
  const [selectedColumns, setSelectedColumns] = useState<string[]>([]);
  const [searchTerm, setSearchTerm] = useState("");

  // Fetch columns from the API
  const columnsQuery = useQuery({
    queryKey: ['columns', sessionId],
    queryFn: async () => {
      if (!sessionId) {
        throw new Error('No session ID available');
      }
      return await apiService.getColumns(sessionId);
    },
    enabled: !!sessionId,
    retry: 3,
    retryDelay: 1000,
  });

  const columns = columnsQuery.data?.columns || [];
  
  // Filter columns based on search term
  const filteredColumns = columns
    .filter(col => col.toLowerCase().includes(searchTerm.toLowerCase()))
    .slice(0, 200); // Limit for performance

  // Handle submission
  const handleSubmit = () => {
    if (selectedColumns.length === 0) {
      notifications.show({
        title: 'Warning',
        message: 'Please select at least one column to continue',
        color: 'yellow',
      });
      return;
    }

    // Store selected columns for the next step
    if (sessionId) {
      sessionStorage.setItem(`biomapper_${sessionId}_selectedColumns`, JSON.stringify(selectedColumns));
    }
    
    // Navigate to mapping step
    setActiveStep('mapping');
  };

  // Loading state
  if (columnsQuery.isPending) {
    return (
      <Paper p="xl" radius="md" style={{ textAlign: 'center' }}>
        <Loader size="lg" />
        <Text mt="md">Loading columns...</Text>
      </Paper>
    );
  }

  // Error state
  if (columnsQuery.isError) {
    const error = columnsQuery.error;
    const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
    
    return (
      <Paper p="xl" radius="md">
        <Title order={2} mb="md" c="red">Error Loading Columns</Title>
        <Text mb="md">{errorMessage}</Text>
        <Group>
          <Button color="blue" onClick={() => columnsQuery.refetch()}>
            Try Again
          </Button>
        </Group>
      </Paper>
    );
  }

  return (
    <Paper p="xl" radius="md">
      <Title order={2} mb="md">Select Columns for Mapping</Title>
      <Text mb="lg" c="dimmed">
        Choose the columns containing identifiers that you want to map.
      </Text>

      <TextInput
        label="Search Columns"
        placeholder="Type to filter columns..."
        value={searchTerm}
        onChange={(event) => setSearchTerm(event.currentTarget.value)}
        mb="md"
      />

      <MultiSelect
        label="Select Columns"
        description="Choose one or more columns for mapping"
        placeholder="Select columns"
        data={columns}
        value={selectedColumns}
        onChange={setSelectedColumns}
        searchable
        clearable
        mb="xl"
      />

      <Card withBorder p="md" radius="md" mb="xl">
        <Group justify="space-between" mb="md">
          <Title order={4}>Available Columns</Title>
          <Text size="sm">
            {filteredColumns.length} of {columns.length} columns
            {searchTerm && ` (filtered by "${searchTerm}")`}
          </Text>
        </Group>
        
        <ScrollArea h={300} offsetScrollbars scrollbarSize={6}>
          <Stack gap="xs">
            {filteredColumns.map((col) => (
              <Checkbox
                key={col}
                label={col}
                checked={selectedColumns.includes(col)}
                onChange={(event) => {
                  if (event.currentTarget.checked) {
                    setSelectedColumns([...selectedColumns, col]);
                  } else {
                    setSelectedColumns(selectedColumns.filter(c => c !== col));
                  }
                }}
              />
            ))}
          </Stack>
        </ScrollArea>
      </Card>

      <Group justify="space-between">
        <Text size="sm" c="dimmed">
          {selectedColumns.length} column{selectedColumns.length !== 1 ? 's' : ''} selected
        </Text>
        <Button 
          size="lg" 
          onClick={handleSubmit}
          disabled={selectedColumns.length === 0}
        >
          Next
        </Button>
      </Group>
    </Paper>
  );
}