import React, { useState, useEffect } from 'react'
import CSVUpload from './CSVUpload'
import EnrichmentStatus from './EnrichmentStatus'

const API_BASE = 'http://localhost:8002/api'

const styles = {
  container: {
    padding: '10px',
  },
  tabs: {
    display: 'flex',
    gap: '0',
    marginBottom: '20px',
    borderBottom: '2px solid #e0e0e0',
  },
  tab: {
    padding: '12px 24px',
    border: 'none',
    background: 'none',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: '500',
    color: '#666',
    borderBottom: '2px solid transparent',
    marginBottom: '-2px',
    transition: 'all 0.2s',
  },
  activeTab: {
    color: '#667eea',
    borderBottomColor: '#667eea',
  },
  statsBar: {
    display: 'flex',
    gap: '20px',
    padding: '15px 20px',
    backgroundColor: '#f0f0ff',
    borderRadius: '8px',
    marginBottom: '20px',
  },
  statItem: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  statLabel: {
    fontSize: '12px',
    color: '#666',
  },
  statValue: {
    fontSize: '20px',
    fontWeight: '600',
    color: '#333',
  },
  statHighlight: {
    color: '#667eea',
  },
  description: {
    padding: '20px',
    backgroundColor: '#f9f9f9',
    borderRadius: '8px',
    marginBottom: '20px',
  },
  descTitle: {
    fontSize: '16px',
    fontWeight: '600',
    marginBottom: '10px',
    color: '#333',
  },
  descText: {
    fontSize: '14px',
    color: '#666',
    lineHeight: '1.6',
  },
  featureList: {
    marginTop: '10px',
    paddingLeft: '20px',
  },
  featureItem: {
    fontSize: '14px',
    color: '#666',
    marginBottom: '5px',
  },
}

function Enrich({ categories }) {
  const [activeSubTab, setActiveSubTab] = useState('enrich')
  const [enrichmentStats, setEnrichmentStats] = useState(null)

  const fetchEnrichmentStats = async () => {
    try {
      const res = await fetch(`${API_BASE}/enrichment/stats`)
      const data = await res.json()
      setEnrichmentStats(data)
    } catch (err) {
      console.error('Failed to fetch enrichment stats:', err)
    }
  }

  useEffect(() => {
    fetchEnrichmentStats()
    const interval = setInterval(fetchEnrichmentStats, 5000)
    return () => clearInterval(interval)
  }, [])

  const handleImportComplete = () => {
    fetchEnrichmentStats()
  }

  return (
    <div style={styles.container}>
      <div style={styles.description}>
        <div style={styles.descTitle}>Lead Enrichment Engine</div>
        <div style={styles.descText}>
          Use AI-powered search to automatically find missing owner names, email addresses,
          and LinkedIn profiles for your contractor database.
        </div>
        <ul style={styles.featureList}>
          <li style={styles.featureItem}>Searches multiple sources including business websites, LinkedIn, and public records</li>
          <li style={styles.featureItem}>Uses GPT-4 to extract and validate contact information</li>
          <li style={styles.featureItem}>Processes records in parallel for faster enrichment</li>
          <li style={styles.featureItem}>Import CSV files and enrich them automatically</li>
        </ul>
      </div>

      {enrichmentStats && (
        <div style={styles.statsBar}>
          <div style={styles.statItem}>
            <div style={styles.statLabel}>Needs Enrichment</div>
            <div style={{ ...styles.statValue, ...styles.statHighlight }}>
              {enrichmentStats.needs_enrichment}
            </div>
          </div>
          <div style={styles.statItem}>
            <div style={styles.statLabel}>Already Enriched</div>
            <div style={styles.statValue}>{enrichmentStats.total_enriched}</div>
          </div>
          <div style={styles.statItem}>
            <div style={styles.statLabel}>With LinkedIn</div>
            <div style={styles.statValue}>{enrichmentStats.with_linkedin}</div>
          </div>
          <div style={styles.statItem}>
            <div style={styles.statLabel}>Avg Confidence</div>
            <div style={styles.statValue}>
              {(enrichmentStats.avg_confidence * 100).toFixed(0)}%
            </div>
          </div>
          {enrichmentStats.active_enrichment_jobs > 0 && (
            <div style={styles.statItem}>
              <div style={styles.statLabel}>Active Jobs</div>
              <div style={{ ...styles.statValue, color: '#28a745' }}>
                {enrichmentStats.active_enrichment_jobs}
              </div>
            </div>
          )}
        </div>
      )}

      <div style={styles.tabs}>
        <button
          style={{
            ...styles.tab,
            ...(activeSubTab === 'enrich' ? styles.activeTab : {})
          }}
          onClick={() => setActiveSubTab('enrich')}
        >
          Enrich Database
        </button>
        <button
          style={{
            ...styles.tab,
            ...(activeSubTab === 'import' ? styles.activeTab : {})
          }}
          onClick={() => setActiveSubTab('import')}
        >
          Import CSV
        </button>
      </div>

      {activeSubTab === 'enrich' && (
        <EnrichmentStatus
          categories={categories}
          onRefresh={fetchEnrichmentStats}
        />
      )}

      {activeSubTab === 'import' && (
        <CSVUpload onImportComplete={handleImportComplete} />
      )}
    </div>
  )
}

export default Enrich
