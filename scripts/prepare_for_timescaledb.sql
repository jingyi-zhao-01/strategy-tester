-- Drop the unique constraint that doesn't include the time column as first column
ALTER TABLE option_snapshots DROP CONSTRAINT IF EXISTS "option_snapshots_id_optionId_last_updated_key";

-- Create a new unique constraint with last_updated as the first column
ALTER TABLE option_snapshots ADD CONSTRAINT "option_snapshots_last_updated_optionId_id_key" 
    UNIQUE (last_updated, "optionId", id);

-- Now convert to hypertable
SELECT create_hypertable('option_snapshots', 'last_updated', 
                         if_not_exists => TRUE,
                         create_default_indexes => FALSE);

-- Set chunk time interval to 1 day (adjust based on your data volume)
SELECT set_chunk_time_interval('option_snapshots', INTERVAL '1 day');

-- Create additional indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_option_snapshots_optionid_time ON option_snapshots ("optionId", last_updated DESC);