# TimescaleDB Integration for Option Snapshots

This document explains the changes made to optimize the `optionSnapshot` table using TimescaleDB.

## Changes Made

1. **Replaced ticker with optionId**:
   - Changed the foreign key relationship from `ticker` to `optionId`
   - This reduces storage requirements by avoiding the duplication of long ticker strings

2. **Optimized for TimescaleDB**:
   - Converted the `option_snapshots` table to a TimescaleDB hypertable
   - Changed the primary key to include the time column first (`last_updated, optionId, id`)
   - Added appropriate indexes for time-series queries

## Schema Changes

The updated schema for the `OptionSnapshot` model:

```prisma
model OptionSnapshot {
  id            Int      @default(autoincrement())
  optionId      Int
  volume        Float?
  day_change    Float?
  day_close     Float?
  day_open      Float?
  implied_vol   Float?
  last_price    Float?
  last_updated  DateTime @db.Timestamptz  // NOT NULL for TimescaleDB
  last_crawled  DateTime @db.Timestamptz
  open_interest Int?
  option        Options  @relation(fields: [optionId], references: [id])

  // Primary key is now a composite of time column first, then optionId and id
  @@id([last_updated, optionId, id])
  
  // No need for additional indexes as the primary key already covers this
  @@map("option_snapshots")
}
```

## TimescaleDB Benefits

1. **Efficient Storage**:
   - TimescaleDB automatically partitions data into chunks based on time
   - This improves query performance for time-based queries
   - Reduces storage requirements through better compression

2. **Time-Series Specific Functions**:
   - `time_bucket()`: Group data into time intervals (hourly, daily, etc.)
   - `first()` and `last()`: Get first/last values in a time bucket
   - Continuous aggregates (materialized views optimized for time-series)

3. **Query Performance**:
   - Faster time-range queries
   - Efficient aggregations over time
   - Better index utilization

## Example Queries

### Daily Aggregation

```sql
SELECT 
    time_bucket('1 day', last_updated) AS day,
    "optionId",
    AVG(last_price) AS avg_price,
    MIN(last_price) AS min_price,
    MAX(last_price) AS max_price,
    SUM(volume) AS total_volume
FROM option_snapshots
WHERE last_updated >= NOW() - INTERVAL '7 days'
GROUP BY day, "optionId"
ORDER BY day DESC, "optionId"
```

### First/Last Values (Open/Close Prices)

```sql
SELECT 
    time_bucket('1 day', last_updated) AS day,
    "optionId",
    first(last_price, last_updated) AS open_price,
    last(last_price, last_updated) AS close_price
FROM option_snapshots
WHERE last_updated >= NOW() - INTERVAL '7 days'
GROUP BY day, "optionId"
ORDER BY day DESC, "optionId"
```

## Testing Scripts

1. `scripts/test_timescaledb.py`: Creates sample data and tests basic functionality
2. `scripts/timescaledb_benefits.py`: Demonstrates TimescaleDB-specific features and benefits

## Future Optimizations

1. **Compression Policies**:
   - Enable compression for chunks older than a certain age
   - Example: `SELECT add_compression_policy('option_snapshots', INTERVAL '7 days')`

2. **Retention Policies**:
   - Automatically remove data older than a certain age
   - Example: `SELECT add_retention_policy('option_snapshots', INTERVAL '1 year')`

3. **Continuous Aggregates**:
   - Create materialized views for common aggregation queries
   - Automatically refresh as new data arrives

Note: Some features like compression and retention policies require the TimescaleDB Community Edition or Enterprise license.