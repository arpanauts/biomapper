import React, { useState } from 'react';
import { 
  Alert,
  Badge,
  Button, 
  Card, 
  Group, 
  Loader, 
  Paper, 
  Progress,
  Stack,
  Table, 
  Text, 
  Title 
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { useQuery } from '@tanstack/react-query';
import { IconAlertCircle, IconArrowBack, IconCheck, IconDownload } from '@tabler/icons-react';
import { mappingApi } from '../../services/api';

interface ResultsProps {
  jobId: string;
  onReset: () => void;
}

// Job status types
type JobStatus = 'pending' | 'processing' | 'completed' | 'failed';

// Result data type
interface ResultData {
  headers: string[];
  data: string[][];
  statistics: {
    total_rows: number;
    mapped_count: number;
    unmapped_count: number;
    mapping_rate: number;
  };
}

type JobStatusResponse = {
  status: JobStatus;
  progress?: number;
}

export default function Results({ jobId, onReset }: ResultsProps) {
  const [status, setStatus] = useState<JobStatus>('pending');
  const [progress, setProgress] = useState(0);
  const [pollInterval, setPollInterval] = useState(1000); // Start with 1 second

  // Query for job status
  const statusQuery = useQuery({
    queryKey: ['job-status', jobId],
    queryFn: () => mappingApi.getJobStatus(jobId) as Promise<JobStatusResponse>,
    refetchInterval: pollInterval
  });
  
  // Handle status query response
  React.useEffect(() => {
    if (statusQuery.data) {
      setStatus(statusQuery.data.status);
      setProgress(statusQuery.data.progress || 0);
      
      // If job is complete or failed, stop polling
      if (statusQuery.data.status === 'completed' || statusQuery.data.status === 'failed') {
        setPollInterval(0);
      } else {
        // Gradually slow down polling if it's taking a while
        if (pollInterval < 5000) {
          setPollInterval(Math.min(pollInterval * 1.2, 5000));
        }
      }
    }
  }, [statusQuery.data, pollInterval]);
  
  // Handle status query error
  React.useEffect(() => {
    if (statusQuery.error) {
      notifications.show({
        title: 'Error',
        message: 'Failed to fetch job status',
        color: 'red',
      });
      setPollInterval(0);
    }
  }, [statusQuery.error]);

  // Query for results (only when job is completed)
  const resultsQuery = useQuery<ResultData>({
    queryKey: ['job-results', jobId],
    queryFn: () => mappingApi.getResults(jobId) as Promise<ResultData>,
    enabled: status === 'completed',
    staleTime: Infinity // Don't refresh this data
  });
  
  // Handle results query error
  React.useEffect(() => {
    if (resultsQuery.error) {
      notifications.show({
        title: 'Error',
        message: 'Failed to fetch mapping results',
        color: 'red',
      });
    }
  }, [resultsQuery.error]);

  // Handle download results button click
  const handleDownload = () => {
    window.open(mappingApi.getDownloadUrl(jobId), '_blank');
  };

  // Determine the progress color
  const getProgressColor = () => {
    if (status === 'failed') return 'red';
    if (progress < 30) return 'yellow';
    if (progress < 70) return 'blue';
    return 'green';
  };

  // Render status badge
  const renderStatusBadge = () => {
    switch (status) {
      case 'pending':
        return <Badge color="yellow">Pending</Badge>;
      case 'processing': 
        return <Badge color="blue">Processing</Badge>;
      case 'completed':
        return <Badge color="green">Completed</Badge>;
      case 'failed':
        return <Badge color="red">Failed</Badge>;
      default:
        return null;
    }
  };

  return (
    <Paper p="xl" radius="md">
      <Title order={2} mb="md">Mapping Results</Title>
      <Text mb="lg" c="dimmed">
        View and download your mapping results.
      </Text>

      <Card withBorder p="md" radius="md" mb="xl">
        <Group mb="md">
          <Title order={4}>Job Status:</Title>
          {renderStatusBadge()}
        </Group>
        
        <Progress 
          value={progress} 
          color={getProgressColor()} 
          size="xl" 
          mb="md" 
          striped={status === 'processing'}
          animated={status === 'processing'}
        />
        
        <Group mb="md">
          <Text>{Math.round(progress)}% complete</Text>
          {statusQuery.isFetching && <Loader size="xs" />}
        </Group>

        {status === 'failed' && (
          <Alert 
            icon={<IconAlertCircle size="1rem" />} 
            title="Mapping Failed" 
            color="red" 
            mb="md"
          >
            There was an error processing your mapping job. Please try again.
          </Alert>
        )}

        {status === 'completed' && resultsQuery.isSuccess && (
          <Stack>
            <Alert 
              icon={<IconCheck size="1rem" />} 
              title="Mapping Completed" 
              color="green" 
              mb="md"
            >
              Your mapping job has been successfully completed. You can now download the results.
            </Alert>
            
            <Group mb="md">
              <Button 
                leftSection={<IconDownload size="1rem" />}
                onClick={handleDownload}
              >
                Download Results
              </Button>
            </Group>
            
            {resultsQuery.data && resultsQuery.data as ResultData && (
              <>
                <Title order={5}>Mapping Statistics</Title>
                <Group mb="md">
                  <Card withBorder p="xs" radius="md">
                    <Text size="sm" fw={500}>Total Rows</Text>
                    <Text size="xl">{resultsQuery.data.statistics?.total_rows || 0}</Text>
                  </Card>
                  <Card withBorder p="xs" radius="md">
                    <Text size="sm" fw={500}>Mapped</Text>
                    <Text size="xl" c="green">{resultsQuery.data.statistics?.mapped_count || 0}</Text>
                  </Card>
                  <Card withBorder p="xs" radius="md">
                    <Text size="sm" fw={500}>Unmapped</Text>
                    <Text size="xl" c="red">{resultsQuery.data.statistics?.unmapped_count || 0}</Text>
                  </Card>
                  <Card withBorder p="xs" radius="md">
                    <Text size="sm" fw={500}>Success Rate</Text>
                    <Text size="xl">{(resultsQuery.data.statistics?.mapping_rate || 0) * 100}%</Text>
                  </Card>
                </Group>

                <Title order={5} mb="xs">Results Preview</Title>
                <div style={{ overflowX: 'auto' }}>
                  <Table striped highlightOnHover withTableBorder>
                    <Table.Thead>
                      <Table.Tr>
                        {resultsQuery.data.headers?.map((header: string, index: number) => (
                          <Table.Th key={index}>{header}</Table.Th>
                        ))}
                      </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                      {resultsQuery.data.data?.slice(0, 5).map((row, rowIndex) => (
                        <Table.Tr key={rowIndex}>
                          {row.map((cell: string, cellIndex: number) => (
                            <Table.Td key={cellIndex}>{cell}</Table.Td>
                          ))}
                        </Table.Tr>
                      ))}
                    </Table.Tbody>
                  </Table>
                </div>
                <Text size="xs" c="dimmed" mt="xs">Showing first 5 rows only</Text>
              </>
            )}
          </Stack>
        )}
      </Card>

      <Group justify="center">
        <Button 
          leftSection={<IconArrowBack size="1rem" />}
          variant="outline"
          onClick={onReset}
        >
          Start New Mapping
        </Button>
      </Group>
    </Paper>
  );
}
