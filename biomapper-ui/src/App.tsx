import { useState, useEffect } from 'react'
import { AppShell, Burger, Center, Group, NavLink, ScrollArea, Text, Title, Tabs, rem, ActionIcon, useMantineColorScheme } from '@mantine/core'
import { IconDna, IconFileAnalytics, IconFileUpload, IconTable, IconAtom, IconBraces, IconNetwork, IconArrowsExchange, IconSun, IconMoon } from '@tabler/icons-react'
import './App.css'

// Import pages/components
import FileUpload from './components/FileUpload/FileUpload'
import ColumnSelection from './components/ColumnSelection/ColumnSelection'
import MappingConfig from './components/MappingConfig/MappingConfig'
import Results from './components/Results/Results'

// Define the app steps
// Define the app steps
type AppStep = 'upload' | 'columns' | 'mapping' | 'results'

// Define feature domains
type FeatureDomain = 'entity-mapping' | 'data-harmonization' | 'llm-integration' | 'spoke-explorer'

function App() {
  // Add this line to debug if the component is rendering
  console.log('App component is rendering');
  
  const [opened, setOpened] = useState(false)
  const [activeFeature, setActiveFeature] = useState<FeatureDomain>('entity-mapping')
  const [activeStep, setActiveStep] = useState<AppStep>('upload')
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [jobId, setJobId] = useState<string | null>(null)
  const [filename, setFilename] = useState<string | null>(null)
  
  // Get color scheme and toggle function from Mantine
  const { colorScheme, toggleColorScheme } = useMantineColorScheme()

  // Handle successful file upload
  const handleFileUploaded = (newSessionId: string, uploadedFilename: string) => {
    console.log(`App: File uploaded with session ID ${newSessionId}`);
    
    // Validate the session ID
    if (!newSessionId) {
      console.error('App: Received empty session ID from file upload');
      return;
    }
    
    // Use the function form of state setter to ensure we have the latest state
    console.log('App: Setting sessionId to:', newSessionId);
    
    // First, store session ID in sessionStorage for persistence
    sessionStorage.setItem('biomapper_current_session', newSessionId);
    console.log('App: Stored sessionId in sessionStorage as biomapper_current_session');
    
    // Then update state
    setSessionId(newSessionId);
    
    console.log('App: Setting filename to:', uploadedFilename);
    sessionStorage.setItem('biomapper_current_filename', uploadedFilename);
    setFilename(uploadedFilename);
    
    // We'll let the useEffect handle navigation after state updates
    console.log('App: State updated, navigation will happen via useEffect');
  }

  // Effect to handle navigation after sessionId is set
  useEffect(() => {
    if (sessionId && activeStep === 'upload') {
      console.log('App: useEffect detected sessionId update, navigating to columns step');
      console.log('App: Current sessionId value:', sessionId);
      setTimeout(() => {
        console.log('App: Navigating to columns step after delay');
        setActiveStep('columns');
      }, 500); // Small delay to ensure state is fully updated
    }
  }, [sessionId, activeStep]);
  
  // Effect to recover session from sessionStorage on app init
  useEffect(() => {
    const storedSessionId = sessionStorage.getItem('biomapper_current_session');
    const storedFilename = sessionStorage.getItem('biomapper_current_filename');
    
    if (storedSessionId && !sessionId) {
      console.log('App: Recovered sessionId from sessionStorage:', storedSessionId);
      setSessionId(storedSessionId);
      
      if (storedFilename) {
        console.log('App: Recovered filename from sessionStorage:', storedFilename);
        setFilename(storedFilename);
      }
      
      // If we're on the upload page but have a valid session, move to columns
      if (activeStep === 'upload') {
        console.log('App: Have valid session, moving to columns step');
        setActiveStep('columns');
      }
    }
  }, []);
  
  // Debug effect to monitor all state changes
  useEffect(() => {
    console.log('App: State update - sessionId:', sessionId, 'activeStep:', activeStep, 'filename:', filename);
  }, [sessionId, activeStep, filename]);
  
  // Handle column selection completion
  const handleColumnsSelected = () => {
    setActiveStep('mapping')
  }

  // Handle mapping job creation
  const handleMappingStarted = (newJobId: string) => {
    setJobId(newJobId)
    setActiveStep('results')
  }

  // Handle reset to start new mapping
  const handleReset = () => {
    setSessionId(null)
    setJobId(null)
    setFilename(null)
    setActiveStep('upload')
  }

  // Feature domain items (top tabs)
  const featureDomains = [
    { label: 'Entity Mapping', icon: IconAtom, value: 'entity-mapping', description: 'Map biological entities to standard identifiers' },
    { label: 'Data Harmonization', icon: IconArrowsExchange, value: 'data-harmonization', description: 'Standardize and integrate multi-omic datasets', disabled: true },
    { label: 'LLM Integration', icon: IconBraces, value: 'llm-integration', description: 'AI-powered biological term mapping', disabled: true },
    { label: 'SPOKE Explorer', icon: IconNetwork, value: 'spoke-explorer', description: 'Explore the SPOKE knowledge graph', disabled: true },
  ]

  // Workflow step items (sidebar)
  const navItems = [
    { label: 'Upload File', icon: IconFileUpload, step: 'upload' },
    { label: 'Select Columns', icon: IconTable, step: 'columns' },
    { label: 'Configure Mapping', icon: IconDna, step: 'mapping' },
    { label: 'View Results', icon: IconFileAnalytics, step: 'results' },
  ]

  return (
    <AppShell
      header={{ height: 110 }}
      navbar={{
        width: 300,
        breakpoint: 'sm',
        collapsed: { mobile: !opened },
      }}
      padding="md"
    >
      <AppShell.Header>
        <Group h={60} px="md">
          <Burger
            opened={opened}
            onClick={() => setOpened((o) => !o)}
            hiddenFrom="sm"
            size="sm"
          />
          <Group justify="space-between" style={{ flex: 1 }}>
            <Title order={3}>Biomapper</Title>
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
        
        {/* Feature domain tabs */}
        <Tabs
          value={activeFeature}
          onChange={(value) => setActiveFeature(value as FeatureDomain)}
          variant="outline"
          px="md"
        >
          <Tabs.List>
            {featureDomains.map((domain) => (
              <Tabs.Tab
                key={domain.value}
                value={domain.value}
                leftSection={<domain.icon style={{ width: rem(16), height: rem(16) }} />}
                disabled={domain.disabled}
              >
                {domain.label}
              </Tabs.Tab>
            ))}
          </Tabs.List>
        </Tabs>
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
              leftSection={
                <item.icon style={{ width: rem(16), height: rem(16) }} />
              }
              active={activeStep === item.step}
              onClick={() => {
                // Only allow navigation to steps that are accessible
                if (
                  (item.step === 'upload') ||
                  (item.step === 'columns' && sessionId) ||
                  (item.step === 'mapping' && sessionId) ||
                  (item.step === 'results' && jobId)
                ) {
                  setActiveStep(item.step as AppStep)
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
        {/* Always render the component for debugging, but only show the active one */}
        <div style={{ display: activeStep === 'upload' ? 'block' : 'none' }}>
          <FileUpload onFileUploaded={handleFileUploaded} />
        </div>
        
        <div style={{ display: activeStep === 'columns' && sessionId ? 'block' : 'none' }}>
          {sessionId ? (
            <>
              {/* Console logging for debug instead of visible UI element */}
              {console.debug(`Debug Info: Rendering ColumnSelection with sessionId: ${sessionId}`)}
              <ColumnSelection 
                sessionId={sessionId} 
                onColumnsSelected={handleColumnsSelected} 
              />
            </>
          ) : (
            <div style={{padding: '10px', backgroundColor: '#ffeeee'}}>
              <strong>Error:</strong> No sessionId available for ColumnSelection
            </div>
          )}
        </div>
        
        <div style={{ display: activeStep === 'mapping' && sessionId ? 'block' : 'none' }}>
          {sessionId && (
            <MappingConfig 
              sessionId={sessionId} 
              onMappingStarted={handleMappingStarted} 
            />
          )}
        </div>
        
        <div style={{ display: activeStep === 'results' && jobId ? 'block' : 'none' }}>
          {jobId && (
            <Results 
              jobId={jobId} 
              onReset={handleReset} 
            />
          )}
        </div>

        {/* Fallback for invalid state */}
        {(activeStep === 'columns' && !sessionId) || 
         (activeStep === 'mapping' && !sessionId) || 
         (activeStep === 'results' && !jobId) ? (
          <Center h={400}>
            <Text>Please upload a file first to start the mapping process.</Text>
          </Center>
        ) : null}
      </AppShell.Main>
    </AppShell>
  )
}

export default App
