import { AppShell, Burger, NavLink, Text, Title } from '@mantine/core'
import { useDisclosure } from '@mantine/hooks'
import {
  IconFileUpload,
  IconColumns,
  IconRoute,
  IconChartDots
} from '@tabler/icons-react'

function App() {
  const [opened, { toggle }] = useDisclosure()

  return (
    <AppShell
      header={{ height: 60 }}
      navbar={{
        width: 300,
        breakpoint: 'sm',
        collapsed: { mobile: !opened }
      }}
      padding="md"
    >
      <AppShell.Header>
        <div style={{ display: 'flex', alignItems: 'center', height: '100%', padding: '0 20px' }}>
          <Burger
            opened={opened}
            onClick={toggle}
            hiddenFrom="sm"
            size="sm"
          />
          <Title order={3} style={{ marginLeft: '10px' }}>
            BioMapper UI
          </Title>
        </div>
      </AppShell.Header>

      <AppShell.Navbar p="md">
        <NavLink
          label="Upload"
          leftSection={<IconFileUpload size="1.2rem" stroke={1.5} />}
          description="Upload your CSV file"
        />
        <NavLink
          label="Column Selection"
          leftSection={<IconColumns size="1.2rem" stroke={1.5} />}
          description="Select identifier columns"
        />
        <NavLink
          label="Mapping Configuration"
          leftSection={<IconRoute size="1.2rem" stroke={1.5} />}
          description="Configure mapping parameters"
        />
        <NavLink
          label="Results"
          leftSection={<IconChartDots size="1.2rem" stroke={1.5} />}
          description="View mapping results"
        />
      </AppShell.Navbar>

      <AppShell.Main>
        <Text>Welcome to BioMapper UI</Text>
        <Text c="dimmed" size="sm">
          Select a workflow step from the sidebar to begin
        </Text>
      </AppShell.Main>
    </AppShell>
  )
}

export default App