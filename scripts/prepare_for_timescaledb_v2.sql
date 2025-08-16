-- Drop all constraints
ALTER TABLE option_snapshots DROP CONSTRAINT IF EXISTS "option_snapshots_pkey";
ALTER TABLE option_snapshots DROP CONSTRAINT IF EXISTS "option_snapshots_id_optionId_last_updated_key";
ALTER TABLE option_snapshots DROP CONSTRAINT IF EXISTS "option_snapshots_last_updated_optionId_id_key";

-- Drop foreign key constraint
ALTER TABLE option_snapshots DROP CONSTRAINT IF EXISTS "option_snapshots_optionId_fkey";

-- Create a new primary key with last_updated as the first column
ALTER TABLE option_snapshots ADD PRIMARY KEY (last_updated, "optionId", id);

-- Add back the foreign key
ALTER TABLE option_snapshots ADD CONSTRAINT "option_snapshots_optionId_fkey" 
    FOREIGN KEY ("optionId") REFERENCES options(id) ON UPDATE CASCADE ON DELETE RESTRICT;

-- Now convert to hypertable
SELECT create_hypertable('option_snapshots', 'last_updated', 
                         if_not_exists => TRUE,
                         create_default_indexes => FALSE,
                         migrate_data => TRUE);

-- Set chunk time interval to 1 day (adjust based on your data volume)
SELECT set_chunk_time_interval('option_snapshots', INTERVAL '1 day');