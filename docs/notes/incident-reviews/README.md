# Incident Review Quick Reference

**Incident**: PostgreSQL Query Planner Error  
**Date**: October 26, 2025  
**Duration**: 18 minutes  
**Status**: ✅ Resolved

---

## TL;DR

**What Happened**: Service failing with PostgreSQL error "variable not found in subplan target list"

**Root Cause**: Prisma `connect` clause created complex subquery that failed under connection pool pressure

**Why Today**: Concurrency limit reduced from 700→100 yesterday (Oct 25, 5:58 PM), exposing latent bug

**Fix**: Removed `connect` clause, used direct foreign key assignment

**Prevention**: Better testing, gradual rollouts, query pattern documentation

---

## The Problem

```python
# ❌ BAD - Creates complex subquery
"create": {
    "option": {"connect": {"ticker": contract_ticker}},
    ...
}
```

## The Solution

```python
# ✅ GOOD - Direct assignment
"create": {
    "ticker": contract_ticker,
    ...
}
```

---

## Why It Worked Before

| Aspect | Before (Oct 25 12PM) | After (Oct 25 6PM) |
|--------|---------------------|-------------------|
| Concurrency Limit | 700 | 100 |
| Queue Pressure | Low | High (500 tasks → 100 slots) |
| Connection Pool | Relaxed | Stressed |
| Query Planner | Optimal path | Edge case triggered |
| Result | ✅ Works | ❌ Fails |

---

## Git Commits Involved

```bash
145a79b  enhance concurrency connection      ← Exposed bug
         - DATA_BASE_CONCURRENCY_LIMIT: 700 → 100
         - Added _db_semaphore wrapper
         
4325c69  avoiding bursting prisma limits     ← Changed connection management
         - Single persistent connection
```

---

## Key Learnings

1. **Latent bugs exist** - Configuration changes can expose hidden issues
2. **Simple is better** - Direct assignment > `connect` when FK is exposed
3. **Test under load** - Configuration changes need validation
4. **Gradual rollouts** - 85% reduction was too aggressive
5. **Monitor everything** - Add observability before making changes

---

## Action Items Priority

### P0 - Critical (This Week)
- [ ] Add integration tests for upsert
- [ ] Document Prisma patterns
- [ ] Setup PostgreSQL error alerting

### P1 - High (Next 2 Weeks)
- [ ] Create load testing framework
- [ ] Review connection limit configuration
- [ ] Deployment runbooks

### P2 - Medium (Next Month)
- [ ] Staging environment
- [ ] Query performance monitoring
- [ ] Regular performance reviews

---

## Quick Decision Guide: `connect` vs Direct Assignment

### Use Direct Assignment When:
- ✅ Foreign key field is exposed in model
- ✅ You know the FK value
- ✅ Simple one-to-one or many-to-one relation
- **Example**: Your case with `ticker`

### Use `connect` When:
- ⚠️ Foreign key is hidden/not in model
- ⚠️ You only know a unique field (not the FK)
- ⚠️ Need to create nested relations
- **Example**: FK is `userId: Int` but you only know `email`

---

## When to Review This Document

- ✅ When making database schema changes
- ✅ Before adjusting concurrency limits
- ✅ When onboarding new developers
- ✅ During quarterly incident reviews
- ✅ Before using Prisma `connect` clause

---

**Full Report**: See `2025-10-26-postgresql-query-planner-error.md`  
**Owner**: Engineering Team  
**Last Updated**: October 26, 2025
