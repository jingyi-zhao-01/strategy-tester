# Fix: "'async for' requires __aiter__ method" Error

## Problem

Error: `'async for' requires an object with __aiter__ method, got coroutine`

This occurred when calling `stream_retrieve_active()` in `ingest_option_snapshots()`:
```python
async for contracts_batch in self.option_retriever.stream_retrieve_active():
    # ...
```

## Root Cause

The `@bounded_db_connection` decorator was designed for **regular async functions** that return a value:
```python
async def some_func():
    return await query()  # Returns a value
```

It wraps the function in a way that returns a **coroutine**, not an **async generator**.

When you decorated an **async generator function** with it:
```python
@bounded_db_connection  # WRONG for async generators!
async def stream_retrieve_active():
    while True:
        yield batch  # Yields values
```

The decorator converted it to return a coroutine instead of an async generator, breaking the `async for` pattern.

## Solution

Created a new dedicated decorator `@bounded_db_connection_asyncgen` specifically for async generators:

### Changes Made:

1. **Created new decorator in `options/decorator.py`:**
```python
def bounded_db_connection_asyncgen(func):
    """Wrap async generators with database connection and concurrency management."""
    async def wrapper(*args, **kwargs):
        # ... establish connection ...
        # For async generators, limit concurrency per yield
        async for item in func(*args, **kwargs):
            async with _db_semaphore:
                _log_connection_pool_stats()
                yield item
    return wrapper
```

2. **Updated `options/retriever.py`:**
```python
from options.decorator import (
    bounded_db_connection,              # For regular async functions
    bounded_db_connection_asyncgen,     # For async generators
    traced_span_asyncgen,
)

# Regular async function - uses bounded_db_connection
@bounded_db_connection
async def retrieve_all(self) -> list["Options"]:
    # ...

# Async generator - uses bounded_db_connection_asyncgen
@traced_span_asyncgen(name="stream_retrieve_active", attributes={"module": "NEON"})
@bounded_db_connection_asyncgen
async def stream_retrieve_active(self) -> AsyncGenerator[list["Options"], None]:
    # ...
```

## How It Works

### Key Difference:

| Type | Decorator | Pattern |
|------|-----------|---------|
| **Regular async function** | `@bounded_db_connection` | `result = await func()` |
| **Async generator** | `@bounded_db_connection_asyncgen` | `async for item in func(): ...` |

### Both decorators ensure:
1. ✅ Database connection is established once and reused
2. ✅ Connection pool semaphore limits concurrent operations
3. ✅ Connection pool statistics are logged
4. ✅ Proper resource cleanup

### Decorator Stack Order (for async generators):
```python
@traced_span_asyncgen(...)          # Outer: Wraps for observability
@bounded_db_connection_asyncgen     # Inner: Manages connection & concurrency
async def stream_retrieve_active(...):
    # Implementation
```

This order ensures:
1. Inner decorator handles connection setup and semaphore
2. Outer decorator wraps the generator in a trace span
3. `async for` pattern works correctly

## Testing

After this fix:
- ✅ No more "TypeError: 'async for' requires __aiter__ method, got coroutine"
- ✅ Async generators can properly yield batches
- ✅ Database connection is managed per-batch
- ✅ Concurrency is limited to `DATA_BASE_CONCURRENCY_LIMIT`

Example working flow:
```python
async for contracts_batch in self.option_retriever.stream_retrieve_active():
    # Each iteration:
    # 1. Acquires semaphore slot
    # 2. Logs connection pool stats
    # 3. Yields the batch
    # 4. Releases semaphore slot when done
    process(contracts_batch)
```

## Lessons Learned

1. **Different decorator patterns for different function types:**
   - Regular async functions: `return await func()`
   - Async generators: `async for item in func(): yield item`

2. **Type preservation is critical:**
   - Async function ≠ Async generator
   - Decorators must preserve the function type they wrap

3. **Decorator stacking with generators:**
   - Order matters: observability decorator on the outside
   - Inner decorator handles resource management
   - Maintains proper flow for `async for` pattern

## Related Code

- **New decorator**: `options/decorator.py` - `bounded_db_connection_asyncgen()`
- **Async generator using it**: `options/retriever.py` - `stream_retrieve_active()`
- **Caller**: `options/ingestor.py` - `ingest_option_snapshots()`
- **Configuration**: `options/decorator.py` - `DATA_BASE_CONCURRENCY_LIMIT = 100`
