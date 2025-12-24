import React, { useState, useRef } from 'react'

const API_BASE = 'http://localhost:8002/api'

const styles = {
  container: {
    padding: '20px',
  },
  dropZone: {
    border: '2px dashed #667eea',
    borderRadius: '10px',
    padding: '40px',
    textAlign: 'center',
    cursor: 'pointer',
    transition: 'all 0.2s',
    backgroundColor: '#fafafa',
  },
  dropZoneActive: {
    backgroundColor: '#f0f0ff',
    borderColor: '#764ba2',
  },
  dropZoneIcon: {
    fontSize: '48px',
    marginBottom: '15px',
  },
  dropZoneText: {
    fontSize: '16px',
    color: '#666',
    marginBottom: '10px',
  },
  dropZoneSubtext: {
    fontSize: '12px',
    color: '#999',
  },
  hiddenInput: {
    display: 'none',
  },
  previewSection: {
    marginTop: '20px',
  },
  previewHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '15px',
  },
  previewTitle: {
    fontSize: '18px',
    fontWeight: '600',
  },
  previewStats: {
    display: 'flex',
    gap: '20px',
    fontSize: '14px',
    color: '#666',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: '13px',
  },
  th: {
    padding: '10px',
    textAlign: 'left',
    borderBottom: '2px solid #eee',
    backgroundColor: '#f9f9f9',
    fontWeight: '600',
    position: 'sticky',
    top: 0,
  },
  td: {
    padding: '10px',
    borderBottom: '1px solid #eee',
    maxWidth: '200px',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  tableWrapper: {
    maxHeight: '400px',
    overflowY: 'auto',
    border: '1px solid #eee',
    borderRadius: '8px',
  },
  missingBadge: {
    backgroundColor: '#fff3cd',
    color: '#856404',
    padding: '2px 6px',
    borderRadius: '4px',
    fontSize: '11px',
  },
  presentBadge: {
    backgroundColor: '#d4edda',
    color: '#155724',
    padding: '2px 6px',
    borderRadius: '4px',
    fontSize: '11px',
  },
  actionsSection: {
    marginTop: '20px',
    padding: '20px',
    backgroundColor: '#f9f9f9',
    borderRadius: '8px',
  },
  checkboxLabel: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    marginBottom: '15px',
    cursor: 'pointer',
  },
  checkbox: {
    width: '18px',
    height: '18px',
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
  secondaryButton: {
    padding: '12px 24px',
    backgroundColor: 'white',
    color: '#333',
    border: '1px solid #ddd',
    borderRadius: '8px',
    cursor: 'pointer',
    fontSize: '14px',
  },
  disabledButton: {
    opacity: 0.6,
    cursor: 'not-allowed',
  },
  resultMessage: {
    marginTop: '20px',
    padding: '15px',
    borderRadius: '8px',
  },
  successMessage: {
    backgroundColor: '#d4edda',
    color: '#155724',
  },
  errorMessage: {
    backgroundColor: '#f8d7da',
    color: '#721c24',
  },
  fieldSelect: {
    padding: '8px',
    borderRadius: '4px',
    border: '1px solid #ddd',
    fontSize: '13px',
    minWidth: '120px',
  },
  mappingSection: {
    marginTop: '20px',
    padding: '15px',
    backgroundColor: '#f0f0f0',
    borderRadius: '8px',
  },
  mappingTitle: {
    fontSize: '14px',
    fontWeight: '600',
    marginBottom: '10px',
  },
  mappingGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
    gap: '10px',
  },
  mappingItem: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  mappingLabel: {
    fontSize: '12px',
    color: '#666',
  },
}

const EXPECTED_FIELDS = [
  { key: 'name', label: 'Business Name', required: true },
  { key: 'owner_name', label: 'Owner Name', required: false },
  { key: 'category', label: 'Category', required: false },
  { key: 'address', label: 'Address', required: false },
  { key: 'city', label: 'City', required: false },
  { key: 'state', label: 'State', required: false },
  { key: 'zip_code', label: 'Zip Code', required: false },
  { key: 'phone', label: 'Phone', required: false },
  { key: 'email', label: 'Email', required: false },
  { key: 'website', label: 'Website', required: false },
]

