import React, { useState, useEffect } from 'react'

const API_BASE = 'http://localhost:8002/api'

const styles = {
  controls: {
    display: 'flex',
    gap: '15px',
    marginBottom: '20px',
    flexWrap: 'wrap',
    alignItems: 'center',
  },
  input: {
    padding: '10px 12px',
    fontSize: '14px',
    border: '1px solid #ddd',
    borderRadius: '6px',
    minWidth: '200px',
  },
  select: {
    padding: '10px 12px',
    fontSize: '14px',
    border: '1px solid #ddd',
    borderRadius: '6px',
    backgroundColor: 'white',
  },
  button: {
    padding: '10px 20px',
    fontSize: '14px',
    fontWeight: '500',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    backgroundColor: '#28a745',
    color: 'white',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: '13px',
  },
  th: {
    backgroundColor: '#f8f9fa',
    padding: '12px 10px',
    textAlign: 'left',
    fontWeight: '600',
    borderBottom: '2px solid #ddd',
    whiteSpace: 'nowrap',
  },
  td: {
    padding: '10px',
    borderBottom: '1px solid #eee',
    maxWidth: '200px',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  pagination: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: '20px',
    padding: '15px 0',
    borderTop: '1px solid #eee',
  },
  pageButton: {
    padding: '8px 16px',
    fontSize: '13px',
    border: '1px solid #ddd',
    borderRadius: '4px',
    backgroundColor: 'white',
    cursor: 'pointer',
  },
  emptyState: {
    textAlign: 'center',
    padding: '40px',
    color: '#666',
  },
  link: {
    color: '#667eea',
    textDecoration: 'none',
  },
  enrichedBadge: {
    display: 'inline-block',
    padding: '2px 6px',
    fontSize: '10px',
    fontWeight: '600',
    borderRadius: '10px',
    backgroundColor: '#e3f2fd',
    color: '#1565c0',
    marginLeft: '5px',
  },
  confidenceBadge: {
    display: 'inline-block',
    padding: '2px 6px',
    fontSize: '10px',
    borderRadius: '4px',
    marginLeft: '4px',
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
    marginLeft: '5px',
  },
  enrichedCell: {
    backgroundColor: '#e8f5e9',
    borderLeft: '3px solid #4caf50',
  },
}

