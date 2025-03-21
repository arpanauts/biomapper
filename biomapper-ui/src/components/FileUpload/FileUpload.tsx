import { useState, useEffect } from 'react';
import { Button, Card, Group, Paper, Text, Title, rem, Progress, Divider } from '@mantine/core';
import { TextInput, Select } from '@mantine/core';
import { Dropzone, FileWithPath } from '@mantine/dropzone';
import { IconCloudUpload, IconDownload, IconX, IconFolder, IconFile, IconServer } from '@tabler/icons-react';
import { notifications } from '@mantine/notifications';
import { useMutation, useQuery } from '@tanstack/react-query';
import { fileApi } from '../../services/api';

interface FileUploadProps {
  onFileUploaded: (sessionId: string, filename: string) => void;
}

export default function FileUpload({ onFileUploaded }: FileUploadProps) {
  // File upload states
  const [selectedFile, setSelectedFile] = useState<FileWithPath | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [maxFileSize, setMaxFileSize] = useState(1024 * 1024 * 1024); // Default to 1GB
  
  // Server file selection states
  const [directoryPath, setDirectoryPath] = useState('');
  const [selectedServerFile, setSelectedServerFile] = useState<string | null>(null);
  const [serverFiles, setServerFiles] = useState<Array<{name: string, path: string, size: number}>>([]);

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
  
  // Query to list server files
  const serverFilesQuery = useQuery({
    queryKey: ['serverFiles', directoryPath],
    queryFn: async () => {
      try {
        console.log('Listing files from directory:', directoryPath);
        
        // Verify directory path is not empty
        if (!directoryPath.trim()) {
          throw new Error('Directory path cannot be empty');
        }
        
        const files = await fileApi.listServerFiles(directoryPath);
        console.log('Files returned from server:', files);
        setServerFiles(files);
        
        // Show success notification
        notifications.show({
          title: 'Success',
          message: `Found ${files.length} files in ${directoryPath}`,
          color: 'green',
        });
        
        return files;
      } catch (error: any) {
        console.error('Error fetching server files:', error);
        
        // Enhanced error logging
        if (error.response) {
          console.error('Server response:', error.response.data);
          console.error('Status code:', error.response.status);
          
          notifications.show({
            title: 'Server Error',
            message: `Failed to list server files: ${error.response.data?.detail || error.response.statusText}`,
            color: 'red',
          });
        } else if (error.request) {
          console.error('No response received from server');
          notifications.show({
            title: 'Network Error',
            message: 'No response received from server. Is the API server running?',
            color: 'red',
          });
        } else {
          notifications.show({
            title: 'Error',
            message: `Failed to list server files: ${error.message || 'Unknown error'}`,
            color: 'red',
          });
        }
        return [];
      }
    },
    enabled: !!directoryPath,
  });

  // Upload file mutation with improved error handling and progress tracking
  // Mutation to load a file from the server
  const loadServerFileMutation = useMutation({
    mutationFn: async (filePath: string) => {
      try {
        console.log('FileUpload component: Loading server file:', filePath);
        
        const result = await fileApi.loadServerFile(filePath);
        
        // Validate response
        if (!result || !result.session_id) {
          console.error('FileUpload component: Invalid response from API', result);
          throw new Error('Invalid response from server. Missing session ID.');
        }
        
        console.log('FileUpload component: Successfully loaded server file with session ID:', result.session_id);
        return result;
      } catch (err) {
        console.error('FileUpload component: Error loading server file:', err);
        throw err;
      }
    },
    onSuccess: (data) => {
      console.log('FileUpload component: Server file load success data:', data);
      
      if (!data || !data.session_id) {
        console.error('FileUpload component: Session ID is missing from response');
        notifications.show({
          title: 'Error',
          message: 'File loaded but session ID is missing from response',
          color: 'red',
        });
        return;
      }
      
      notifications.show({
        title: 'Success',
        message: `File ${data.filename} loaded successfully from server`,
        color: 'green',
      });
      
      // Call the parent callback with session ID and filename
      onFileUploaded(data.session_id, data.filename);
    },
    onError: (error) => {
      console.error('FileUpload component: Error loading server file:', error);
      notifications.show({
        title: 'Error',
        message: `Failed to load server file: ${error instanceof Error ? error.message : 'Unknown error'}`,
        color: 'red',
      });
    },
  });
  
  // Handle directory path change
  const handleDirectoryChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setDirectoryPath(event.target.value);
  };
  
  // Handle server file selection
  const handleServerFileSelect = (value: string | null) => {
    setSelectedServerFile(value);
  };
  
  // Handle loading the selected server file
  const handleLoadServerFile = () => {
    if (selectedServerFile) {
      console.log('Loading server file with full path:', selectedServerFile);
      
      // Validate path has proper extension
      const lowerPath = selectedServerFile.toLowerCase();
      if (!lowerPath.endsWith('.csv') && !lowerPath.endsWith('.tsv')) {
        notifications.show({
          title: 'Error',
          message: 'Only .csv and .tsv files are supported',
          color: 'red',
        });
        return;
      }
      
      // Check if the file exists on the server
      const selectedFile = serverFiles.find(file => file.path === selectedServerFile);
      if (!selectedFile) {
        notifications.show({
          title: 'Error',
          message: 'The selected file no longer exists in the server directory',
          color: 'red',
        });
        return;
      }
      
      loadServerFileMutation.mutate(selectedServerFile);
    } else {
      notifications.show({
        title: 'Warning',
        message: 'Please select a file from the server',
        color: 'yellow',
      });
    }
  };
  
  // Handle refreshing the file list
  const handleRefreshFileList = () => {
    serverFilesQuery.refetch();
  };

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

      <Group justify="center" mb="xl">
        <Button 
          size="lg" 
          onClick={handleUpload}
          loading={uploadMutation.isPending}
          disabled={!selectedFile}
        >
          Upload and Continue
        </Button>
      </Group>

      <Divider my="xl" label="OR" labelPosition="center" />

      <Title order={2} mb="md">Select Server File</Title>
      <Text mb="lg" c="dimmed">
        Alternatively, select a file directly from the server's filesystem.
      </Text>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <TextInput
          label="Server Directory Path"
          placeholder="Enter server directory path"
          value={directoryPath}
          onChange={handleDirectoryChange}
          rightSection={
            <Button size="xs" variant="subtle" onClick={handleRefreshFileList} disabled={serverFilesQuery.isFetching}>
              Refresh
            </Button>
          }
        />
        {/* Add folder icon visually */}
        <div style={{ marginTop: '-38px', marginLeft: '12px', position: 'relative', pointerEvents: 'none', zIndex: 1 }}>
          <IconFolder size={16} color="gray" />
        </div>

        <div style={{ position: 'relative' }}>
          <Select
            label="Available Files"
            placeholder="Select a file from the server"
            value={selectedServerFile}
            onChange={handleServerFileSelect}
            data={serverFiles.map(file => ({
              value: file.path,
              label: `${file.name} (${(file.size / (1024 * 1024)).toFixed(2)} MB)`
            }))}
            searchable
            disabled={serverFilesQuery.isLoading || serverFiles.length === 0}
          />
          {/* Add file icon visually */}
          <div style={{ position: 'absolute', top: '35px', left: '12px', pointerEvents: 'none' }}>
            <IconFile size={16} color="gray" />
          </div>
        </div>
        
        {serverFiles.length === 0 && !serverFilesQuery.isLoading && (
          <Text size="sm" c="dimmed">No files found in directory</Text>
        )}

        {serverFilesQuery.isLoading && (
          <Text size="sm" c="dimmed">Loading files from server...</Text>
        )}

        {serverFiles.length > 0 && (
          <Text size="sm" c="dimmed">{serverFiles.length} files found in directory</Text>
        )}

        <Group justify="center">
          <Button
            size="lg"
            leftSection={<IconServer size={20} />}
            onClick={handleLoadServerFile}
            loading={loadServerFileMutation.isPending}
            disabled={!selectedServerFile}
          >
            Load Server File
          </Button>
        </Group>
      </div>
    </Paper>
  );
}
