# Strategy Tester Option Ingestor 事故 RCA（2026-06-07）

## 摘要

`2026-06-07` 晚上约 `19:00:48`（US/Pacific，对应 `2026-06-08 02:00:48 UTC`），`strategy-tester` 的 `option-ingestor` CronJob 在通过 Neon PostgreSQL pooler 写入期权合约数据时失败，目标地址为：

- host: `ep-snowy-silence-adv2fbdg-pooler.c-2.us-east-1.aws.neon.tech`
- port: `5432`

Grafana Loki 中最先出现的明确数据库错误是 Prisma `P1001`，即“`Can't reach database server`”。在第一次数据库可达性失败之后，同一批 ingestion 任务又连续出现了一串后续错误，包括：

- `ClientNotConnectedError`
- `RemoteProtocolError`
- `ReadError`

从本次排查结果看，这次事故只影响了 `option-ingestor`。在同一时间窗口内，没有看到 `snapshot-ingestor` 出现同样的 `P1001` 错误。

## 影响范围

- 当次 `option-ingestor` 定时任务未能成功完成合约 `upsert`
- 出问题前，该轮任务已经为 `NBIS` 拉取到 `2094` 条合约，因此故障发生在大批量写入过程中
- 该轮任务对应的期权合约数据未能按预期刷新，直到后续下一次成功 ingestion 才恢复

## 证据

本次排查使用的 Grafana 日志来源：

- datasource: `grafanacloud-jingyizhao01-logs`（`uid: grafanacloud-logs`）
- stream selector: `{namespace="strategy-tester",container="option-ingestor"}`

关键日志证据如下：

- `2026-06-08 02:00:41 UTC`
  `Total contracts found for NBIS: 2094`
- `2026-06-08 02:00:41 UTC`
  开始出现大量 `Upserting contract: ...` 日志，说明任务已经进入批量写库阶段
- `2026-06-08 02:00:48 UTC`
  Prisma engine 报出指向 Neon pooler 的 `P1001`
- `2026-06-08 02:00:48 UTC`
  应用日志开始出现 `Error upserting contract ...: Can't reach database server ...`
- `2026-06-08 02:00:48 UTC`
  其他并发协程继续报出 `Client is not connected to the query engine`
- `2026-06-08 02:00:48 UTC`
  同批次还出现 `Server disconnected without sending a response. (RemoteProtocolError)` 以及 `ReadError`

用户提供的 traceback 与 Grafana 中观测到的错误类型和时间戳是一致的，可以互相印证。

## 事故经过

在 [microservices/option_ingestor/ingestor.py](/home/jingyi/PycharmProjects/homelab-cloud/application/strategy-tester/microservices/option_ingestor/ingestor.py:31) 中，任务会先拉取某个标的的全部期权合约，再通过 `asyncio.gather(...)` 并发执行数据库 `upsert`。本次故障过程大致如下：

1. 任务正常完成合约拉取，并开始并发执行大量 `upsert`
2. 某一个或多个 Prisma 请求在访问 Neon pooler 时失去连通性，抛出 `P1001`
3. 由于同一时间已有大量写请求在飞行中，其他协程继续复用同一个 Prisma client，而此时底层 engine 已经进入异常状态
4. 原本一次数据库可达性抖动，被放大成一串级联错误，包括连接未建立、远端断开、读失败等
5. `_upsert_option_contract()` 在捕获异常后会重新抛出，因此整个 job 最终失败，而不是局部降级后继续执行

## 根因

本次事故的主根因是：

- 在批量 `upsert` 期间，应用到 Neon pooler 的数据库连通性出现短时故障，导致 Prisma 抛出 `P1001`

这个结论直接由 Grafana 日志和用户提供的 traceback 支撑。当前没有证据表明这是 schema 错误、SQL payload 错误，或者 Kubernetes 调度层面的故障。

## 促成因素

### 1. 写入并发量较高，放大了故障影响面

本轮任务为 `NBIS` 一次性拉取到了 `2094` 条合约，然后对这些数据进行并发 `upsert`。当前 Helm 配置为：

- `INGEST_CONCURRENCY_LIMIT=100`
- `INGEST_DB_CONCURRENCY_LIMIT=100`

见 [charts/strategy-tester/values.yaml](/home/jingyi/PycharmProjects/homelab-cloud/charts/strategy-tester/values.yaml:47)。

在数据库链路健康时，这个并发值本身不一定有问题；但一旦 Neon pooler 短时不可达或不稳定，较高的并发会明显扩大一次故障的波及范围。

### 2. Prisma 连接生命周期仍然是函数级，而不是 job 级

当前数据库包装逻辑在 [microservices/shared/decorator.py](/home/jingyi/PycharmProjects/homelab-cloud/application/strategy-tester/microservices/shared/decorator.py:18)，通过 `@bounded_db_connection` 管理 Prisma 的连接，而不是采用更清晰的“job 启动时 connect，一次任务结束后 disconnect”的生命周期模型。

这个风险其实已经在 [../adrs/0001-job-scoped-prisma-connection-lifecycle.md](/home/jingyi/PycharmProjects/homelab-cloud/application/strategy-tester/docs/adrs/0001-job-scoped-prisma-connection-lifecycle.md:1) 里被识别出来了。此次 Grafana 里的错误形态也和 ADR 中提到的担忧一致：一旦首个数据库错误出现，异步并发场景下更容易继续冒出 `ClientNotConnectedError` 一类级联问题。

### 3. 对瞬时数据库可达性错误缺少重试 / 退避机制

[microservices/option_ingestor/service.py](/home/jingyi/PycharmProjects/homelab-cloud/application/strategy-tester/microservices/option_ingestor/service.py:21) 中的服务入口是“一次运行到底”的模式。当前没有针对 `P1001` 这类瞬时数据库连通性故障增加应用层的 retry 或 backoff。

这意味着只要在关键写入阶段撞上一小段数据库抖动，本轮任务就很容易直接失败退出。

## 可以排除的方向

- 不是本次时间窗口内的 Kubernetes 调度故障
- 不是 Polygon 权限不足导致的错误
- 没有证据表明同一时间 `snapshot-ingestor` 也发生了相同的 Neon 可达性故障

## 后续改进建议

### 建议的代码改动

1. 将 Prisma 连接生命周期改成 job-scoped，而不是函数级 connect/disconnect
2. 对 `P1001` 以及类似的瞬时传输层错误补上显式 retry / backoff
3. 在 Neon pooler 不稳定时，考虑进一步降低有效 DB 写入并发，或者改成更可控的批量写入策略
4. 在日志和 tracing 中区分“首个触发错误”和“后续级联错误”，方便运维更快识别真正的起点

### 建议的运维改动

1. 在 `strategy-tester` 上增加针对 `P1001` 重复出现的 Grafana 告警
2. 增加一份针对 Neon pooler 可达性故障的 runbook，包括排查步骤和安全重跑流程
3. 后续如果再次出现同类故障，需要顺手对齐当时 Neon 是否存在已知 incident 或维护窗口

## 当前状态

- RCA 文档创建时间：`2026-06-08`
- 本次更新仅为事故分析和文档落地，不包含应用代码修复