function DataTable({ categories }) {
  const [contractors, setContractors] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [perPage] = useState(25)
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('')
  const [loading, setLoading] = useState(false)
  const [cleanupMessage, setCleanupMessage] = useState('')
  const [locations, setLocations] = useState({ states: [], cities: [] })
  const [exportState, setExportState] = useState('')
  const [exportCity, setExportCity] = useState('')
  const [showExportModal, setShowExportModal] = useState(false)
  const [showCleanupModal, setShowCleanupModal] = useState(false)
  const [keepStates, setKeepStates] = useState([])

  const fetchContractors = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        per_page: perPage.toString(),
      })
      if (search) params.append('search', search)
      if (category) params.append('category', category)

      const res = await fetch(`${API_BASE}/contractors?${params}`)
      const data = await res.json()
      setContractors(data.items)
      setTotal(data.total)
    } catch (err) {
      console.error('Failed to fetch contractors:', err)
    }
    setLoading(false)
  }

  const fetchLocations = async () => {
    try {
      const res = await fetch(`${API_BASE}/locations`)
      const data = await res.json()
      setLocations(data)
    } catch (err) {
      console.error('Failed to fetch locations:', err)
    }
  }

  useEffect(() => {
    fetchContractors()
    fetchLocations()
  }, [page, category])

  const handleSearch = () => {
    setPage(1)
    fetchContractors()
  }

  const handleExport = () => {
    const params = new URLSearchParams()
    if (category) params.append('category', category)
    if (exportState) params.append('state', exportState)
    if (exportCity) params.append('city', exportCity)
    window.open(`${API_BASE}/export?${params}`, '_blank')
    setShowExportModal(false)
  }

  const handleCleanupByState = async () => {
    if (keepStates.length === 0) {
      alert('Please select at least one state to keep')
      return
    }
    try {
      const res = await fetch(`${API_BASE}/cleanup-location?${keepStates.map(s => `keep_states=${s}`).join('&')}`, {
        method: 'POST'
      })
      const data = await res.json()
      setCleanupMessage(data.message)
      setShowCleanupModal(false)
      setKeepStates([])
      fetchContractors()
      fetchLocations()
      setTimeout(() => setCleanupMessage(''), 5000)
    } catch (err) {
      setCleanupMessage('Failed to cleanup')
      console.error('Failed to cleanup:', err)
    }
  }

  const toggleKeepState = (state) => {
    setKeepStates(prev =>
      prev.includes(state) ? prev.filter(s => s !== state) : [...prev, state]
    )
  }

  const filteredCities = exportState
    ? locations.cities.filter(c => c.state?.toUpperCase() === exportState.toUpperCase())
    : locations.cities

  const handleCleanupDuplicates = async () => {
    setCleanupMessage('Cleaning up duplicates...')
    try {
      const res = await fetch(`${API_BASE}/cleanup-duplicates`, { method: 'POST' })
      const data = await res.json()
      setCleanupMessage(data.message)
      // Refresh data after cleanup
      fetchContractors()
      // Clear message after 5 seconds
      setTimeout(() => setCleanupMessage(''), 5000)
    } catch (err) {
      setCleanupMessage('Failed to cleanup duplicates')
      console.error('Failed to cleanup duplicates:', err)
    }
  }

  const totalPages = Math.ceil(total / perPage)

  return (
    <div>
      <div style={styles.controls}>
        <input
          style={styles.input}
          type="text"
          placeholder="Search by name, address, phone..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
        />
        <select
          style={styles.select}
          value={category}
          onChange={(e) => {
            setCategory(e.target.value)
            setPage(1)
          }}
        >
          <option value="">All Categories</option>
          {categories.map((cat) => (
            <option key={cat.value} value={cat.value}>
              {cat.label}
            </option>
          ))}
        </select>
        <button
          style={{ ...styles.pageButton, backgroundColor: '#667eea', color: 'white', border: 'none' }}
          onClick={handleSearch}
        >
          Search
        </button>
        <button style={styles.button} onClick={() => setShowExportModal(true)}>
          Export CSV
        </button>
        <button
          style={{ ...styles.button, backgroundColor: '#dc3545' }}
          onClick={handleCleanupDuplicates}
        >
          Remove Duplicates
        </button>
        <button
          style={{ ...styles.button, backgroundColor: '#ff9800' }}
          onClick={() => setShowCleanupModal(true)}
        >
          Filter by State
        </button>
        {cleanupMessage && (
          <span style={{ color: '#28a745', fontWeight: '500', fontSize: '14px' }}>
            {cleanupMessage}
          </span>
        )}
      </div>

      {/* Export Modal */}
      {showExportModal && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex',
          alignItems: 'center', justifyContent: 'center', zIndex: 1000
        }}>
          <div style={{
            backgroundColor: 'white', padding: '30px', borderRadius: '10px',
            minWidth: '400px', maxWidth: '500px'
          }}>
            <h3 style={{ marginTop: 0, marginBottom: '20px' }}>Export Contractors</h3>

            <div style={{ marginBottom: '15px' }}>
              <label style={styles.label}>Filter by State</label>
              <select
                style={styles.select}
                value={exportState}
                onChange={(e) => { setExportState(e.target.value); setExportCity(''); }}
              >
                <option value="">All States</option>
                {locations.states.map(s => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>

            <div style={{ marginBottom: '15px' }}>
              <label style={styles.label}>Filter by City</label>
              <select
                style={styles.select}
                value={exportCity}
                onChange={(e) => setExportCity(e.target.value)}
              >
                <option value="">All Cities</option>
                {filteredCities.map((c, i) => (
                  <option key={i} value={c.city}>{c.city}, {c.state}</option>
                ))}
              </select>
            </div>

            <div style={{ marginBottom: '15px' }}>
              <label style={styles.label}>Filter by Category</label>
              <select
                style={styles.select}
                value={category}
                onChange={(e) => setCategory(e.target.value)}
              >
                <option value="">All Categories</option>
                {categories.map((cat) => (
                  <option key={cat.value} value={cat.value}>{cat.label}</option>
                ))}
              </select>
            </div>

            <div style={{ display: 'flex', gap: '10px', marginTop: '20px' }}>
              <button style={{ ...styles.button }} onClick={handleExport}>
                Download CSV
              </button>
              <button
                style={{ ...styles.button, backgroundColor: '#6c757d' }}
                onClick={() => setShowExportModal(false)}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Cleanup by State Modal */}
      {showCleanupModal && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex',
          alignItems: 'center', justifyContent: 'center', zIndex: 1000
        }}>
          <div style={{
            backgroundColor: 'white', padding: '30px', borderRadius: '10px',
            minWidth: '400px', maxWidth: '500px'
          }}>
            <h3 style={{ marginTop: 0, marginBottom: '10px', color: '#dc3545' }}>
              Remove Out-of-Area Data
            </h3>
            <p style={{ fontSize: '14px', color: '#666', marginBottom: '20px' }}>
              Select the states you want to KEEP. All other states will be deleted.
            </p>

            <div style={{
              display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px',
              marginBottom: '20px', maxHeight: '200px', overflowY: 'auto'
            }}>
              {locations.states.map(state => (
                <label key={state} style={{
                  display: 'flex', alignItems: 'center', gap: '5px',
                  padding: '8px', backgroundColor: keepStates.includes(state) ? '#e8f5e9' : '#f5f5f5',
                  borderRadius: '4px', cursor: 'pointer',
                  border: keepStates.includes(state) ? '2px solid #4caf50' : '1px solid #ddd'
                }}>
                  <input
                    type="checkbox"
                    checked={keepStates.includes(state)}
                    onChange={() => toggleKeepState(state)}
                  />
                  <span style={{ fontWeight: keepStates.includes(state) ? 'bold' : 'normal' }}>
                    {state}
                  </span>
                </label>
              ))}
            </div>

            <div style={{
              padding: '10px', backgroundColor: '#fff3e0', borderRadius: '6px',
              marginBottom: '20px', fontSize: '13px', color: '#e65100'
            }}>
              <strong>Warning:</strong> This will permanently delete all contractors
              from states NOT selected above.
              {keepStates.length > 0 && (
                <div style={{ marginTop: '5px' }}>
                  Keeping: <strong>{keepStates.join(', ')}</strong>
                </div>
              )}
            </div>

            <div style={{ display: 'flex', gap: '10px' }}>
              <button
                style={{ ...styles.button, backgroundColor: '#dc3545' }}
                onClick={handleCleanupByState}
                disabled={keepStates.length === 0}
              >
                Delete Other States
              </button>
              <button
                style={{ ...styles.button, backgroundColor: '#6c757d' }}
                onClick={() => { setShowCleanupModal(false); setKeepStates([]); }}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {loading ? (
        <div style={styles.emptyState}>Loading...</div>
      ) : contractors.length === 0 ? (
        <div style={styles.emptyState}>
          No contractors found. Start a scraping job to collect data.
        </div>
      ) : (
        <>
          <div style={{ overflowX: 'auto' }}>
            <table style={styles.table}>
              <thead>
                <tr>
                  <th style={styles.th}>Business</th>
                  <th style={{ ...styles.th, backgroundColor: '#e8f5e9' }}>Owner/Contact</th>
                  <th style={styles.th}>Category</th>
                  <th style={styles.th}>Phone</th>
                  <th style={styles.th}>Email</th>
                  <th style={styles.th}>Address</th>
                  <th style={styles.th}>Links</th>
                </tr>
              </thead>
              <tbody>
                {contractors.map((c) => {
                  const isEnriched = c.enriched;
                  const confidence = c.enrichment_confidence || 0;
                  const confidenceColor = confidence > 0.7 ? '#4caf50' : confidence > 0.4 ? '#ff9800' : '#f44336';

                  return (
                    <tr key={c.id} style={isEnriched ? { backgroundColor: '#fafffe' } : {}}>
                      <td style={styles.td} title={c.name}>
                        {c.name}
                        {isEnriched && (
                          <span style={styles.enrichedBadge} title={`AI Enriched (${Math.round(confidence * 100)}% confidence)`}>
                            AI
                          </span>
                        )}
                      </td>
                      <td style={{
                        ...styles.td,
                        ...(isEnriched && c.owner_name ? styles.enrichedCell : {}),
                        backgroundColor: c.owner_name ? '#e8f5e9' : '#fff3e0',
                        fontWeight: c.owner_name ? '600' : 'normal',
                        color: c.owner_name ? '#2e7d32' : '#e65100',
                      }}>
                        {c.owner_name || '—'}
                        {isEnriched && confidence > 0 && (
                          <span
                            style={{
                              ...styles.confidenceBadge,
                              backgroundColor: confidenceColor + '20',
                              color: confidenceColor,
                            }}
                            title={`${Math.round(confidence * 100)}% confidence`}
                          >
                            {Math.round(confidence * 100)}%
                          </span>
                        )}
                      </td>
                      <td style={styles.td}>
                        {c.category.replace(/_/g, ' ')}
                      </td>
                      <td style={styles.td}>
                        {c.phone && (
                          <a href={`tel:${c.phone}`} style={styles.link}>
                            {c.phone}
                          </a>
                        )}
                      </td>
                      <td style={{
                        ...styles.td,
                        ...(isEnriched && c.email ? styles.enrichedCell : {}),
                      }}>
                        {c.email && (
                          <a href={`mailto:${c.email}`} style={styles.link}>
                            {c.email}
                          </a>
                        )}
                      </td>
                      <td style={styles.td} title={`${c.address || ''} ${c.city || ''} ${c.state || ''} ${c.zip_code || ''}`}>
                        {[c.city, c.state].filter(Boolean).join(', ')}
                      </td>
                      <td style={styles.td}>
                        {c.website && (
                          <a
                            href={c.website}
                            target="_blank"
                            rel="noopener noreferrer"
                            style={styles.link}
                          >
                            Web
                          </a>
                        )}
                        {c.linkedin_url && (
                          <a
                            href={c.linkedin_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            style={styles.linkedinIcon}
                            title="View LinkedIn Profile"
                          >
                            in
                          </a>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div style={styles.pagination}>
            <span>
              Showing {(page - 1) * perPage + 1} -{' '}
              {Math.min(page * perPage, total)} of {total} contractors
            </span>
            <div style={{ display: 'flex', gap: '10px' }}>
              <button
                style={styles.pageButton}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
              >
                Previous
              </button>
              <span style={{ padding: '8px 16px' }}>
                Page {page} of {totalPages}
              </span>
              <button
                style={styles.pageButton}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
              >
                Next
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

export default DataTable
