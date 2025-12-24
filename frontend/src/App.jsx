import React, { useState, useEffect } from 'react'
import Dashboard from './components/Dashboard'
import JobConfig from './components/JobConfig'
import DataTable from './components/DataTable'
import JobStatus from './components/JobStatus'

const API_BASE = 'http://localhost:8002/api'

const styles = {
  container: {
    maxWidth: '1400px',
    margin: '0 auto',
    padding: '20px',
  },
  header: {
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    color: 'white',
    padding: '30px',
    borderRadius: '10px',
    marginBottom: '20px',
    boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
  },
  title: {
    fontSize: '28px',
    fontWeight: 'bold',
    marginBottom: '5px',
  },
  subtitle: {
    fontSize: '14px',
    opacity: 0.9,
  },
  tabs: {
    display: 'flex',
    gap: '10px',
    marginBottom: '20px',
  },
  tab: {
    padding: '12px 24px',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: '500',
    transition: 'all 0.2s',
  },
  activeTab: {
    backgroundColor: '#667eea',
    color: 'white',
  },
  inactiveTab: {
    backgroundColor: 'white',
    color: '#333',
    border: '1px solid #ddd',
  },
  content: {
    backgroundColor: 'white',
    borderRadius: '10px',
    padding: '20px',
    boxShadow: '0 2px 4px rgba(0, 0, 0, 0.05)',
  },
}

function App() {
  const [activeTab, setActiveTab] = useState('dashboard')
  const [stats, setStats] = useState(null)
  const [jobs, setJobs] = useState([])
  const [locations, setLocations] = useState([])
  const [categories, setCategories] = useState([])

  const fetchStats = async () => {
    try {
      const res = await fetch(`${API_BASE}/stats`)
      const data = await res.json()
      setStats(data)
    } catch (err) {
      console.error('Failed to fetch stats:', err)
    }
  }

  const fetchJobs = async () => {
    try {
      const res = await fetch(`${API_BASE}/jobs`)
      const data = await res.json()
      setJobs(data)
    } catch (err) {
      console.error('Failed to fetch jobs:', err)
    }
  }

  const fetchConfig = async () => {
    try {
      const [locRes, catRes] = await Promise.all([
        fetch(`${API_BASE}/config/locations`),
        fetch(`${API_BASE}/config/categories`),
      ])
      setLocations(await locRes.json())
      setCategories(await catRes.json())
    } catch (err) {
      console.error('Failed to fetch config:', err)
    }
  }

  useEffect(() => {
    fetchStats()
    fetchJobs()
    fetchConfig()

    const interval = setInterval(() => {
      fetchStats()
      fetchJobs()
    }, 5000)

    return () => clearInterval(interval)
  }, [])

  const handleStartJob = async (location, selectedCategories, threadCount = 3) => {
    try {
      const res = await fetch(`${API_BASE}/jobs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ location, categories: selectedCategories, thread_count: threadCount }),
      })
      if (res.ok) {
        fetchJobs()
        fetchStats()
        setActiveTab('jobs')
      }
    } catch (err) {
      console.error('Failed to start job:', err)
    }
  }

  const handleCancelJob = async (jobId) => {
    try {
      await fetch(`${API_BASE}/jobs/${jobId}`, { method: 'DELETE' })
      fetchJobs()
      fetchStats()
    } catch (err) {
      console.error('Failed to cancel job:', err)
    }
  }

  const renderContent = () => {
    switch (activeTab) {
      case 'dashboard':
        return <Dashboard stats={stats} jobs={jobs} />
      case 'new-job':
        return (
          <JobConfig
            locations={locations}
            categories={categories}
            onStartJob={handleStartJob}
          />
        )
      case 'jobs':
        return <JobStatus jobs={jobs} onCancel={handleCancelJob} />
      case 'data':
        return <DataTable categories={categories} />
      default:
        return <Dashboard stats={stats} jobs={jobs} />
    }
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div style={styles.title}>Contractor Data Scraper</div>
        <div style={styles.subtitle}>
          Gather contact information for local contractors
        </div>
      </div>

      <div style={styles.tabs}>
        {[
          { id: 'dashboard', label: 'Dashboard' },
          { id: 'new-job', label: 'New Scraping Job' },
          { id: 'jobs', label: 'Job Status' },
          { id: 'data', label: 'Collected Data' },
        ].map((tab) => (
          <button
            key={tab.id}
            style={{
              ...styles.tab,
              ...(activeTab === tab.id ? styles.activeTab : styles.inactiveTab),
            }}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div style={styles.content}>{renderContent()}</div>
    </div>
  )
}

export default App
