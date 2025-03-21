import { useState } from 'react';
import { 
  Button, 
  Card,
  Checkbox,
  Grid, 
  Group, 
  Paper, 
  Radio, 
  Select,
  Stack,
  Text, 
  TextInput,
  Title 
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { useMutation } from '@tanstack/react-query';
import { mappingApi } from '../../services/api';

interface MappingConfigProps {
  sessionId: string;
  onMappingStarted: (jobId: string) => void;
}

// Available ontology targets
const ONTOLOGY_OPTIONS = [
  { value: 'chebi', label: 'ChEBI (Chemical Entities of Biological Interest)' },
  { value: 'pubchem', label: 'PubChem' },
  { value: 'inchikey', label: 'InChI Key' },
  { value: 'hmdb', label: 'Human Metabolome Database (HMDB)' },
  { value: 'unii', label: 'FDA Unique Ingredient Identifier (UNII)' },
  { value: 'spoke', label: 'SPOKE Knowledge Graph Combined' },
];

export default function MappingConfig({ sessionId, onMappingStarted }: MappingConfigProps) {
  // Get the ID column from session storage
  const idColumn = sessionStorage.getItem(`biomapper_${sessionId}_idColumn`) || '';
  
  // State for configuration options
  const [targetOntology, setTargetOntology] = useState<string>('spoke');
  const [useAI, setUseAI] = useState<boolean>(true);
  const [confidence, setConfidence] = useState<string>('medium');
  
  // Mapping job creation mutation
  const createJobMutation = useMutation({
    mutationFn: () => mappingApi.createMappingJob(
      sessionId,
      idColumn,
      targetOntology,
      {
        use_ai: useAI,
        confidence_level: confidence,
      }
    ),
    onSuccess: (data) => {
      notifications.show({
        title: 'Success',
        message: 'Mapping job created successfully',
        color: 'green',
      });
      
      onMappingStarted(data.job_id);
    },
    onError: (error) => {
      notifications.show({
        title: 'Error',
        message: `Failed to create mapping job: ${error instanceof Error ? error.message : 'Unknown error'}`,
        color: 'red',
      });
    },
  });

  // Handle start mapping button click
  const handleStartMapping = () => {
    if (!idColumn) {
      notifications.show({
        title: 'Warning',
        message: 'No ID column selected. Please go back and select a column.',
        color: 'yellow',
      });
      return;
    }

    createJobMutation.mutate();
  };

  if (!idColumn) {
    return (
      <Paper p="xl" radius="md">
        <Title order={2} mb="md" c="orange">ID Column Missing</Title>
        <Text>No ID column was selected. Please go back to the previous step.</Text>
      </Paper>
    );
  }

  return (
    <Paper p="xl" radius="md">
      <Title order={2} mb="md">Configure Mapping</Title>
      <Text mb="lg" c="dimmed">
        Configure how your identifiers will be mapped to ontology terms.
      </Text>

      <Card withBorder p="md" radius="md" mb="xl">
        <Grid>
          <Grid.Col span={{ base: 12, md: 6 }}>
            <Stack>
              <TextInput
                label="ID Column"
                value={idColumn}
                readOnly
                description="The column containing identifiers to map"
              />

              <Select
                label="Target Ontology"
                description="Select the ontology to map identifiers to"
                data={ONTOLOGY_OPTIONS}
                value={targetOntology}
                onChange={(val) => val && setTargetOntology(val)}
                required
                mb="md"
              />

              <Checkbox
                label="Use AI-powered mapping"
                description="Enable AI to improve mapping accuracy for ambiguous terms"
                checked={useAI}
                onChange={(e) => setUseAI(e.currentTarget.checked)}
                mb="md"
              />

              <Radio.Group
                name="confidence"
                label="Confidence Level"
                description="Set the confidence threshold for mapping"
                value={confidence}
                onChange={setConfidence}
                withAsterisk
              >
                <Group mt="xs">
                  <Radio value="high" label="High (fewer results, higher confidence)" />
                  <Radio value="medium" label="Medium (balanced)" />
                  <Radio value="low" label="Low (more results, lower confidence)" />
                </Group>
              </Radio.Group>
            </Stack>
          </Grid.Col>
          
          <Grid.Col span={{ base: 12, md: 6 }}>
            <Card withBorder p="sm" radius="md" mb="md">
              <Title order={5} mb="xs">Mapping Information</Title>
              <Text size="sm">
                <strong>ID Column:</strong> {idColumn}
              </Text>
              <Text size="sm">
                <strong>Target Ontology:</strong> {ONTOLOGY_OPTIONS.find(opt => opt.value === targetOntology)?.label || targetOntology}
              </Text>
              <Text size="sm">
                <strong>AI Assistance:</strong> {useAI ? 'Enabled' : 'Disabled'}
              </Text>
              <Text size="sm">
                <strong>Confidence:</strong> {confidence.charAt(0).toUpperCase() + confidence.slice(1)}
              </Text>
            </Card>
            
            <Card withBorder p="sm" radius="md">
              <Title order={5} mb="xs">About {ONTOLOGY_OPTIONS.find(opt => opt.value === targetOntology)?.label || 'Selected Ontology'}</Title>
              {targetOntology === 'chebi' && (
                <Text size="sm">
                  ChEBI (Chemical Entities of Biological Interest) is a freely available dictionary 
                  of molecular entities focused on small chemical compounds.
                </Text>
              )}
              {targetOntology === 'pubchem' && (
                <Text size="sm">
                  PubChem is an open chemistry database at the National Institutes of Health (NIH) 
                  containing information on chemical structures, identifiers, and biological activities.
                </Text>
              )}
              {targetOntology === 'inchikey' && (
                <Text size="sm">
                  InChI Key is a hashed version of the full International Chemical Identifier (InChI), 
                  designed to facilitate web searches and database indexing.
                </Text>
              )}
              {targetOntology === 'hmdb' && (
                <Text size="sm">
                  The Human Metabolome Database (HMDB) is a comprehensive resource containing detailed 
                  information about metabolites found in the human body.
                </Text>
              )}
              {targetOntology === 'unii' && (
                <Text size="sm">
                  FDA Unique Ingredient Identifier (UNII) is a non-proprietary, free, unique, 
                  unambiguous identifier for substances in drugs, biologics, foods, and devices.
                </Text>
              )}
              {targetOntology === 'spoke' && (
                <Text size="sm">
                  SPOKE (Scalable Precision Medicine Open Knowledge Engine) is a knowledge graph that 
                  integrates data across various biomedical domains, including genes, proteins, 
                  diseases, drugs, and more.
                </Text>
              )}
            </Card>
          </Grid.Col>
        </Grid>
      </Card>

      <Group justify="center">
        <Button 
          size="lg" 
          onClick={handleStartMapping}
          loading={createJobMutation.isPending}
          disabled={!idColumn || !targetOntology}
        >
          Start Mapping
        </Button>
      </Group>
    </Paper>
  );
}
