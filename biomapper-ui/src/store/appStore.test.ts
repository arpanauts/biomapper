import { useAppStore } from './appStore'

describe('appStore', () => {
  beforeEach(() => {
    useAppStore.setState({
      activeStep: 'upload',
      sessionId: null,
      filename: null,
      jobId: null,
      isLoading: false,
      error: null
    })
  })

  describe('initial state', () => {
    test('should have correct initial values', () => {
      const state = useAppStore.getState()
      
      expect(state.activeStep).toBe('upload')
      expect(state.sessionId).toBeNull()
      expect(state.filename).toBeNull()
      expect(state.jobId).toBeNull()
      expect(state.isLoading).toBe(false)
      expect(state.error).toBeNull()
    })
  })

  describe('actions', () => {
    test('setSession should update sessionId and filename', () => {
      const { setSession } = useAppStore.getState()
      
      setSession('test-session-123', 'test-file.csv')
      
      const state = useAppStore.getState()
      expect(state.sessionId).toBe('test-session-123')
      expect(state.filename).toBe('test-file.csv')
    })

    test('setJobId should update jobId', () => {
      const { setJobId } = useAppStore.getState()
      
      setJobId('job-456')
      
      const state = useAppStore.getState()
      expect(state.jobId).toBe('job-456')
    })

    test('setActiveStep should update activeStep', () => {
      const { setActiveStep } = useAppStore.getState()
      
      setActiveStep('columns')
      expect(useAppStore.getState().activeStep).toBe('columns')
      
      setActiveStep('mapping')
      expect(useAppStore.getState().activeStep).toBe('mapping')
      
      setActiveStep('results')
      expect(useAppStore.getState().activeStep).toBe('results')
    })

    test('reset should restore initial state', () => {
      const { setSession, setJobId, setActiveStep, setLoading, setError, reset } = useAppStore.getState()
      
      // Set some values
      setSession('session-123', 'file.csv')
      setJobId('job-789')
      setActiveStep('results')
      setLoading(true)
      setError('Some error')
      
      // Verify values are set
      let state = useAppStore.getState()
      expect(state.sessionId).toBe('session-123')
      expect(state.filename).toBe('file.csv')
      expect(state.jobId).toBe('job-789')
      expect(state.activeStep).toBe('results')
      expect(state.isLoading).toBe(true)
      expect(state.error).toBe('Some error')
      
      // Reset
      reset()
      
      // Verify initial state is restored
      state = useAppStore.getState()
      expect(state.activeStep).toBe('upload')
      expect(state.sessionId).toBeNull()
      expect(state.filename).toBeNull()
      expect(state.jobId).toBeNull()
      expect(state.isLoading).toBe(false)
      expect(state.error).toBeNull()
    })

    test('setLoading should update isLoading', () => {
      const { setLoading } = useAppStore.getState()
      
      setLoading(true)
      expect(useAppStore.getState().isLoading).toBe(true)
      
      setLoading(false)
      expect(useAppStore.getState().isLoading).toBe(false)
    })

    test('setError should update error', () => {
      const { setError } = useAppStore.getState()
      
      setError('Test error message')
      expect(useAppStore.getState().error).toBe('Test error message')
      
      setError(null)
      expect(useAppStore.getState().error).toBeNull()
    })
  })

  describe('state persistence', () => {
    test('state should persist across multiple updates', () => {
      const { setSession, setActiveStep, setJobId } = useAppStore.getState()
      
      setSession('session-1', 'file1.csv')
      setActiveStep('columns')
      
      let state = useAppStore.getState()
      expect(state.sessionId).toBe('session-1')
      expect(state.filename).toBe('file1.csv')
      expect(state.activeStep).toBe('columns')
      
      setJobId('job-1')
      setActiveStep('mapping')
      
      state = useAppStore.getState()
      expect(state.sessionId).toBe('session-1')
      expect(state.filename).toBe('file1.csv')
      expect(state.jobId).toBe('job-1')
      expect(state.activeStep).toBe('mapping')
    })
  })
})