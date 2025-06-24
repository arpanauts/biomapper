import { MantineProvider } from '@mantine/core';
import { Notifications } from '@mantine/notifications';
import '@mantine/core/styles.css';
import '@mantine/notifications/styles.css';
import MappingConfig from './components/MappingConfig';

// Demo app to test MappingConfig component in isolation
export default function MappingConfigDemo() {
  return (
    <MantineProvider>
      <Notifications />
      <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '2rem' }}>
        <h1 style={{ marginBottom: '2rem' }}>MappingConfig Component Demo</h1>
        <MappingConfig />
      </div>
    </MantineProvider>
  );
}