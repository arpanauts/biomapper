import { useState, useEffect } from 'react';
import { Button, Card, Group, Paper, Text, Title, rem, Progress } from '@mantine/core';
import { Dropzone, FileWithPath } from '@mantine/dropzone';
import { IconCloudUpload, IconDownload, IconX } from '@tabler/icons-react';
import { notifications } from '@mantine/notifications';
import { useMutation } from '@tanstack/react-query';
import { fileApi } from '../../services/api';

interface FileUploadProps {
  onFileUploaded: (sessionId: string, filename: string) => void;
}

export default function FileUpload({ onFileUploaded }: FileUploadProps) {
  const [selectedFile, setSelectedFile] = useState<FileWithPath | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [maxFileSize, setMaxFileSize] = useState(1024 * 1024 * 1024); // Default to 1GB

  // Get system memory info when component mounts
  useEffect(() => {
    // Check if we're in a browser environment
    if (typeof navigator !== 'undefined') {
      // Get rough estimate of available memory if possible
      // @ts-ignore - deviceMemory is not in all TypeScript definitions yet
      if (navigator.deviceMemory) {
        // @ts-ignore
        const memoryGB = navigator.deviceMemory;
        // Set max file size to half of available memory (in bytes)
        const halfMemoryBytes = memoryGB * 1024 * 1024 * 1024 / 2;
        setMaxFileSize(halfMemoryBytes);
        console.log(`Setting max file size to ${halfMemoryBytes / (1024 * 1024)} MB based on ${memoryGB}GB device memory`);
      }
    }
  }, []);

  // Upload file mutation with improved error handling and progress tracking
  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      try {
        console.log('FileUpload component: Starting file upload for', file.name);
        setUploadProgress(0);
        
        const onProgress = (progressEvent: any) => {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          setUploadProgress(percentCompleted);
          console.log(`Upload progress: ${percentCompleted}%`);
        };
        
        const result = await fileApi.uploadFile(file, onProgress);
        
        // Validate response
        if (!result || !result.session_id) {
          console.error('FileUpload component: Invalid response from API', result);
          throw new Error('Invalid response from server. Missing session ID.');
        }
        
        console.log('FileUpload component: Successful upload with session ID:', result.session_id);
        return result;
      } catch (err) {
        console.error('FileUpload component: Error in mutation function:', err);
        throw err;
      }
    },
    onSuccess: (data) => {
      console.log('FileUpload component: Upload success data:', data);
      
      // Check if data exists and has the expected structure
      if (!data) {
        console.error('FileUpload component: Upload response data is null or undefined');
        notifications.show({
          title: 'Error',
          message: 'File uploaded but response data is missing',
          color: 'red',
        });
        return;
      }
      
      // Log the session ID for debugging
      console.log('Session ID from response:', data.session_id);
      
      // Validate the session ID
      if (!data.session_id) {
        console.error('FileUpload component: Session ID is missing from response');
        notifications.show({
          title: 'Error',
          message: 'File uploaded but session ID is missing from response',
          color: 'red',
        });
        return;
      }
      
      notifications.show({
        title: 'Success',
        message: 'File uploaded successfully',
        color: 'green',
      });
      
      if (selectedFile) {
        // Call the parent callback with session ID and filename
        console.log('Calling onFileUploaded with:', data.session_id, selectedFile.name);
        onFileUploaded(data.session_id, selectedFile.name);
      }
    },
    onError: (error) => {
      console.error('FileUpload component: Upload error in onError handler:', error);
      notifications.show({
        title: 'Error',
        message: `Failed to upload file: ${error instanceof Error ? error.message : 'Unknown error'}`,
        color: 'red',
      });
    },
  });

  // Handle file drop
  const handleDrop = (files: FileWithPath[]) => {
    if (files.length > 0) {
      setSelectedFile(files[0]);
    }
  };

  // Handle upload button click
  const handleUpload = () => {
    if (selectedFile) {
      uploadMutation.mutate(selectedFile);
    } else {
      notifications.show({
        title: 'Warning',
        message: 'Please select a file to upload',
        color: 'yellow',
      });
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
          maxSize={maxFileSize} // Dynamic based on system memory
          accept={['text/csv', 'application/vnd.ms-excel']}
          loading={uploadMutation.isPending}
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
                Files up to {(maxFileSize / (1024 * 1024)).toFixed(0)} MB are supported
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
          
          {uploadMutation.isPending && (
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
          loading={uploadMutation.isPending}
          disabled={!selectedFile}
        >
          Upload and Continue
        </Button>
      </Group>
    </Paper>
  );
}
