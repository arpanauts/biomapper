import { useState, useEffect } from 'react';
import { 
  AppShell, 
  Burger, 
  Group, 
  NavLink, 
  ScrollArea, 
  Text, 
  Title, 
  ActionIcon, 
  useMantineColorScheme,
  Center,
  MantineProvider
} from '@mantine/core';
import { Notifications } from '@mantine/notifications';
import { 
  IconFileUpload, 
  IconTable, 
  IconDna, 
  IconFileAnalytics, 
  IconSun, 
  IconMoon 
} from '@tabler/icons-react';
import '@mantine/core/styles.css';
import '@mantine/notifications/styles.css';

// Import components
import FileUpload from './components/FileUpload/FileUpload';
import ColumnSelection from './components/ColumnSelection/ColumnSelection';
import MappingConfig from './components/MappingConfig/MappingConfig';
import Results from './components/Results/Results';

// Import store
import { useAppStore } from './store/appStore';

function AppContent() {
  const [opened, setOpened] = useState(false);
  const { colorScheme, toggleColorScheme } = useMantineColorScheme();
  const { activeStep, sessionId, jobId, filename, setActiveStep } = useAppStore();

  // Recover session from sessionStorage on app init
  useEffect(() => {
    const storedSessionId = sessionStorage.getItem('biomapper_current_session');
    const storedFilename = sessionStorage.getItem('biomapper_current_filename');
    
    if (storedSessionId && !sessionId) {
      useAppStore.getState().setSessionId(storedSessionId);
      
      if (storedFilename) {
        useAppStore.getState().setFilename(storedFilename);
      }
      
      // If we're on the upload page but have a valid session, move to columns
      if (activeStep === 'upload') {
        setActiveStep('columns');
      }
    }
  }, []);

  // Store session in sessionStorage when it changes
  useEffect(() => {
    if (sessionId) {
      sessionStorage.setItem('biomapper_current_session', sessionId);
    }
    if (filename) {
      sessionStorage.setItem('biomapper_current_filename', filename);
    }
  }, [sessionId, filename]);

  // Workflow step items (sidebar)
  const navItems = [
    { label: 'Upload File', icon: IconFileUpload, step: 'upload' as const },
    { label: 'Select Columns', icon: IconTable, step: 'columns' as const },
    { label: 'Configure Mapping', icon: IconDna, step: 'mapping' as const },
    { label: 'View Results', icon: IconFileAnalytics, step: 'results' as const },
  ];

  return (
    <AppShell
      header={{ height: 60 }}
      navbar={{
        width: 300,
        breakpoint: 'sm',
        collapsed: { mobile: !opened },
      }}
      padding="md"
    >
      <AppShell.Header>
        <Group h="100%" px="md">
          <Burger
            opened={opened}
            onClick={() => setOpened((o) => !o)}
            hiddenFrom="sm"
            size="sm"
          />
          <Group justify="space-between" style={{ flex: 1 }}>
            <Title order={3}>BioMapper</Title>
            <Group>
              {filename && (
                <Text size="sm" c="dimmed">
                  Working with: {filename}
                </Text>
              )}
              <ActionIcon
                variant="outline"
                color={colorScheme === 'dark' ? 'yellow' : 'blue'}
                onClick={() => toggleColorScheme()}
                title={`Switch to ${colorScheme === 'dark' ? 'light' : 'dark'} mode`}
              >
                {colorScheme === 'dark' ? <IconSun size={18} /> : <IconMoon size={18} />}
              </ActionIcon>
            </Group>
          </Group>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar p="md">
        <AppShell.Section>
          <Text fw={500} size="sm" pb="xs">
            Workflow Steps
          </Text>
        </AppShell.Section>
        <AppShell.Section grow component={ScrollArea}>
          {navItems.map((item) => (
            <NavLink
              key={item.step}
              label={item.label}
              leftSection={<item.icon size={16} />}
              active={activeStep === item.step}
              onClick={() => {
                // Only allow navigation to steps that are accessible
                if (
                  (item.step === 'upload') ||
                  (item.step === 'columns' && sessionId) ||
                  (item.step === 'mapping' && sessionId) ||
                  (item.step === 'results' && jobId)
                ) {
                  setActiveStep(item.step);
                }
              }}
              disabled={
                (item.step === 'columns' && !sessionId) ||
                (item.step === 'mapping' && !sessionId) ||
                (item.step === 'results' && !jobId)
              }
            />
          ))}
        </AppShell.Section>
      </AppShell.Navbar>

      <AppShell.Main>
        {/* Conditional rendering based on activeStep */}
        {activeStep === 'upload' && <FileUpload />}
        
        {activeStep === 'columns' && sessionId && <ColumnSelection />}
        
        {activeStep === 'mapping' && sessionId && <MappingConfig />}
        
        {activeStep === 'results' && jobId && <Results />}

        {/* Fallback for invalid state */}
        {((activeStep === 'columns' && !sessionId) || 
          (activeStep === 'mapping' && !sessionId) || 
          (activeStep === 'results' && !jobId)) && (
          <Center h={400}>
            <Text>Please upload a file first to start the mapping process.</Text>
          </Center>
        )}
      </AppShell.Main>
    </AppShell>
  );
}

function App() {
  return (
    <MantineProvider>
      <Notifications />
      <AppContent />
    </MantineProvider>
  );
}

export default App;