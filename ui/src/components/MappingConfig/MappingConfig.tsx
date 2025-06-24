import { useState } from 'react';
import { Button, Card, Group, Paper, Select, Text, Title, Stack, Switch } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { mappingApi } from '../../services/api';
import { useAppStore } from '../../store/appStore';

const TARGET_ONTOLOGIES = [
  { value: 'uniprot', label: 'UniProt' },
  { value: 'ensembl', label: 'Ensembl' },
  { value: 'hgnc', label: 'HGNC' },
  { value: 'chebi', label: 'ChEBI' },
  { value: 'pubchem', label: 'PubChem' },
];

export default function MappingConfig() {
  const [targetOntology, setTargetOntology] = useState<string | null>(null);
  const [selectedColumn] = useState<string>('id'); // Mock for now
  const [includeMetadata, setIncludeMetadata] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { sessionId, setJobId, setActiveStep } = useAppStore();

  const handleStartMapping = async () => {
    if (!targetOntology) {
      notifications.show({
        title: 'Warning',
        message: 'Please select a target ontology',
        color: 'yellow',
      });
      return;
    }

    if (!sessionId) {
      notifications.show({
        title: 'Error',
        message: 'No active session found',
        color: 'red',
      });
      return;
    }

    try {
      setIsSubmitting(true);

      const result = await mappingApi.createMappingJob(
        sessionId,
        selectedColumn,
        targetOntology,
        { include_metadata: includeMetadata }
      );

      if (!result || !result.job_id) {
        throw new Error('Invalid response from server');
      }

      notifications.show({
        title: 'Success',
        message: 'Mapping job started successfully',
        color: 'green',
      });

      setJobId(result.job_id);
      setActiveStep('results');
    } catch (error) {
      console.error('Error starting mapping:', error);
      notifications.show({
        title: 'Error',
        message: `Failed to start mapping: ${error instanceof Error ? error.message : 'Unknown error'}`,
        color: 'red',
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Paper p="xl" radius="md">
      <Title order={2} mb="md">Configure Mapping</Title>
      <Text mb="lg" c="dimmed">
        Configure how your identifiers should be mapped to standard ontologies.
      </Text>

      <Card withBorder radius="md" mb="xl">
        <Stack gap="lg">
          <Select
            label="Target Ontology"
            placeholder="Select target ontology"
            data={TARGET_ONTOLOGIES}
            value={targetOntology}
            onChange={setTargetOntology}
            size="md"
            description="The standardized ontology to map your identifiers to"
          />

          <Group>
            <Switch
              label="Include metadata"
              checked={includeMetadata}
              onChange={(event) => setIncludeMetadata(event.currentTarget.checked)}
              description="Include additional metadata in the mapping results"
            />
          </Group>

          <Card withBorder p="md" bg="gray.0">
            <Text size="sm" fw={500} mb="xs">Mapping Summary</Text>
            <Text size="sm">Source column: {selectedColumn}</Text>
            <Text size="sm">Target ontology: {targetOntology || 'Not selected'}</Text>
            <Text size="sm">Include metadata: {includeMetadata ? 'Yes' : 'No'}</Text>
          </Card>
        </Stack>
      </Card>

      <Group justify="center">
        <Button 
          size="lg"
          onClick={handleStartMapping}
          loading={isSubmitting}
          disabled={!targetOntology}
        >
          Start Mapping
        </Button>
      </Group>
    </Paper>
  );
}