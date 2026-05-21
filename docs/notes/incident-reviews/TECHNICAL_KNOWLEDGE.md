# Technical Knowledge Base: Prisma & PostgreSQL

This document captures technical knowledge gained from the October 26, 2025 incident.

---

## Prisma Relation Patterns

### Direct Foreign Key Assignment

**When to use**: Foreign key field is exposed in your model

```prisma
// Schema
model OptionSnapshot {
  ticker        String   // ← FK is exposed
  option        Options  @relation(fields: [ticker], references: [ticker])
}
```

```python
# Code - Direct assignment ✅
await OptionSnapshot.prisma().upsert(
    where={...},
    data={
        "create": {
            "ticker": "O:AAPL251121C00150000",  # Direct FK assignment
            "volume": 1000,
            ...
        }
    }
)
```

**Advantages**:
- ✅ Simple, clear intent
- ✅ Better performance (no extra SELECT)
- ✅ More resilient to query planner issues
- ✅ Works identically in create and update

### Using `connect` Clause

**When to use**: Foreign key is hidden or you need relation lookup

```prisma
// Schema - FK not exposed
model OptionSnapshot {
  optionId      Int      // ← FK hidden, only know ticker
  option        Options  @relation(fields: [optionId], references: [id])
}
```

```python
# Code - Must use connect ⚠️
await OptionSnapshot.prisma().upsert(
    where={...},
    data={
        "create": {
            "option": {
                "connect": {"ticker": "O:AAPL251121C00150000"}
            },
            "volume": 1000,
            ...
        }
    }
)
```

**What it does**: Generates a subquery to find the related record:
```sql
-- Approximate SQL
SELECT id FROM options WHERE ticker = 'O:AAPL251121C00150000'
-- Then uses that id in the INSERT
```

**Disadvantages**:
- ⚠️ Extra query/subquery
- ⚠️ More complex query plan
- ⚠️ Can trigger PostgreSQL planner edge cases
- ⚠️ Different behavior under connection pooling

---

## PostgreSQL Query Planner

### Error XX000: Internal Error

**Full error message**:
```
Error occurred during query execution:
ConnectorError(ConnectorError { 
  user_facing_error: None, 
  kind: QueryError(PostgresError { 
    code: "XX000", 
    message: "variable not found in subplan target list", 
    severity: "ERROR"
  })
})
```

**What it means**: 
- PostgreSQL's query optimizer chose an execution plan that referenced a variable incorrectly
- Usually indicates a bug or edge case in PostgreSQL itself
- Often triggered by complex nested subqueries

**Common triggers**:
1. Complex CTEs (Common Table Expressions)
2. Nested subqueries in ON CONFLICT clauses
3. Upsert operations with multiple relations
4. Connection pooler interference with plan caching
5. Stale query plans after connection pool changes

**How to diagnose**:
```sql
-- Check if table statistics are stale
ANALYZE option_snapshots;
ANALYZE options;

-- View current query plan
EXPLAIN ANALYZE <your query>;

-- Check for corruption
SELECT * FROM pg_stat_user_tables WHERE schemaname = 'public';
```

**Resolution strategies**:
1. ✅ Simplify the query (best approach)
2. Run ANALYZE on affected tables
3. Restart connection pool
4. Disable parallel query execution
5. Upgrade PostgreSQL version

### Query Plan Caching

**How it works**:
1. PostgreSQL caches execution plans for prepared statements
2. Plan choice depends on table statistics and connection state
3. Connection poolers can interfere with this caching

**Under normal conditions**:
```
Query → Parser → Analyzer → Planner → Cached Plan → Execution
                             ↓
                      (Optimal path chosen)
```

**Under stress** (high queue pressure, connection churn):
```
Query → Parser → Analyzer → Planner → Different Plan → Execution
                             ↓
                      (Suboptimal path chosen)
                             ↓
                      Variable resolution fails → XX000
```

---

## Connection Pooling Architecture

### Layers of Concurrency Control

```
┌───────────────────────────────┐
│   Application Tasks (500+)    │  ← asyncio.gather creates many tasks
└───────────────┬───────────────┘
                │
┌───────────────▼───────────────┐
│   Semaphore (100 slots)       │  ← DATA_BASE_CONCURRENCY_LIMIT
│   _db_semaphore wrapper       │     Limits concurrent DB operations
└───────────────┬───────────────┘
                │
┌───────────────▼───────────────┐
│   Prisma Client               │  ← Single persistent connection
│   (one per process)           │     (after commit 4325c69)
└───────────────┬───────────────┘
                │
┌───────────────▼───────────────┐
│   asyncpg Connection Pool     │  ← connection_limit=1200
│   (Prisma's internal pool)    │     Physical connections to DB
└───────────────┬───────────────┘
                │
┌───────────────▼───────────────┐
│   Neon Connection Pooler      │  ← Transparent proxy
│   (transaction/session mode)  │     Multiplexes connections
└───────────────┬───────────────┘
                │
┌───────────────▼───────────────┐
│   PostgreSQL Database         │  ← Actual database
└───────────────────────────────┘
```

### Impact of Each Layer

| Layer | Purpose | Impact on Query Planning |
|-------|---------|--------------------------|
| Semaphore | Rate limiting | Can cause queueing, affects timing |
| Prisma Pool | Connection reuse | Plan caching at asyncpg level |
| Neon Pooler | Resource efficiency | Different connections = different plans |
| PostgreSQL | Execution | Final plan choice and caching |

---

## Neon Connection Pooler Behavior

