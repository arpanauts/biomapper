import { useState, useEffect } from 'react'
import axios from 'axios'
import './App.css'

interface HealthResponse {
  status: string
  version: string
}

function App() {
  const [apiStatus, setApiStatus] = useState<string>('Loading...')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const response = await axios.get<HealthResponse>('/api/health/')
        setApiStatus(`API Status: ${response.data.status} (v${response.data.version})`)
        setError(null)
      } catch (err) {
        setApiStatus('API Status: Error')
        setError(err instanceof Error ? err.message : 'Unknown error occurred')
      }
    }

    checkHealth()
  }, [])

  return (
    <>
      <div>
        <h1>Biomapper UI</h1>
        <div className="card">
          <h2>{apiStatus}</h2>
          {error && (
            <p style={{ color: 'red' }}>
              Error details: {error}
            </p>
          )}
          <p>
            This UI is successfully connected to the Biomapper API.
          </p>
        </div>
      </div>
    </>
  )
}

export default App