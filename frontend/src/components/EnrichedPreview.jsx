import React, { useState, useEffect } from 'react'

const API_BASE = 'http://localhost:8002/api'

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
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: '13px',
    backgroundColor: 'white',
    borderRadius: '8px',
    overflow: 'hidden',
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
  },
  th: {
    backgroundColor: '#f8f9fa',
    padding: '12px 10px',
    textAlign: 'left',
    fontWeight: '600',
    borderBottom: '2px solid #eee',
    color: '#333',
  },
  td: {
    padding: '12px 10px',
    borderBottom: '1px solid #f0f0f0',
  },
  highlight: {
    backgroundColor: '#e8f5e9',
    color: '#2e7d32',
    fontWeight: '600',
    padding: '2px 4px',
    borderRadius: '4px',
  },
  badge: {
    display: 'inline-block',
    padding: '2px 8px',
    fontSize: '11px',
    fontWeight: '600',
    borderRadius: '12px',
    marginLeft: '5px',
  },
  confidenceHigh: {
    backgroundColor: '#d4edda',
    color: '#155724',
  },
  confidenceMedium: {
    backgroundColor: '#fff3cd',
    color: '#856404',
  },
  confidenceLow: {
    backgroundColor: '#f8d7da',
    color: '#721c24',
  },
  link: {
    color: '#667eea',
    textDecoration: 'none',
    marginRight: '8px',
  },
  sourceLink: {
    display: 'block',
    fontSize: '11px',
    color: '#999',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    maxWidth: '150px',
  },
  linkedinIcon: {
    display: 'inline-block',
    padding: '2px 6px',
    fontSize: '10px',
    fontWeight: '600',
    borderRadius: '4px',
    backgroundColor: '#0077b5',
    color: 'white',
    textDecoration: 'none',
  },
  emptyState: {
    textAlign: 'center',
    padding: '40px',
    color: '#666',
    backgroundColor: '#f9f9f9',
    borderRadius: '8px',
  }
}

function EnrichedPreview() {
  const [contractors, setContractors] = useState([])
  const [loading, setLoading] = useState(true)

  const fetchSample = async () => {
    try {
      const res = await fetch(`${API_BASE}/enrichment/sample?limit=15`)
      const data = await res.json()
      setContractors(data)
    } catch (err) {
      console.error('Failed to fetch enrichment sample:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchSample()
    const interval = setInterval(fetchSample, 10000)
    return () => clearInterval(interval)
  }, [])

  const getConfidenceStyle = (score) => {
    if (score >= 0.8) return styles.confidenceHigh
    if (score >= 0.5) return styles.confidenceMedium
    return styles.confidenceLow
  }

  const renderSourceUrls = (sourceUrlsJson) => {
    if (!sourceUrlsJson) return null
    try {
      const urls = JSON.parse(sourceUrlsJson)
      return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
          {urls.map((url, i) => (
            <a key={i} href={url} target="_blank" rel="noopener noreferrer" style={styles.sourceLink}>
              {url.replace(/^https?:\/\/(www\.)?/, '').split('/')[0]}
            </a>
          ))}
        </div>
      )
    } catch (e) {
      return null
    }
  }

  if (loading && contractors.length === 0) {
    return <div style={styles.emptyState}>Loading preview...</div>
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div style={styles.title}>Recently Enriched Leads</div>
        <button 
          onClick={fetchSample} 
          style={{ 
            padding: '8px 16px', 
            backgroundColor: 'white', 
            border: '1px solid #ddd', 
            borderRadius: '6px', 
            cursor: 'pointer',
            fontSize: '13px'
          }}
        >
          Refresh
        </button>
      </div>

      {contractors.length === 0 ? (
        <div style={styles.emptyState}>
          No enriched leads found yet. Start an enrichment job to see results here!
        </div>
      ) : (
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={styles.th}>Business Name</th>
              <th style={styles.th}>Enriched Owner</th>
              <th style={styles.th}>Enriched Email</th>
              <th style={styles.th}>LinkedIn</th>
              <th style={styles.th}>Confidence</th>
              <th style={styles.th}>Sources</th>
            </tr>
          </thead>
          <tbody>
            {contractors.map((c) => (
              <tr key={c.id}>
                <td style={styles.td}>
                  <strong>{c.name}</strong>
                  <div style={{ fontSize: '11px', color: '#999' }}>{c.city}, {c.state}</div>
                </td>
                <td style={styles.td}>
                  {c.owner_name ? (
                    <span style={styles.highlight}>{c.owner_name}</span>
                  ) : (
                    <span style={{ color: '#ccc' }}>Not found</span>
                  )}
                </td>
                <td style={styles.td}>
                  {c.email ? (
                    <a href={`mailto:${c.email}`} style={{ ...styles.link, ...styles.highlight }}>
                      {c.email}
                    </a>
                  ) : (
                    <span style={{ color: '#ccc' }}>Not found</span>
                  )}
                </td>
                <td style={styles.td}>
                  {c.linkedin_url ? (
                    <a 
                      href={c.linkedin_url} 
                      target="_blank" 
                      rel="noopener noreferrer" 
                      style={styles.linkedinIcon}
                    >
                      in
                    </a>
                  ) : (
                    <span style={{ color: '#ccc' }}>—</span>
                  )}
                </td>
                <td style={styles.td}>
                  <span style={{ 
                    ...styles.badge, 
                    ...getConfidenceStyle(c.enrichment_confidence || 0) 
                  }}>
                    {Math.round((c.enrichment_confidence || 0) * 100)}%
                  </span>
                </td>
                <td style={styles.td}>
                  {renderSourceUrls(c.enrichment_source_urls)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

export default EnrichedPreview

