import React, { useState, useEffect, useRef } from 'react'

const API_BASE = 'http://localhost:8002/api'
const WS_BASE = 'ws://localhost:8002/ws'

const styles = {
  container: {
    padding: '20px',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '20px',
  },
  title: {
    fontSize: '18px',
    fontWeight: '600',
  },
  startSection: {
    padding: '20px',
    backgroundColor: '#f9f9f9',
    borderRadius: '8px',
    marginBottom: '20px',
  },
  sectionTitle: {
    fontSize: '16px',
    fontWeight: '600',
    marginBottom: '15px',
  },
  formGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
    gap: '15px',
    marginBottom: '15px',
  },
  formGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: '5px',
  },
  label: {
    fontSize: '12px',
    color: '#666',
    fontWeight: '500',
  },
  select: {
    padding: '10px',
    borderRadius: '6px',
    border: '1px solid #ddd',
    fontSize: '14px',
  },
  input: {
    padding: '10px',
    borderRadius: '6px',
    border: '1px solid #ddd',
    fontSize: '14px',
  },
  previewBox: {
    padding: '15px',
    backgroundColor: '#fff',
    borderRadius: '6px',
    border: '1px solid #e0e0e0',
    marginBottom: '15px',
  },
  previewText: {
    fontSize: '14px',
    color: '#333',
  },
  buttonRow: {
    display: 'flex',
    gap: '10px',
  },
  primaryButton: {
    padding: '12px 24px',
    backgroundColor: '#667eea',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: '500',
  },
  disabledButton: {
    opacity: 0.6,
    cursor: 'not-allowed',
  },
  jobList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '15px',
  },
  jobCard: {
    padding: '20px',
    backgroundColor: '#fff',
    borderRadius: '8px',
    border: '1px solid #e0e0e0',
  },
  jobHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '10px',
  },
  jobId: {
    fontSize: '14px',
    fontWeight: '600',
    color: '#333',
  },
  statusBadge: {
    padding: '4px 12px',
    borderRadius: '12px',
    fontSize: '12px',
    fontWeight: '500',
  },
  statusPending: {
    backgroundColor: '#fff3cd',
    color: '#856404',
  },
  statusRunning: {
    backgroundColor: '#cce5ff',
    color: '#004085',
  },
  statusCompleted: {
    backgroundColor: '#d4edda',
    color: '#155724',
  },
  statusFailed: {
    backgroundColor: '#f8d7da',
    color: '#721c24',
  },
  statusCancelled: {
    backgroundColor: '#e2e3e5',
    color: '#383d41',
  },
  progressSection: {
    marginTop: '10px',
  },
  progressBar: {
    height: '8px',
    backgroundColor: '#e0e0e0',
    borderRadius: '4px',
    overflow: 'hidden',
    marginBottom: '10px',
  },
  progressFill: {
    height: '100%',
    backgroundColor: '#667eea',
    transition: 'width 0.3s ease',
  },
  progressText: {
    fontSize: '13px',
    color: '#666',
  },
  statsRow: {
    display: 'flex',
    gap: '20px',
    marginTop: '10px',
  },
  statItem: {
    fontSize: '13px',
    color: '#666',
  },
  statValue: {
    fontWeight: '600',
    color: '#333',
  },
  currentBusiness: {
    marginTop: '10px',
    padding: '10px',
    backgroundColor: '#f0f0f0',
    borderRadius: '6px',
    fontSize: '13px',
    color: '#666',
  },
  cancelButton: {
    padding: '6px 12px',
    backgroundColor: '#dc3545',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '12px',
  },
  errorMessage: {
    marginTop: '10px',
    padding: '10px',
    backgroundColor: '#f8d7da',
    color: '#721c24',
    borderRadius: '6px',
    fontSize: '13px',
  },
  emptyState: {
    textAlign: 'center',
    padding: '40px',
    color: '#666',
  },
  timestamp: {
    fontSize: '12px',
    color: '#999',
    marginTop: '10px',
  },
}

