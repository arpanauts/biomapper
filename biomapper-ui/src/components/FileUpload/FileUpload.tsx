import React, { useCallback, useState } from 'react';
import { FileButton, Button, Text, Group, Stack, Alert, Progress, Paper } from '@mantine/core';
import { IconUpload, IconAlertCircle } from '@tabler/icons-react';
import { useAppStore } from '../../store/appStore';

export const FileUpload: React.FC = () => {
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  
  const { setSession, setActiveStep, setLoading, setError } = useAppStore();

  const handleFileUpload = useCallback(async (file: File | null) => {
    if (!file) return;

    // Reset state
    setUploadError(null);
    setUploadProgress(0);
    setIsUploading(true);
    setLoading(true);
    setError(null);

    try {
      // Simulate file upload
      const mockUpload = async () => {
        for (let i = 0; i <= 100; i += 10) {
          setUploadProgress(i);
          await new Promise(resolve => setTimeout(resolve, 100));
        }
        
        // Mock successful response
        return {
          session_id: `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          filename: file.name,
        };
      };

      const response = await mockUpload();

      // Update global state with session info
      setSession(response.session_id, response.filename);

      // Advance to next step
      setActiveStep('columns');

      console.log('File uploaded successfully:', response);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to upload file';
      setUploadError(errorMessage);
      setError(errorMessage);
      console.error('Upload error:', error);
    } finally {
      setIsUploading(false);
      setLoading(false);
      setUploadProgress(0);
    }
  }, [setSession, setActiveStep, setLoading, setError]);

  return (
    <Paper shadow="sm" p="md" radius="md">
      <Stack gap="md">
        <Text size="lg" fw={500}>Upload Your Data File</Text>
        <Text size="sm" c="dimmed">
          Select a CSV or TSV file to begin the mapping process
        </Text>

        <FileButton
          onChange={handleFileUpload}
          accept=".csv,.tsv"
          disabled={isUploading}
        >
          {(props) => (
            <Button
              {...props}
              leftSection={<IconUpload size={16} />}
              loading={isUploading}
              size="lg"
              fullWidth
            >
              {isUploading ? 'Uploading...' : 'Choose File'}
            </Button>
          )}
        </FileButton>

        {isUploading && (
          <Stack gap="xs">
            <Progress
              value={uploadProgress}
              size="xl"
              radius="md"
              animated
            />
            <Text size="sm" ta="center">{uploadProgress}%</Text>
          </Stack>
        )}

        {uploadError && (
          <Alert
            icon={<IconAlertCircle size={16} />}
            title="Upload Failed"
            color="red"
            variant="light"
          >
            {uploadError}
          </Alert>
        )}

        <Group justify="space-between" mt="xs">
          <Text size="xs" c="dimmed">
            Supported formats: CSV, TSV
          </Text>
          <Text size="xs" c="dimmed">
            Maximum file size: 100MB
          </Text>
        </Group>
      </Stack>
    </Paper>
  );
};