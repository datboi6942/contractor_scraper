import React, { useState } from 'react'

const styles = {
  form: {
    maxWidth: '700px',
  },
  field: {
    marginBottom: '20px',
  },
  label: {
    display: 'block',
    fontSize: '14px',
    fontWeight: '500',
    marginBottom: '8px',
    color: '#333',
  },
  select: {
    width: '100%',
    padding: '10px 12px',
    fontSize: '14px',
    border: '1px solid #ddd',
    borderRadius: '6px',
    backgroundColor: 'white',
  },
  input: {
    width: '100%',
    padding: '10px 12px',
    fontSize: '14px',
    border: '1px solid #ddd',
    borderRadius: '6px',
  },
  categoriesGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
    gap: '10px',
    marginTop: '10px',
  },
  categoryItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '8px 12px',
    backgroundColor: '#f8f9fa',
    borderRadius: '6px',
    cursor: 'pointer',
  },
  checkbox: {
    width: '18px',
    height: '18px',
    cursor: 'pointer',
  },
  categoryLabel: {
    fontSize: '13px',
    textTransform: 'capitalize',
    cursor: 'pointer',
  },
  buttons: {
    display: 'flex',
    gap: '10px',
    marginTop: '30px',
  },
  button: {
    padding: '12px 24px',
    fontSize: '14px',
    fontWeight: '500',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    transition: 'all 0.2s',
  },
  primaryButton: {
    backgroundColor: '#667eea',
    color: 'white',
  },
  secondaryButton: {
    backgroundColor: '#e9ecef',
    color: '#333',
  },
  hint: {
    fontSize: '12px',
    color: '#666',
    marginTop: '5px',
  },
  row: {
    display: 'flex',
    gap: '20px',
  },
  halfField: {
    flex: 1,
  },
  threadButtons: {
    display: 'flex',
    gap: '8px',
    marginTop: '8px',
  },
  threadButton: {
    padding: '10px 20px',
    fontSize: '14px',
    border: '2px solid #ddd',
    borderRadius: '6px',
    cursor: 'pointer',
    backgroundColor: 'white',
    transition: 'all 0.2s',
  },
  threadButtonActive: {
    borderColor: '#667eea',
    backgroundColor: '#e8f0ff',
    color: '#667eea',
    fontWeight: '600',
  },
}

function JobConfig({ locations, categories, onStartJob }) {
  const [location, setLocation] = useState('')
  const [customLocation, setCustomLocation] = useState('')
  const [selectedCategories, setSelectedCategories] = useState([])
  const [threadCount, setThreadCount] = useState(3)

  const handleCategoryToggle = (categoryValue) => {
    setSelectedCategories((prev) =>
      prev.includes(categoryValue)
        ? prev.filter((c) => c !== categoryValue)
        : [...prev, categoryValue]
    )
  }

  const handleSelectAll = () => {
    if (selectedCategories.length === categories.length) {
      setSelectedCategories([])
    } else {
      setSelectedCategories(categories.map((c) => c.value))
    }
  }

  const handleSubmit = () => {
    const finalLocation = location === 'custom' ? customLocation : location
    if (!finalLocation || selectedCategories.length === 0) {
      alert('Please select a location and at least one category')
      return
    }
    onStartJob(finalLocation, selectedCategories, threadCount)
  }

  const threadOptions = [1, 2, 3, 5, 8, 10]

  return (
    <div style={styles.form}>
      <div style={styles.row}>
        <div style={{ ...styles.field, ...styles.halfField }}>
          <label style={styles.label}>Location</label>
          <select
            style={styles.select}
            value={location}
            onChange={(e) => setLocation(e.target.value)}
          >
            <option value="">Select a location...</option>
            {locations.map((loc) => (
              <option key={loc.id} value={`${loc.city}, ${loc.state}`}>
                {loc.name}
              </option>
            ))}
            <option value="custom">Custom location...</option>
          </select>
          {location === 'custom' && (
            <input
              style={{ ...styles.input, marginTop: '10px' }}
              type="text"
              placeholder="Enter city, state (e.g., 'Martinsburg, WV')"
              value={customLocation}
              onChange={(e) => setCustomLocation(e.target.value)}
            />
          )}
        </div>

        <div style={{ ...styles.field, ...styles.halfField }}>
          <label style={styles.label}>Parallel Threads</label>
          <div style={styles.threadButtons}>
            {threadOptions.map((num) => (
              <button
                key={num}
                style={{
                  ...styles.threadButton,
                  ...(threadCount === num ? styles.threadButtonActive : {}),
                }}
                onClick={() => setThreadCount(num)}
              >
                {num}
              </button>
            ))}
          </div>
          <div style={styles.hint}>
            More threads = faster but uses more resources. Recommended: 3-5
          </div>
        </div>
      </div>

      <div style={styles.field}>
        <label style={styles.label}>
          Contractor Categories
          <button
            style={{
              ...styles.button,
              ...styles.secondaryButton,
              padding: '4px 10px',
              fontSize: '12px',
              marginLeft: '10px',
            }}
            onClick={handleSelectAll}
          >
            {selectedCategories.length === categories.length
              ? 'Deselect All'
              : 'Select All'}
          </button>
        </label>
        <div style={styles.categoriesGrid}>
          {categories.map((cat) => (
            <label
              key={cat.value}
              style={{
                ...styles.categoryItem,
                backgroundColor: selectedCategories.includes(cat.value)
                  ? '#e8f0ff'
                  : '#f8f9fa',
                border: selectedCategories.includes(cat.value)
                  ? '1px solid #667eea'
                  : '1px solid transparent',
              }}
            >
              <input
                type="checkbox"
                style={styles.checkbox}
                checked={selectedCategories.includes(cat.value)}
                onChange={() => handleCategoryToggle(cat.value)}
              />
              <span style={styles.categoryLabel}>
                {cat.label.replace(/_/g, ' ')}
              </span>
            </label>
          ))}
        </div>
        <div style={styles.hint}>
          Selected: {selectedCategories.length} of {categories.length} categories
        </div>
      </div>

      <div style={styles.buttons}>
        <button
          style={{ ...styles.button, ...styles.primaryButton }}
          onClick={handleSubmit}
          disabled={!location && !customLocation}
        >
          Start Scraping Job ({threadCount} threads)
        </button>
      </div>

      <div
        style={{
          marginTop: '20px',
          padding: '15px',
          backgroundColor: '#d4edda',
          borderRadius: '6px',
          fontSize: '13px',
          color: '#155724',
        }}
      >
        <strong>Parallel Processing:</strong> With {threadCount} threads, the scraper will
        process {threadCount} sources simultaneously. Total tasks: ~{selectedCategories.length * 6} searches
        ({selectedCategories.length} categories x 3 sources x ~2 terms each).
      </div>
    </div>
  )
}

export default JobConfig
