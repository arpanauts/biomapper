import React, { useEffect, useState } from 'react';
import {
  Alert,
  Badge,
  Button,
  Card,
  Group,
  Loader,
  Paper,
  Stack,
  Table,
  Text,
  Title,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import {
  IconAlertCircle,
  IconArrowBack,
  IconCheck,
  IconDownload,
} from '@tabler/icons-react';

// Import the API service (will be implemented in prompt 02)
// For now, we'll define the interface
interface ApiService {
  getMappingStatus(jobId: string): Promise<MappingStatusResponse>;
  getMappingResults(jobId: string): Promise<MappingResult>;
  downloadResults(jobId: string): void;
}

// Import the app store (will be implemented in prompt 03)
// For now, we'll define the interface
interface AppStore {
  jobId: string | null;
  reset(): void;
}

// Types
type JobStatus = 'pending' | 'running' | 'completed' | 'failed';

interface MappingStatusResponse {
  status: JobStatus;
  progress?: number;
  message?: string;
  error?: string;
}

interface MappingResult {
  headers: string[];
  rows: Array<Record<string, any>>;
  statistics: {
    total_rows: number;
    mapped_count: number;
    unmapped_count: number;
    mapping_rate: number;
  };
}

interface ResultsProps {
  // These will be injected when integrating with the actual services
  apiService?: ApiService;
  appStore?: AppStore;
}

export default function Results({ apiService, appStore }: ResultsProps) {
  const [status, setStatus] = useState<JobStatus>('pending');
  const [progress, setProgress] = useState(0);
  const [results, setResults] = useState<MappingResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isPolling, setIsPolling] = useState(true);

  // Mock jobId for testing - will come from appStore
  const jobId = appStore?.jobId || 'test-job-id';

  // Polling logic
  useEffect(() => {
    if (!jobId || !isPolling || !apiService) return;

    const pollInterval = setInterval(async () => {
      try {
        const statusResponse = await apiService.getMappingStatus(jobId);
        setStatus(statusResponse.status);
        setProgress(statusResponse.progress || 0);

        if (statusResponse.status === 'completed') {
          setIsPolling(false);
          // Fetch the results
          const resultsData = await apiService.getMappingResults(jobId);
          setResults(resultsData);
          notifications.show({
            title: 'Success',
            message: 'Mapping completed successfully!',
            color: 'green',
            icon: <IconCheck size="1rem" />,
          });
        } else if (statusResponse.status === 'failed') {
          setIsPolling(false);
          setError(statusResponse.error || 'Mapping failed');
          notifications.show({
            title: 'Error',
            message: statusResponse.error || 'Mapping failed',
            color: 'red',
            icon: <IconAlertCircle size="1rem" />,
          });
        }
      } catch (err) {
        console.error('Error polling status:', err);
        setIsPolling(false);
        setError('Failed to fetch job status');
        notifications.show({
          title: 'Error',
          message: 'Failed to fetch job status',
          color: 'red',
        });
      }
    }, 2000); // Poll every 2 seconds

    return () => clearInterval(pollInterval);
  }, [jobId, isPolling, apiService]);

  // Handle download
  const handleDownload = () => {
    if (apiService && jobId) {
      apiService.downloadResults(jobId);
    }
  };

  // Handle reset
  const handleReset = () => {
    if (appStore) {
      appStore.reset();
    }
  };

  // Render status badge
  const renderStatusBadge = () => {
    const statusConfig = {
      pending: { color: 'gray', label: 'Pending' },
      running: { color: 'blue', label: 'In Progress' },
      completed: { color: 'green', label: 'Completed' },
      failed: { color: 'red', label: 'Failed' },
    };

    const config = statusConfig[status];
    return <Badge color={config.color}>{config.label}</Badge>;
  };

  // Convert results to table format
  const getTableData = () => {
    if (!results || !results.rows || results.rows.length === 0) return [];
    
    // Take first 10 rows for preview
    return results.rows.slice(0, 10).map((row) => 
      results.headers.map(header => row[header] || '')
    );
  };

  return (
    <Paper p="xl" radius="md">
      <Title order={2} mb="md">
        Mapping Results
      </Title>

      <Card withBorder p="md" radius="md" mb="xl">
        <Group justify="space-between" mb="md">
          <Group>
            <Text fw={500}>Job Status:</Text>
            {renderStatusBadge()}
          </Group>
          {isPolling && <Loader size="sm" />}
        </Group>

        {/* Progress indicator for running jobs */}
        {status === 'running' && (
          <Stack gap="xs" mb="md">
            <Text size="sm" c="dimmed">
              Progress: {progress}%
            </Text>
            <div
              style={{
                width: '100%',
                height: '8px',
                backgroundColor: '#e9ecef',
                borderRadius: '4px',
                overflow: 'hidden',
              }}
            >
              <div
                style={{
                  width: `${progress}%`,
                  height: '100%',
                  backgroundColor: '#228be6',
                  transition: 'width 0.3s ease',
                }}
              />
            </div>
          </Stack>
        )}

        {/* Error state */}
        {status === 'failed' && error && (
          <Alert
            icon={<IconAlertCircle size="1rem" />}
            title="Mapping Failed"
            color="red"
            mb="md"
          >
            {error}
          </Alert>
        )}

        {/* Success state with results */}
        {status === 'completed' && results && (
          <Stack>
            <Alert
              icon={<IconCheck size="1rem" />}
              title="Mapping Completed"
              color="green"
              mb="md"
            >
              Your mapping job has been successfully completed.
            </Alert>

            {/* Statistics */}
            <Title order={4} mb="sm">
              Mapping Statistics
            </Title>
            <Group mb="xl">
              <Card withBorder p="xs" radius="md">
                <Text size="sm" fw={500} c="dimmed">
                  Total Rows
                </Text>
                <Text size="xl">{results.statistics.total_rows}</Text>
              </Card>
              <Card withBorder p="xs" radius="md">
                <Text size="sm" fw={500} c="dimmed">
                  Mapped
                </Text>
                <Text size="xl" c="green">
                  {results.statistics.mapped_count}
                </Text>
              </Card>
              <Card withBorder p="xs" radius="md">
                <Text size="sm" fw={500} c="dimmed">
                  Unmapped
                </Text>
                <Text size="xl" c="red">
                  {results.statistics.unmapped_count}
                </Text>
              </Card>
              <Card withBorder p="xs" radius="md">
                <Text size="sm" fw={500} c="dimmed">
                  Success Rate
                </Text>
                <Text size="xl">
                  {(results.statistics.mapping_rate * 100).toFixed(1)}%
                </Text>
              </Card>
            </Group>

            {/* Results preview table */}
            <Title order={4} mb="sm">
              Results Preview
            </Title>
            <div style={{ overflowX: 'auto' }}>
              <Table striped highlightOnHover withTableBorder>
                <Table.Thead>
                  <Table.Tr>
                    {results.headers.map((header, index) => (
                      <Table.Th key={index}>{header}</Table.Th>
                    ))}
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {getTableData().map((row, rowIndex) => (
                    <Table.Tr key={rowIndex}>
                      {row.map((cell, cellIndex) => (
                        <Table.Td key={cellIndex}>{cell}</Table.Td>
                      ))}
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </div>
            <Text size="xs" c="dimmed" mt="xs">
              Showing first 10 rows
            </Text>

            {/* Download button */}
            <Group mt="xl">
              <Button
                leftSection={<IconDownload size="1rem" />}
                onClick={handleDownload}
              >
                Download Results
              </Button>
            </Group>
          </Stack>
        )}
      </Card>

      {/* Reset button */}
      <Group justify="center">
        <Button
          leftSection={<IconArrowBack size="1rem" />}
          variant="outline"
          onClick={handleReset}
        >
          Start New Mapping
        </Button>
      </Group>
    </Paper>
  );
}