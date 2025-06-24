import { useState } from 'react';
import { 
  Button, 
  Card, 
  Group, 
  Paper, 
  Text, 
  Title,
  Stack,
  Alert
} from '@mantine/core';
import { IconAlertCircle } from '@tabler/icons-react';
import { useAppStore } from '../../store/appStore';

export default function ColumnSelection() {
  const { sessionId, setActiveStep } = useAppStore();
  const [selectedColumn, setSelectedColumn] = useState<string>('compound_name');

  if (!sessionId) {
    return (
      <Paper p="xl" radius="md">
        <Alert 
          icon={<IconAlertCircle size={16} />} 
          title="No Session Found" 
          color="orange"
        >
          Please upload a file first.
        </Alert>
      </Paper>
    );
  }

  const handleContinue = () => {
    setActiveStep('mapping');
  };

  return (
    <Paper p="xl" radius="md">
      <Title order={2} mb="md">Select Column for Mapping</Title>
      <Text mb="lg" c="dimmed">
        Choose the column that contains the identifiers you want to map.
      </Text>

      <Card withBorder p="md" radius="md" mb="xl">
        <Stack>
          <Text fw={500}>Available Columns:</Text>
          <Group>
            <Button 
              variant={selectedColumn === 'compound_name' ? 'filled' : 'outline'}
              onClick={() => setSelectedColumn('compound_name')}
            >
              compound_name
            </Button>
            <Button 
              variant={selectedColumn === 'identifier' ? 'filled' : 'outline'}
              onClick={() => setSelectedColumn('identifier')}
            >
              identifier
            </Button>
            <Button 
              variant={selectedColumn === 'metabolite_id' ? 'filled' : 'outline'}
              onClick={() => setSelectedColumn('metabolite_id')}
            >
              metabolite_id
            </Button>
          </Group>
          
          {selectedColumn && (
            <Text size="sm" c="dimmed">
              Selected: <strong>{selectedColumn}</strong>
            </Text>
          )}
        </Stack>
      </Card>

      <Group justify="center">
        <Button size="lg" onClick={handleContinue} disabled={!selectedColumn}>
          Continue to Mapping Configuration
        </Button>
      </Group>
    </Paper>
  );
}