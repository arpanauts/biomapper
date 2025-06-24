import { useState, useEffect } from 'react';
import { Button, Card, Group, Paper, Progress, Text, Title, Table, Badge, LoadingOverlay } from '@mantine/core';
import { IconCheck, IconX, IconDownload, IconRefresh } from '@tabler/icons-react';
import { notifications } from '@mantine/notifications';
import { mappingApi } from '../../services/api';
import { useAppStore } from '../../store/appStore';

export default function Results() {
  const [status, setStatus] = useState<string>('pending');
  const [progress, setProgress] = useState(0);
  const [results, setResults] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const { jobId, reset } = useAppStore();

  useEffect(() => {
    if (jobId) {
      checkJobStatus();
      const interval = setInterval(checkJobStatus, 2000);
      return () => clearInterval(interval);
    }
  }, [jobId]);

  const checkJobStatus = async () => {
    if (!jobId) return;

    try {
      const statusData = await mappingApi.getJobStatus(jobId);
      setStatus(statusData.status);
      setProgress(statusData.progress || 0);

      if (statusData.status === 'completed') {
        const resultsData = await mappingApi.getResults(jobId);
        setResults(resultsData.mappings || []);
        setIsLoading(false);
      } else if (statusData.status === 'failed') {
        setIsLoading(false);
        notifications.show({
          title: 'Error',
          message: 'Mapping job failed',
          color: 'red',
        });
      }
    } catch (error) {
      console.error('Error checking job status:', error);
    }
  };

  const handleDownload = () => {
    if (!jobId) return;
    
    const downloadUrl = mappingApi.getDownloadUrl(jobId);
    window.open(downloadUrl, '_blank');
  };

  const handleNewMapping = () => {
    reset();
  };

  const getStatusColor = () => {
    switch (status) {
      case 'completed': return 'green';
      case 'failed': return 'red';
      case 'running': return 'blue';
      default: return 'gray';
    }
  };

  return (
    <Paper p="xl" radius="md" pos="relative">
      <LoadingOverlay visible={isLoading && status !== 'completed' && status !== 'failed'} />
      
      <Title order={2} mb="md">Mapping Results</Title>
      
      <Card withBorder radius="md" mb="xl">
        <Group justify="space-between" mb="md">
          <div>
            <Text fw={500}>Job Status</Text>
            <Badge color={getStatusColor()} size="lg" mt="xs">
              {status.toUpperCase()}
            </Badge>
          </div>
          {status === 'running' && (
            <div style={{ flex: 1, maxWidth: 300 }}>
              <Text size="sm" mb="xs">Progress</Text>
              <Progress value={progress} size="lg" animated />
              <Text size="xs" c="dimmed" mt="xs">{progress}% complete</Text>
            </div>
          )}
        </Group>

        {status === 'completed' && results.length > 0 && (
          <>
            <Text fw={500} mb="sm">Mapping Summary</Text>
            <Table striped highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Source ID</Table.Th>
                  <Table.Th>Target ID</Table.Th>
                  <Table.Th>Confidence</Table.Th>
                  <Table.Th>Status</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {results.slice(0, 10).map((result, idx) => (
                  <Table.Tr key={idx}>
                    <Table.Td>{result.source_id}</Table.Td>
                    <Table.Td>{result.target_id || 'Not found'}</Table.Td>
                    <Table.Td>{result.confidence ? `${(result.confidence * 100).toFixed(0)}%` : '-'}</Table.Td>
                    <Table.Td>
                      {result.target_id ? (
                        <IconCheck size={16} color="green" />
                      ) : (
                        <IconX size={16} color="red" />
                      )}
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
            {results.length > 10 && (
              <Text size="sm" c="dimmed" mt="sm">
                Showing first 10 results of {results.length}
              </Text>
            )}
          </>
        )}
      </Card>

      <Group justify="center">
        {status === 'completed' && (
          <>
            <Button 
              size="lg"
              leftSection={<IconDownload size={20} />}
              onClick={handleDownload}
            >
              Download Results
            </Button>
            <Button 
              size="lg"
              variant="outline"
              leftSection={<IconRefresh size={20} />}
              onClick={handleNewMapping}
            >
              Start New Mapping
            </Button>
          </>
        )}
        {status === 'failed' && (
          <Button 
            size="lg"
            onClick={handleNewMapping}
          >
            Try Again
          </Button>
        )}
      </Group>
    </Paper>
  );
}