function CSVUpload({ onImportComplete }) {
  const [isDragging, setIsDragging] = useState(false)
  const [csvData, setCsvData] = useState(null)
  const [headers, setHeaders] = useState([])
  const [fieldMapping, setFieldMapping] = useState({})
  const [enrichAfterImport, setEnrichAfterImport] = useState(true)
  const [isImporting, setIsImporting] = useState(false)
  const [result, setResult] = useState(null)
  const fileInputRef = useRef(null)

  const parseCSV = (text) => {
    const lines = text.split('\n').filter(line => line.trim())
    if (lines.length === 0) return { headers: [], data: [] }

    // Parse headers
    const headerLine = lines[0]
    const parsedHeaders = parseCSVLine(headerLine)

    // Parse data rows
    const data = []
    for (let i = 1; i < lines.length; i++) {
      const values = parseCSVLine(lines[i])
      if (values.length > 0) {
        const row = {}
        parsedHeaders.forEach((header, idx) => {
          row[header] = values[idx] || ''
        })
        data.push(row)
      }
    }

    return { headers: parsedHeaders, data }
  }

  const parseCSVLine = (line) => {
    const result = []
    let current = ''
    let inQuotes = false

    for (let i = 0; i < line.length; i++) {
      const char = line[i]
      if (char === '"') {
        inQuotes = !inQuotes
      } else if (char === ',' && !inQuotes) {
        result.push(current.trim())
        current = ''
      } else {
        current += char
      }
    }
    result.push(current.trim())
    return result
  }

  const autoMapFields = (csvHeaders) => {
    const mapping = {}
    const lowerHeaders = csvHeaders.map(h => h.toLowerCase().replace(/[^a-z0-9]/g, ''))

    EXPECTED_FIELDS.forEach(field => {
      const fieldLower = field.key.replace('_', '')
      const labelLower = field.label.toLowerCase().replace(/[^a-z0-9]/g, '')

      // Try to find a matching header
      const matchIndex = lowerHeaders.findIndex(h =>
        h === fieldLower ||
        h === labelLower ||
        h.includes(fieldLower) ||
        fieldLower.includes(h) ||
        (field.key === 'name' && (h.includes('business') || h.includes('company'))) ||
        (field.key === 'owner_name' && (h.includes('owner') || h.includes('contact'))) ||
        (field.key === 'zip_code' && h.includes('zip'))
      )

      if (matchIndex !== -1) {
        mapping[field.key] = csvHeaders[matchIndex]
      }
    })

    return mapping
  }

  const handleFile = (file) => {
    if (!file || !file.name.endsWith('.csv')) {
      setResult({ success: false, message: 'Please upload a CSV file' })
      return
    }

    const reader = new FileReader()
    reader.onload = (e) => {
      const { headers: csvHeaders, data } = parseCSV(e.target.result)
      setHeaders(csvHeaders)
      setCsvData(data)
      setFieldMapping(autoMapFields(csvHeaders))
      setResult(null)
    }
    reader.readAsText(file)
  }

  const handleDragOver = (e) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = () => {
    setIsDragging(false)
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setIsDragging(false)
    const file = e.dataTransfer.files[0]
    handleFile(file)
  }

  const handleFileSelect = (e) => {
    const file = e.target.files[0]
    handleFile(file)
  }

  const handleMappingChange = (fieldKey, csvHeader) => {
    setFieldMapping(prev => ({
      ...prev,
      [fieldKey]: csvHeader || undefined
    }))
  }

  const getMappedData = () => {
    if (!csvData) return []

    return csvData.map(row => {
      const mappedRow = {}
      Object.entries(fieldMapping).forEach(([fieldKey, csvHeader]) => {
        if (csvHeader && row[csvHeader]) {
          mappedRow[fieldKey] = row[csvHeader]
        }
      })
      return mappedRow
    }).filter(row => row.name) // Must have a name
  }

  const handleImport = async () => {
    const contractors = getMappedData()
    if (contractors.length === 0) {
      setResult({ success: false, message: 'No valid contractors to import. Make sure Business Name is mapped.' })
      return
    }

    setIsImporting(true)
    setResult(null)

    try {
      const res = await fetch(`${API_BASE}/import-csv`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          contractors,
          enrich_after: enrichAfterImport,
          thread_count: 3
        })
      })

      const data = await res.json()

      if (res.ok) {
        setResult({
          success: true,
          message: `Successfully imported ${data.imported} contractors (${data.merged} merged with existing). ${data.enrichment_job_id ? 'Enrichment job started.' : ''}`
        })
        if (onImportComplete) {
          onImportComplete(data)
        }
      } else {
        setResult({ success: false, message: data.detail || 'Import failed' })
      }
    } catch (err) {
      setResult({ success: false, message: 'Failed to connect to server' })
    } finally {
      setIsImporting(false)
    }
  }

  const handleClear = () => {
    setCsvData(null)
    setHeaders([])
    setFieldMapping({})
    setResult(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const getMissingFields = () => {
    const mapped = getMappedData()
    if (mapped.length === 0) return { withOwner: 0, withEmail: 0, withPhone: 0, total: 0 }

    return {
      total: mapped.length,
      withOwner: mapped.filter(r => r.owner_name).length,
      withEmail: mapped.filter(r => r.email).length,
      withPhone: mapped.filter(r => r.phone).length,
    }
  }

  const stats = csvData ? getMissingFields() : null

  return (
    <div style={styles.container}>
      <div
        style={{
          ...styles.dropZone,
          ...(isDragging ? styles.dropZoneActive : {})
        }}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <div style={styles.dropZoneIcon}>📁</div>
        <div style={styles.dropZoneText}>
          Drag & drop a CSV file here, or click to browse
        </div>
        <div style={styles.dropZoneSubtext}>
          Supports CSV files with contractor data (name, phone, email, etc.)
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv"
          style={styles.hiddenInput}
          onChange={handleFileSelect}
        />
      </div>

      {csvData && csvData.length > 0 && (
        <>
          <div style={styles.mappingSection}>
            <div style={styles.mappingTitle}>Field Mapping</div>
            <div style={styles.mappingGrid}>
              {EXPECTED_FIELDS.map(field => (
                <div key={field.key} style={styles.mappingItem}>
                  <label style={styles.mappingLabel}>
                    {field.label} {field.required && '*'}
                  </label>
                  <select
                    style={styles.fieldSelect}
                    value={fieldMapping[field.key] || ''}
                    onChange={(e) => handleMappingChange(field.key, e.target.value)}
                  >
                    <option value="">-- Not Mapped --</option>
                    {headers.map(h => (
                      <option key={h} value={h}>{h}</option>
                    ))}
                  </select>
                </div>
              ))}
            </div>
          </div>

          <div style={styles.previewSection}>
            <div style={styles.previewHeader}>
              <div style={styles.previewTitle}>Preview ({csvData.length} rows)</div>
              {stats && (
                <div style={styles.previewStats}>
                  <span>Valid: {stats.total}</span>
                  <span>With Owner: {stats.withOwner}</span>
                  <span>With Email: {stats.withEmail}</span>
                  <span>With Phone: {stats.withPhone}</span>
                </div>
              )}
            </div>

            <div style={styles.tableWrapper}>
              <table style={styles.table}>
                <thead>
                  <tr>
                    <th style={styles.th}>Business Name</th>
                    <th style={styles.th}>Owner</th>
                    <th style={styles.th}>Phone</th>
                    <th style={styles.th}>Email</th>
                    <th style={styles.th}>City</th>
                    <th style={styles.th}>State</th>
                  </tr>
                </thead>
                <tbody>
                  {getMappedData().slice(0, 50).map((row, idx) => (
                    <tr key={idx}>
                      <td style={styles.td}>{row.name || '-'}</td>
                      <td style={styles.td}>
                        {row.owner_name ? (
                          row.owner_name
                        ) : (
                          <span style={styles.missingBadge}>Missing</span>
                        )}
                      </td>
                      <td style={styles.td}>{row.phone || '-'}</td>
                      <td style={styles.td}>
                        {row.email ? (
                          row.email
                        ) : (
                          <span style={styles.missingBadge}>Missing</span>
                        )}
                      </td>
                      <td style={styles.td}>{row.city || '-'}</td>
                      <td style={styles.td}>{row.state || '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div style={styles.actionsSection}>
            <label style={styles.checkboxLabel}>
              <input
                type="checkbox"
                style={styles.checkbox}
                checked={enrichAfterImport}
                onChange={(e) => setEnrichAfterImport(e.target.checked)}
              />
              <span>Enrich after import (find missing owner names & emails using AI)</span>
            </label>

            <div style={styles.buttonRow}>
              <button
                style={{
                  ...styles.primaryButton,
                  ...(isImporting ? styles.disabledButton : {})
                }}
                onClick={handleImport}
                disabled={isImporting}
              >
                {isImporting ? 'Importing...' : `Import ${stats?.total || 0} Contractors`}
              </button>
              <button
                style={styles.secondaryButton}
                onClick={handleClear}
              >
                Clear
              </button>
            </div>
          </div>
        </>
      )}

      {result && (
        <div style={{
          ...styles.resultMessage,
          ...(result.success ? styles.successMessage : styles.errorMessage)
        }}>
          {result.message}
        </div>
      )}
    </div>
  )
}

export default CSVUpload