function EnrichmentStatus({ categories, onRefresh }) {
  const [jobs, setJobs] = useState([])
  const [preview, setPreview] = useState(null)
  const [isStarting, setIsStarting] = useState(false)
  const wsConnections = useRef({})
  const [filter, setFilter] = useState({
    category: '',
    state: '',
    limit: 50,
    only_missing: true,
  })

  const fetchJobs = async () => {
    try {
      const res = await fetch(`${API_BASE}/enrich`)
      const data = await res.json()
      setJobs(data)
    } catch (err) {
      console.error('Failed to fetch enrichment jobs:', err)
    }
  }

  const fetchPreview = async () => {
    try {
      const params = new URLSearchParams()
      if (filter.category) params.append('category', filter.category)
      if (filter.state) params.append('state', filter.state)
      params.append('limit', filter.limit)
      params.append('only_missing', filter.only_missing)

      const res = await fetch(`${API_BASE}/enrichment/preview?${params}`)
      const data = await res.json()
      setPreview(data)
    } catch (err) {
      console.error('Failed to fetch preview:', err)
    }
  }

  useEffect(() => {
    fetchJobs()
    fetchPreview()

    // We still keep a slow poll just in case WebSocket misses something 
    // or to discover new jobs started by other tabs
    const interval = setInterval(() => {
      fetchJobs()
    }, 10000)

    return () => {
      clearInterval(interval)
      // Close all WebSockets on unmount
      Object.values(wsConnections.current).forEach(ws => ws.close())
    }
  }, [])

  // Manage WebSocket connections for running jobs
  useEffect(() => {
    const runningJobs = jobs.filter(j => j.status === 'running')
    
    runningJobs.forEach(job => {
      if (!wsConnections.current[job.id]) {
        console.log(`Connecting WebSocket for job ${job.id}`)
        const ws = new WebSocket(`${WS_BASE}/enrich/${job.id}`)
        
        ws.onmessage = (event) => {
          const data = JSON.parse(event.data)
          setJobs(prevJobs => prevJobs.map(j => {
            if (j.id === data.job_id) {
              const updatedJob = { ...j }
              if (data.type === 'progress') {
                updatedJob.processed = data.processed
                updatedJob.enriched = data.enriched
                updatedJob.failed = data.failed
              } else if (data.type === 'result') {
                updatedJob.current_business = data.contractor
                updatedJob.enriched = data.enriched
                updatedJob.failed = data.failed
                updatedJob.processed = data.processed
              } else if (data.type === 'status') {
                updatedJob.status = data.status
                if (data.error) updatedJob.error_message = data.error
              }
              return updatedJob
            }
            return j
          }))
          
          if (data.type === 'status' && (data.status === 'completed' || data.status === 'failed' || data.status === 'cancelled')) {
            ws.close()
            if (onRefresh) onRefresh()
          }
        }
        
        ws.onclose = () => {
          delete wsConnections.current[job.id]
        }
        
        wsConnections.current[job.id] = ws
      }
    })
  }, [jobs])

  useEffect(() => {
    fetchPreview()
  }, [filter])

  const handleStartEnrichment = async () => {
    if (!preview || preview.count === 0) return

    setIsStarting(true)
    try {
      const res = await fetch(`${API_BASE}/enrich`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          category: filter.category || null,
          state: filter.state || null,
          limit: filter.limit,
          thread_count: 3,
          only_missing: filter.only_missing,
        })
      })

      if (res.ok) {
        fetchJobs()
        if (onRefresh) onRefresh()
      }
    } catch (err) {
      console.error('Failed to start enrichment:', err)
    } finally {
      setIsStarting(false)
    }
  }

  const handleCancelJob = async (jobId) => {
    try {
      await fetch(`${API_BASE}/enrich/${jobId}`, { method: 'DELETE' })
      fetchJobs()
    } catch (err) {
      console.error('Failed to cancel job:', err)
    }
  }

  const getStatusStyle = (status) => {
    switch (status) {
      case 'pending': return styles.statusPending
      case 'running': return styles.statusRunning
      case 'completed': return styles.statusCompleted
      case 'failed': return styles.statusFailed
      case 'cancelled': return styles.statusCancelled
      default: return {}
    }
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return ''
    const date = new Date(dateStr)
    return date.toLocaleString()
  }

  return (
    <div style={styles.container}>
      <div style={styles.startSection}>
        <div style={styles.sectionTitle}>Start New Enrichment Job</div>
        <div style={styles.formGrid}>
          <div style={styles.formGroup}>
            <label style={styles.label}>Category (optional)</label>
            <select
              style={styles.select}
              value={filter.category}
              onChange={(e) => setFilter({ ...filter, category: e.target.value })}
            >
              <option value="">All Categories</option>
              {categories.map(cat => (
                <option key={cat.value} value={cat.value}>{cat.label}</option>
              ))}
            </select>
          </div>

          <div style={styles.formGroup}>
            <label style={styles.label}>State (optional)</label>
            <input
              type="text"
              style={styles.input}
              placeholder="e.g., WV, VA, MD"
              value={filter.state}
              onChange={(e) => setFilter({ ...filter, state: e.target.value.toUpperCase() })}
              maxLength={2}
            />
          </div>

          <div style={styles.formGroup}>
            <label style={styles.label}>Max Records</label>
            <select
              style={styles.select}
              value={filter.limit}
              onChange={(e) => setFilter({ ...filter, limit: parseInt(e.target.value) })}
            >
              <option value={10}>10 records</option>
              <option value={25}>25 records</option>
              <option value={50}>50 records</option>
              <option value={100}>100 records</option>
              <option value={200}>200 records</option>
            </select>
          </div>
        </div>

        {preview && (
          <div style={styles.previewBox}>
            <div style={styles.previewText}>
              <strong>{preview.count}</strong> contractors found matching criteria
              {preview.count > 0 && (
                <span> - Missing owner/email data will be enriched using AI search</span>
              )}
            </div>
          </div>
        )}

        <div style={styles.buttonRow}>
          <button
            style={{
              ...styles.primaryButton,
              ...((isStarting || !preview || preview.count === 0) ? styles.disabledButton : {})
            }}
            onClick={handleStartEnrichment}
            disabled={isStarting || !preview || preview.count === 0}
          >
            {isStarting ? 'Starting...' : `Start Enrichment (${preview?.count || 0} records)`}
          </button>
        </div>
      </div>

      <div style={styles.header}>
        <div style={styles.title}>Enrichment Jobs</div>
      </div>

      {jobs.length === 0 ? (
        <div style={styles.emptyState}>
          No enrichment jobs yet. Start one above!
        </div>
      ) : (
        <div style={styles.jobList}>
          {jobs.map(job => {
            const progress = job.total_records > 0
              ? Math.round((job.processed / job.total_records) * 100)
              : 0

            return (
              <div key={job.id} style={styles.jobCard}>
                <div style={styles.jobHeader}>
                  <div style={styles.jobId}>
                    Enrichment #{job.id}
                    <span style={{ marginLeft: '10px', fontWeight: 'normal', color: '#666' }}>
                      ({job.source})
                    </span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={{ ...styles.statusBadge, ...getStatusStyle(job.status) }}>
                      {job.status}
                    </span>
                    {job.status === 'running' && (
                      <button
                        style={styles.cancelButton}
                        onClick={() => handleCancelJob(job.id)}
                      >
                        Cancel
                      </button>
                    )}
                  </div>
                </div>

                {job.status === 'running' && (
                  <div style={styles.progressSection}>
                    <div style={styles.progressBar}>
                      <div
                        style={{ ...styles.progressFill, width: `${progress}%` }}
                      />
                    </div>
                    <div style={styles.progressText}>
                      {job.processed} / {job.total_records} processed ({progress}%)
                    </div>
                  </div>
                )}

                <div style={styles.statsRow}>
                  <div style={styles.statItem}>
                    Total: <span style={styles.statValue}>{job.total_records}</span>
                  </div>
                  <div style={styles.statItem}>
                    Enriched: <span style={{ ...styles.statValue, color: '#28a745' }}>{job.enriched}</span>
                  </div>
                  <div style={styles.statItem}>
                    Failed: <span style={{ ...styles.statValue, color: '#dc3545' }}>{job.failed}</span>
                  </div>
                </div>

                {job.status === 'running' && job.current_business && (
                  <div style={styles.currentBusiness}>
                    Currently processing: <strong>{job.current_business}</strong>
                  </div>
                )}

                {job.error_message && (
                  <div style={styles.errorMessage}>
                    Error: {job.error_message}
                  </div>
                )}

                <div style={styles.timestamp}>
                  Started: {formatDate(job.created_at)}
                  {job.completed_at && ` | Completed: ${formatDate(job.completed_at)}`}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

export default EnrichmentStatus
