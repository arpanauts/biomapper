import { useState } from 'react';
import { 
  Button, 
  Card,
  Grid, 
  Group, 
  Paper, 
  Select,
  Stack,
  Text, 
  TextInput,
  Title,
  Alert
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconAlertCircle } from '@tabler/icons-react';

// Import the apiService (will be created in Prompt 02)
// For now, we'll create a mock interface
import { apiService } from '../../services/apiService';
// Import the appStore (will be created in Prompt 03)
import { useAppStore } from '../../store/appStore';

interface MappingConfigProps {
  // No props required as per task specification
}

// Strategy options for the mapping configuration
const STRATEGY_OPTIONS = [
  { value: 'direct_mapping', label: 'Direct Mapping' },
  { value: 'bidirectional_validation', label: 'Bidirectional Validation' },
  { value: 'iterative_mapping', label: 'Iterative Mapping' },
  { value: 'composite_mapping', label: 'Composite Mapping' },
];

// Target data source options
const DATA_SOURCE_OPTIONS = [
  { value: 'chebi', label: 'ChEBI' },
  { value: 'pubchem', label: 'PubChem' },
  { value: 'hmdb', label: 'HMDB' },
  { value: 'uniprot', label: 'UniProt' },
  { value: 'spoke', label: 'SPOKE Knowledge Graph' },
];

export default function MappingConfig({}: MappingConfigProps) {
  // Get session info from global store
  const { sessionId, selectedColumn, setJobId, setCurrentStep } = useAppStore();
  
  // Local state for form fields
  const [targetDataSource, setTargetDataSource] = useState<string>('');
  const [mappingStrategy, setMappingStrategy] = useState<string>('direct_mapping');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Validate that we have the required session data
  if (!sessionId || !selectedColumn) {
    return (
      <Paper p="xl" radius="md">
        <Alert 
          icon={<IconAlertCircle size={16} />} 
          title="Missing Session Data" 
          color="orange"
        >
          Session information is missing. Please complete the previous steps first.
        </Alert>
      </Paper>
    );
  }

  const handleSubmit = async () => {
    if (!targetDataSource) {
      notifications.show({
        title: 'Validation Error',
        message: 'Please select a target data source',
        color: 'red',
      });
      return;
    }

    setIsSubmitting(true);

    try {
      // Construct the configuration object
      const mappingConfig = {
        sessionId,
        sourceColumn: selectedColumn,
        targetDataSource,
        strategy: mappingStrategy,
        parameters: {
          // Additional parameters can be added here based on strategy
          confidence_threshold: 0.8,
          max_iterations: mappingStrategy === 'iterative_mapping' ? 3 : 1,
          enable_validation: mappingStrategy === 'bidirectional_validation',
        }
      };

      // Call the API service to start mapping
      const result = await apiService.startMapping(mappingConfig);

      // Update global state with the returned jobId
      setJobId(result.jobId);

      // Show success notification
      notifications.show({
        title: 'Success',
        message: 'Mapping process started successfully',
        color: 'green',
      });

      // Navigate to results step
      setCurrentStep('results');

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      notifications.show({
        title: 'Error',
        message: `Failed to start mapping: ${errorMessage}`,
        color: 'red',
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Paper p="xl" radius="md">
      <Title order={2} mb="md">Configure Mapping Strategy</Title>
      <Text mb="lg" c="dimmed">
        Configure how your data will be mapped to the target ontology.
      </Text>

      <Card withBorder p="md" radius="md" mb="xl">
        <Grid>
          <Grid.Col span={{ base: 12, md: 6 }}>
            <Stack>
              <TextInput
                label="Source Column"
                value={selectedColumn}
                readOnly
                description="The column containing identifiers to map"
              />

              <Select
                label="Target Data Source"
                description="Select the ontology or database to map to"
                placeholder="Choose a target"
                data={DATA_SOURCE_OPTIONS}
                value={targetDataSource}
                onChange={(val) => val && setTargetDataSource(val)}
                required
                withAsterisk
              />

              <Select
                label="Mapping Strategy"
                description="Select the mapping approach to use"
                data={STRATEGY_OPTIONS}
                value={mappingStrategy}
                onChange={(val) => val && setMappingStrategy(val)}
                required
              />
            </Stack>
          </Grid.Col>
          
          <Grid.Col span={{ base: 12, md: 6 }}>
            <Card withBorder p="sm" radius="md" mb="md">
              <Title order={5} mb="xs">Configuration Summary</Title>
              <Stack gap="xs">
                <Text size="sm">
                  <strong>Session ID:</strong> {sessionId}
                </Text>
                <Text size="sm">
                  <strong>Source Column:</strong> {selectedColumn}
                </Text>
                <Text size="sm">
                  <strong>Target:</strong> {DATA_SOURCE_OPTIONS.find(opt => opt.value === targetDataSource)?.label || 'Not selected'}
                </Text>
                <Text size="sm">
                  <strong>Strategy:</strong> {STRATEGY_OPTIONS.find(opt => opt.value === mappingStrategy)?.label}
                </Text>
              </Stack>
            </Card>
            
            <Card withBorder p="sm" radius="md">
              <Title order={5} mb="xs">About {STRATEGY_OPTIONS.find(opt => opt.value === mappingStrategy)?.label}</Title>
              {mappingStrategy === 'direct_mapping' && (
                <Text size="sm">
                  Direct mapping uses a straightforward approach to match identifiers 
                  from your source data to the target ontology using exact matches 
                  and standard identifier resolution.
                </Text>
              )}
              {mappingStrategy === 'bidirectional_validation' && (
                <Text size="sm">
                  Bidirectional validation performs mapping in both directions 
                  (source to target and target to source) to ensure consistency 
                  and improve accuracy by validating mappings from both perspectives.
                </Text>
              )}
              {mappingStrategy === 'iterative_mapping' && (
                <Text size="sm">
                  Iterative mapping uses multiple passes to progressively refine 
                  mappings, using results from previous iterations to improve 
                  accuracy and find indirect relationships.
                </Text>
              )}
              {mappingStrategy === 'composite_mapping' && (
                <Text size="sm">
                  Composite mapping handles complex identifiers that may contain 
                  multiple components, splitting and mapping each part individually 
                  before combining the results.
                </Text>
              )}
            </Card>
          </Grid.Col>
        </Grid>
      </Card>

      <Group justify="center">
        <Button 
          size="lg" 
          onClick={handleSubmit}
          loading={isSubmitting}
          disabled={!targetDataSource}
        >
          Start Mapping
        </Button>
      </Group>
    </Paper>
  );
}