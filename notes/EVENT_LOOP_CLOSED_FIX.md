# Fix: "Event loop is closed" Error in stream_retrieve_active

## Problem

The error "Error streaming option contracts: Event loop is closed" was occurring in the `stream_retrieve_active()` method of `OptionRetriever`.

## Root Causes

### 1. **Missing `@bounded_db_connection` Decorator** (PRIMARY ISSUE)
The `stream_retrieve_active()` method was querying the database WITHOUT being decorated with `@bounded_db_connection`. This meant:
- The database connection was not guaranteed to be properly initialized before use
- The persistent connection pool managed by the decorator wasn't being leveraged
- Each batch query might encounter stale or closed connections
- Event loop context was inconsistent

### 2. **Async Generator Without Proper Resource Management**
- The generator was decorated with `@traced_span_asyncgen` but wasn't managing the database connection lifecycle
- When the generator was consumed and garbage collected, the event loop might have already been closed
- The span context was opened but the underlying DB resource wasn't properly scoped

### 3. **Context Mismatch**
- Called from `ingest_option_snapshots()` (which HAS `@bounded_db_connection`)
- But the internal generator didn't have the same decorator
- This created inconsistent event loop and connection contexts

## Solution

Added `@bounded_db_connection` decorator to `stream_retrieve_active()`:

```python
@bounded_db_connection
@traced_span_asyncgen(name="stream_retrieve_active", attributes={"module": "NEON"})
async def stream_retrieve_active(self, *args, **kwargs) -> AsyncGenerator[list["Options"], None]:
    # ... implementation
```

## How This Fixes It

### 1. **Persistent Connection**
- Ensures the database connection is established once and reused
- All batch queries use the same connection pool
- Eliminates "closed connection" errors

### 2. **Proper Event Loop Context**
- The decorator ensures the event loop is available for the entire generator lifecycle
- Connection semaphore prevents pool exhaustion
- Resource cleanup is guaranteed

### 3. **Consistent Decoration Pattern**
- Now matches the pattern used in other database-accessing methods
- Follows the same semaphore-limited concurrent access pattern
- All database calls go through the same resource management layer

## Decorator Stack Order

```python
@bounded_db_connection          # Manages DB connection & concurrency
@traced_span_asyncgen(...)      # Wraps for observability
async def stream_retrieve_active(...):
    # Implementation
```

This order ensures:
1. **Inner decorator** (`bounded_db_connection`): Handles connection setup, semaphore acquisition
2. **Outer decorator** (`traced_span_asyncgen`): Wraps the entire flow in a trace span

## Testing

After this fix, the error should no longer occur when:
- Running `ingest_option_snapshots()` 
- Processing large batches of option contracts
- Under concurrent load with multiple database queries

Monitor logs for:
```
Database pool stats - Active: X, Min: 10, Max: 100
Retrieved batch at offset Y for session Z
```

If no "Event loop is closed" errors appear, the fix is working.

## Related Code

- **File**: `options/retriever.py` line 47
- **Decorator**: `options/decorator.py` - `bounded_db_connection()`
- **Called from**: `options/ingestor.py` line 75 - `ingest_option_snapshots()`
- **Configuration**: `options/decorator.py` - `DATA_BASE_CONCURRENCY_LIMIT = 100`

## Technical Details

### Why This Matters for Async Generators

Async generators have special requirements for event loop management:
- They need the event loop to be active throughout their lifetime
- If the loop is closed before the generator is exhausted, you get "Event loop is closed"
- The `@bounded_db_connection` decorator ensures the loop context is maintained for all yields

### Connection Semaphore Integration

The `@bounded_db_connection` decorator also applies the `_db_semaphore`:
```python
async with _db_semaphore:
    # This ensures max DATA_BASE_CONCURRENCY_LIMIT=100 concurrent DB operations
```

Each batch query will acquire and release the semaphore, preventing connection pool exhaustion.
