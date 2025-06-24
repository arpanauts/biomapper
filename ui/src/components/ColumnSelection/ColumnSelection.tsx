import { useState, useEffect } from 'react';
import { Button, Card, Group, Paper, Select, Text, Title, Table, LoadingOverlay } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { fileApi } from '../../services/api';
import { useAppStore } from '../../store/appStore';

export default function ColumnSelection() {
  const [columns, setColumns] = useState<string[]>([]);
  const [selectedColumn, setSelectedColumn] = useState<string | null>(null);
  const [preview, setPreview] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const { sessionId, setActiveStep } = useAppStore();

  useEffect(() => {
    if (sessionId) {
      loadColumnData();
    }
  }, [sessionId]);

  const loadColumnData = async () => {
    if (!sessionId) return;

    try {
      setIsLoading(true);
      
      // Fetch columns
      const columnsData = await fileApi.getColumns(sessionId);
      setColumns(columnsData.columns);
      
      // Fetch preview
      const previewData = await fileApi.getPreview(sessionId);
      setPreview(previewData.data);
      
    } catch (error) {
      console.error('Error loading column data:', error);
      notifications.show({
        title: 'Error',
        message: 'Failed to load column information',
        color: 'red',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleContinue = () => {
    if (!selectedColumn) {
      notifications.show({
        title: 'Warning',
        message: 'Please select an ID column',
        color: 'yellow',
      });
      return;
    }

    setActiveStep('mapping');
  };

  return (
    <Paper p="xl" radius="md" pos="relative">
      <LoadingOverlay visible={isLoading} />
      
      <Title order={2} mb="md">Select ID Column</Title>
      <Text mb="lg" c="dimmed">
        Choose the column containing the biological identifiers you want to map.
      </Text>

      <Card withBorder radius="md" mb="xl">
        <Select
          label="ID Column"
          placeholder="Select the column with identifiers"
          data={columns}
          value={selectedColumn}
          onChange={setSelectedColumn}
          size="md"
          mb="xl"
        />

        {preview.length > 0 && (
          <>
            <Text fw={500} mb="sm">Data Preview</Text>
            <Table striped highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  {columns.slice(0, 5).map((col) => (
                    <Table.Th key={col}>{col}</Table.Th>
                  ))}
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {preview.slice(0, 5).map((row, idx) => (
                  <Table.Tr key={idx}>
                    {columns.slice(0, 5).map((col) => (
                      <Table.Td key={col}>{row[col]}</Table.Td>
                    ))}
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
            {preview.length > 5 && (
              <Text size="sm" c="dimmed" mt="sm">
                Showing first 5 rows of {preview.length}
              </Text>
            )}
          </>
        )}
      </Card>

      <Group justify="center">
        <Button 
          size="lg"
          onClick={handleContinue}
          disabled={!selectedColumn}
        >
          Continue to Mapping Configuration
        </Button>
      </Group>
    </Paper>
  );
}