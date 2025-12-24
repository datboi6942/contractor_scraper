import React from 'react'

const styles = {
  jobList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '15px',
  },
  jobCard: {
    border: '1px solid #e0e0e0',
    borderRadius: '8px',
    padding: '20px',
    backgroundColor: '#fafafa',
  },
  jobHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: '15px',
  },
  jobTitle: {
    fontSize: '16px',
    fontWeight: '600',
    color: '#333',
  },
  jobMeta: {
    fontSize: '12px',
    color: '#666',
    marginTop: '4px',
  },
  statusBadge: {
    padding: '4px 12px',
    borderRadius: '20px',
    fontSize: '12px',
    fontWeight: '500',
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
  stats: {
    display: 'flex',
    gap: '20px',
    fontSize: '13px',
    color: '#666',
  },
  statItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '5px',
  },
  cancelButton: {
    padding: '6px 12px',
    fontSize: '12px',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    backgroundColor: '#dc3545',
    color: 'white',
  },
  emptyState: {
    textAlign: 'center',
    padding: '40px',
    color: '#666',
  },
  errorMessage: {
    marginTop: '10px',
    padding: '10px',
    backgroundColor: '#f8d7da',
    borderRadius: '4px',
    color: '#721c24',
    fontSize: '13px',
  },
}

const statusColors = {
  pending: { bg: '#fff3cd', color: '#856404' },
  running: { bg: '#cce5ff', color: '#004085' },
  completed: { bg: '#d4edda', color: '#155724' },
  failed: { bg: '#f8d7da', color: '#721c24' },
  cancelled: { bg: '#e2e3e5', color: '#383d41' },
}

function JobStatus({ jobs, onCancel }) {
  if (!jobs || jobs.length === 0) {
    return (
      <div style={styles.emptyState}>
        No scraping jobs yet. Start a new job from the "New Scraping Job" tab.
      </div>
    )
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return '-'
    const date = new Date(dateStr)
    return date.toLocaleString()
  }

  return (
    <div style={styles.jobList}>
      {jobs.map((job) => {
        const progress = job.total_categories > 0
          ? (job.progress / job.total_categories) * 100
          : 0
        const statusStyle = statusColors[job.status] || statusColors.pending

        return (
          <div key={job.id} style={styles.jobCard}>
            <div style={styles.jobHeader}>
              <div>
                <div style={styles.jobTitle}>{job.location}</div>
                <div style={styles.jobMeta}>
                  Started: {formatDate(job.created_at)}
                  {job.completed_at && ` | Completed: ${formatDate(job.completed_at)}`}
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span
                  style={{
                    ...styles.statusBadge,
                    backgroundColor: statusStyle.bg,
                    color: statusStyle.color,
                  }}
                >
                  {job.status.toUpperCase()}
                </span>
                {(job.status === 'running' || job.status === 'pending') && (
                  <button
                    style={styles.cancelButton}
                    onClick={() => onCancel(job.id)}
                  >
                    Cancel
                  </button>
                )}
              </div>
            </div>

            {job.status === 'running' && (
              <div style={styles.progressBar}>
                <div
                  style={{
                    ...styles.progressFill,
                    width: `${progress}%`,
                  }}
                />
              </div>
            )}

            <div style={styles.stats}>
              <div style={styles.statItem}>
                <strong>Categories:</strong>
                {job.progress}/{job.total_categories}
              </div>
              <div style={styles.statItem}>
                <strong>Found:</strong>
                {job.total_found} contractors
              </div>
              {job.current_category && job.status === 'running' && (
                <div style={styles.statItem}>
                  <strong>Current:</strong>
                  {job.current_category.replace(/_/g, ' ')}
                </div>
              )}
            </div>

            <div style={{ marginTop: '10px', fontSize: '12px', color: '#888' }}>
              Categories: {job.categories.map(c => c.replace(/_/g, ' ')).join(', ')}
            </div>

            {job.error_message && (
              <div style={styles.errorMessage}>
                <strong>Error:</strong> {job.error_message}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

export default JobStatus
