import './crypto-polyfill.js'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { MantineProvider, createTheme } from '@mantine/core'
import { Notifications } from '@mantine/notifications'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import '@mantine/core/styles.css'
import '@mantine/notifications/styles.css'
import '@mantine/dates/styles.css'
import '@mantine/dropzone/styles.css'
import './index.css'
import App from './App'

// Create the theme with custom properties
const theme = createTheme({
  primaryColor: 'blue',
  // Add scientific theme customizations
  fontFamily: 'Inter, system-ui, -apple-system, sans-serif',
  // Add dark mode optimized colors
  colors: {
    // Custom scientific color scheme optimized for biological data
    bioBlue: ['#edf2ff', '#dce4ff', '#b3c0ff', '#8a9eff', '#6380ff', '#4366f7', '#3355dd', '#2644c0', '#1a339f', '#0c2383'],
  },
})

// Create React Query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <MantineProvider theme={theme} defaultColorScheme="dark">
        <Notifications position="top-right" />
        <App />
      </MantineProvider>
    </QueryClientProvider>
  </StrictMode>,
)
