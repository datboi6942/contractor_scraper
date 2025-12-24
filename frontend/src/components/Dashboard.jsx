import React from 'react'

const styles = {
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
    gap: '15px',
    marginBottom: '30px',
  },
  statCard: {
    backgroundColor: '#f8f9fa',
    borderRadius: '10px',
    padding: '20px',
    textAlign: 'center',
    border: '1px solid #e9ecef',
  },
  statCardHighlight: {
    backgroundColor: '#e8f5e9',
    borderRadius: '10px',
    padding: '20px',
    textAlign: 'center',
    border: '2px solid #4caf50',
  },
  statValue: {
    fontSize: '28px',
    fontWeight: 'bold',
    color: '#667eea',
    marginBottom: '5px',
  },
  statValueGreen: {
    fontSize: '28px',
    fontWeight: 'bold',
    color: '#2e7d32',
    marginBottom: '5px',
  },
  statLabel: {
    fontSize: '13px',
    color: '#666',
  },
  statPercent: {
    fontSize: '12px',
    color: '#888',
    marginTop: '5px',
  },
  section: {
    marginTop: '30px',
  },
  sectionTitle: {
    fontSize: '18px',
    fontWeight: '600',
    marginBottom: '15px',
    color: '#333',
  },
  categoryGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
    gap: '10px',
  },
  categoryCard: {
    backgroundColor: '#f0f4ff',
    borderRadius: '6px',
    padding: '12px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  categoryName: {
    fontSize: '13px',
    color: '#333',
    textTransform: 'capitalize',
  },
  categoryCount: {
    fontSize: '14px',
    fontWeight: 'bold',
    color: '#667eea',
  },
  emptyState: {
    textAlign: 'center',
    padding: '40px',
    color: '#666',
  },
}

function Dashboard({ stats, jobs }) {
  if (!stats) {
    return <div style={styles.emptyState}>Loading statistics...</div>
  }

  const activeJobs = jobs?.filter((j) => j.status === 'running') || []

  const pct = (val) => stats.total_contractors > 0
    ? Math.round((val / stats.total_contractors) * 100)
    : 0

  return (
    <div>
      {/* Main Stats */}
      <div style={styles.grid}>
        <div style={styles.statCard}>
          <div style={styles.statValue}>{stats.total_contractors}</div>
          <div style={styles.statLabel}>Total Contractors</div>
        </div>
        <div style={styles.statCardHighlight}>
          <div style={styles.statValueGreen}>{stats.with_owner || 0}</div>
          <div style={styles.statLabel}>With Owner Name</div>
          <div style={styles.statPercent}>{pct(stats.with_owner || 0)}% of total</div>
        </div>
        <div style={styles.statCard}>
          <div style={styles.statValue}>{stats.with_phone || 0}</div>
          <div style={styles.statLabel}>With Phone</div>
          <div style={styles.statPercent}>{pct(stats.with_phone || 0)}% of total</div>
        </div>
        <div style={styles.statCard}>
          <div style={styles.statValue}>{stats.with_email || 0}</div>
          <div style={styles.statLabel}>With Email</div>
          <div style={styles.statPercent}>{pct(stats.with_email || 0)}% of total</div>
        </div>
        <div style={styles.statCard}>
          <div style={styles.statValue}>{stats.active_jobs}</div>
          <div style={styles.statLabel}>Active Jobs</div>
        </div>
        <div style={styles.statCard}>
          <div style={styles.statValue}>
            {Object.keys(stats.categories_breakdown || {}).length}
          </div>
          <div style={styles.statLabel}>Categories</div>
        </div>
      </div>

      {activeJobs.length > 0 && (
        <div style={styles.section}>
          <div style={styles.sectionTitle}>Active Jobs</div>
          {activeJobs.map((job) => (
            <div
              key={job.id}
              style={{
                backgroundColor: '#e8f5e9',
                borderRadius: '8px',
                padding: '15px',
                marginBottom: '10px',
              }}
            >
              <div style={{ fontWeight: '500', marginBottom: '5px' }}>
                {job.location}
              </div>
              <div style={{ fontSize: '13px', color: '#666' }}>
                Progress: {job.progress}/{job.total_categories} categories |
                Found: {job.total_found} contractors
                {job.current_category && ` | Current: ${job.current_category}`}
              </div>
            </div>
          ))}
        </div>
      )}

      <div style={styles.section}>
        <div style={styles.sectionTitle}>Contractors by Category</div>
        {Object.keys(stats.categories_breakdown || {}).length === 0 ? (
          <div style={styles.emptyState}>
            No contractors collected yet. Start a scraping job to gather data.
          </div>
        ) : (
          <div style={styles.categoryGrid}>
            {Object.entries(stats.categories_breakdown)
              .sort((a, b) => b[1] - a[1])
              .map(([category, count]) => (
                <div key={category} style={styles.categoryCard}>
                  <span style={styles.categoryName}>
                    {category.replace(/_/g, ' ')}
                  </span>
                  <span style={styles.categoryCount}>{count}</span>
                </div>
              ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default Dashboard
