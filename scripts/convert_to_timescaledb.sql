-- Convert option_snapshots table to a TimescaleDB hypertable
SELECT create_hypertable('option_snapshots', 'last_updated', 
                         if_not_exists => TRUE,
                         create_default_indexes => FALSE);

-- Set chunk time interval to 1 day (adjust based on your data volume)
SELECT set_chunk_time_interval('option_snapshots', INTERVAL '1 day');

-- Create additional indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_option_snapshots_optionid_time ON option_snapshots (optionId, last_updated DESC);

-- Note: For data retention, you can create a scheduled job to run:
-- DELETE FROM option_snapshots WHERE last_updated < NOW() - INTERVAL '1 year';