### Pooling Modes

**Transaction Pooling** (default):
- Each transaction gets a potentially different connection
- Query plan cache not preserved across transactions
- More aggressive connection reuse
- Best for short transactions

**Session Pooling**:
- Client gets same connection for entire session
- Query plan cache preserved
- Less connection reuse
- Better for complex query patterns

### Configuration

```bash
# Your current setup
DATABASE_URL="postgresql://user:pass@...-pooler.c-2.us-east-1.aws.neon.tech/db?connection_limit=1200"
#                                        ^^^^^^                                    ^^^^^^^^^^^^^^^^^^
#                                     Pooler hostname                          Pool size parameter
```

**Pooler effects on query planning**:
1. Plan cache misses more common
2. Connection state not guaranteed
3. Temporary tables/prepared statements may disappear
4. SET commands don't persist across transactions

---

## Debugging Checklist

### When Encountering Database Errors

**Step 1: Verify basic connectivity**
```python
async def test_connection():
    db = Prisma()
    await db.connect()
    result = await db.query_raw("SELECT 1")
    await db.disconnect()
    return result
```

**Step 2: Check query structure**
- [ ] Is the query unnecessarily complex?
- [ ] Are there nested subqueries?
- [ ] Could direct assignment replace `connect`?
- [ ] Is the table structure optimal?

**Step 3: Test under different loads**
- [ ] Works with low concurrency?
- [ ] Fails only under high concurrency?
- [ ] Sequential processing avoids error?
- [ ] Connection pool exhaustion?

**Step 4: Database health**
```sql
-- Check table statistics
SELECT * FROM pg_stat_user_tables WHERE relname = 'option_snapshots';

-- Check active connections
SELECT count(*) FROM pg_stat_activity;

-- Check for locks
SELECT * FROM pg_locks WHERE NOT granted;
```

**Step 5: Configuration review**
- [ ] Semaphore limit vs connection pool size
- [ ] Connection string parameters
- [ ] Pooler mode (transaction vs session)
- [ ] Recent configuration changes

---

## Best Practices

### Prisma Operations

**DO**:
- ✅ Use direct FK assignment when possible
- ✅ Keep queries simple
- ✅ Test under production-like load
- ✅ Monitor query performance
- ✅ Use composite indexes appropriately

**DON'T**:
- ❌ Use `connect` when FK is exposed
- ❌ Create unnecessarily complex relations
- ❌ Change concurrency limits without testing
- ❌ Ignore query performance in development
- ❌ Deploy without integration tests

### Configuration Changes

**Before changing concurrency limits**:
1. Document current behavior
2. Test with new limits in staging
3. Monitor key metrics
4. Deploy gradually (not 700 → 100 immediately)
5. Have rollback plan ready

**Safe concurrency adjustment**:
```python
# Instead of: 700 → 100 (85% reduction)
# Do:         700 → 500 → 300 → 100 (gradual)
```

### Schema Design

**Prefer**:
- Simple primary keys over composite when possible
- Exposed foreign keys for common relations
- Normalized structure
- Appropriate indexes

**Avoid**:
- Unnecessary composite keys
- Hidden foreign keys requiring lookups
- Deeply nested relations
- Overly complex constraints

---

## Performance Characteristics

### Query Patterns Performance

| Pattern | Reads | Writes | Complexity | Risk |
|---------|-------|--------|------------|------|
| Direct FK assign | 0 | 1 | Low | Low ✅ |
| `connect` | 1 | 1 | Medium | Medium ⚠️ |
| Nested `connect` | N | 1 | High | High ❌ |
| Multiple relations | N | 1 | High | High ❌ |

### Concurrency Scaling

| Tasks | Limit | Queue Length | Behavior |
|-------|-------|--------------|----------|
| 100 | 100 | 0 | Smooth ✅ |
| 200 | 100 | 100 | Acceptable ⚠️ |
| 500 | 100 | 400 | High pressure ⚠️ |
| 1000 | 100 | 900 | Critical ❌ |

**Formula**: `Queue Length = Tasks - Limit`

**When queue length > 5x limit**: Expect issues

---

## Related PostgreSQL Errors

### Other Internal Errors to Watch

| Code | Message | Typical Cause |
|------|---------|---------------|
| XX000 | Internal error | Query planner bug |
| XX001 | Data corrupted | Hardware/filesystem issue |
| 40001 | Serialization failure | Concurrent transactions |
| 40P01 | Deadlock detected | Lock contention |
| 53300 | Too many connections | Pool exhaustion |

### Query Optimization Errors

| Code | Message | Solution |
|------|---------|----------|
| 42P01 | Undefined table | Schema sync issue |
| 42703 | Undefined column | Schema mismatch |
| 42883 | Undefined function | Extension missing |

---

## References

### Internal Documentation
- `DATABASE_CONCURRENCY_CONFIG.md` - Concurrency configuration guide
- `incident-reviews/2025-10-26-*.md` - Full incident report
- `prisma/schema.prisma` - Database schema

### External Resources
- [Prisma Relations](https://www.prisma.io/docs/concepts/components/prisma-schema/relations)
- [PostgreSQL Error Codes](https://www.postgresql.org/docs/current/errcodes-appendix.html)
- [Neon Connection Pooling](https://neon.tech/docs/connect/connection-pooling)
- [asyncpg Performance](https://github.com/MagicStack/asyncpg#performance)

---

**Last Updated**: October 26, 2025  
**Maintainer**: Engineering Team  
**Review Frequency**: Quarterly or after major incidents
