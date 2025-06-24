import { useState } from 'react';
import { Button, Card, Group, Paper, Text, Title, rem, Progress } from '@mantine/core';
import { Dropzone, type FileWithPath } from '@mantine/dropzone';
import { IconCloudUpload, IconDownload, IconX } from '@tabler/icons-react';
import { notifications } from '@mantine/notifications';
import { fileApi } from '../../services/api';
import { useAppStore } from '../../store/appStore';

export default function FileUpload() {
  const [selectedFile, setSelectedFile] = useState<FileWithPath | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const { setSessionId, setFilename, setActiveStep } = useAppStore();

  const handleDrop = (files: FileWithPath[]) => {
    if (files.length > 0) {
      setSelectedFile(files[0]);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      notifications.show({
        title: 'Warning',
        message: 'Please select a file to upload',
        color: 'yellow',
      });
      return;
    }

    try {
      setIsUploading(true);
      setUploadProgress(0);

      const onProgress = (progressEvent: any) => {
        const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        setUploadProgress(percentCompleted);
      };

      const result = await fileApi.uploadFile(selectedFile, onProgress);

      if (!result || !result.session_id) {
        throw new Error('Invalid response from server');
      }

      notifications.show({
        title: 'Success',
        message: 'File uploaded successfully',
        color: 'green',
      });

      setSessionId(result.session_id);
      setFilename(selectedFile.name);
      setActiveStep('columns');
    } catch (error) {
      console.error('Upload error:', error);
      notifications.show({
        title: 'Error',
        message: `Failed to upload file: ${error instanceof Error ? error.message : 'Unknown error'}`,
        color: 'red',
      });
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <Paper p="xl" radius="md">
      <Title order={2} mb="md">Upload CSV File</Title>
      <Text mb="lg" c="dimmed">
        Start the mapping process by uploading a CSV file containing biological identifiers.
      </Text>

      <Card withBorder radius="md" mb="xl">
        <Dropzone
          onDrop={handleDrop}
          maxSize={100 * 1024 * 1024} // 100MB
          accept={['text/csv', 'application/vnd.ms-excel']}
          loading={isUploading}
        >
          <Group justify="center" gap="xl" mih={220} style={{ pointerEvents: 'none' }}>
            <Dropzone.Accept>
              <IconDownload
                style={{ width: rem(52), height: rem(52), color: 'var(--mantine-color-blue-6)' }}
                stroke={1.5}
              />
            </Dropzone.Accept>
            <Dropzone.Reject>
              <IconX
                style={{ width: rem(52), height: rem(52), color: 'var(--mantine-color-red-6)' }}
                stroke={1.5}
              />
            </Dropzone.Reject>
            <Dropzone.Idle>
              <IconCloudUpload
                style={{ width: rem(52), height: rem(52), color: 'var(--mantine-color-dimmed)' }}
                stroke={1.5}
              />
            </Dropzone.Idle>

            <div>
              <Text size="xl" inline>
                Drag a CSV file here or click to select
              </Text>
              <Text size="sm" c="dimmed" inline mt={7}>
                Files up to 100MB are supported
              </Text>
            </div>
          </Group>
        </Dropzone>
      </Card>

      {selectedFile && (
        <>
          <Group mb="md">
            <Text fw={500}>Selected file:</Text>
            <Text>{selectedFile.name} ({(selectedFile.size / (1024 * 1024)).toFixed(2)} MB)</Text>
          </Group>
          
          {isUploading && (
            <Card withBorder p="sm" mb="md">
              <Text size="sm" mb="xs">Uploading file...</Text>
              <Progress 
                value={uploadProgress} 
                size="lg" 
                striped 
                animated={uploadProgress < 100}
                mb="xs"
              />
              <Text size="xs" c="dimmed">{uploadProgress}% complete</Text>
            </Card>
          )}
        </>
      )}

      <Group justify="center">
        <Button 
          size="lg" 
          onClick={handleUpload}
          loading={isUploading}
          disabled={!selectedFile}
        >
          Upload and Continue
        </Button>
      </Group>
    </Paper>
  );
}