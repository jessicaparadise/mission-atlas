# ADR-003: Streaming transport — Kinesis Data Streams vs SQS vs MSK

**Status:** Accepted

**Context:** ATLAS ingests a continuous, high-volume stream of aircraft telemetry (~180 aircraft per poll over a single region, updating every few seconds). Downstream, multiple independent consumers will need this data: real-time windowed processing (Flink), archival to a data lake, and a live dashboard. The transport layer must support ordered, replayable, high-throughput streaming that several consumers can read independently.

**Decision:** Use Amazon Kinesis Data Streams.

The alternatives considered:
- **SQS (queue):** Designed for decoupled task processing, not streaming. Records are consumed-and-deleted, so there is no replay, and ordering is only available (with throughput caps) via FIFO queues. A single message is processed by one consumer — it does not fan out to multiple independent readers. Wrong model for a telemetry stream that needs replay and multiple consumers.
- **MSK (managed Kafka):** Technically capable and arguably more powerful, but it is operationally heavy — broker management, partition tuning, and a higher cost floor. Overkill for a single-region telemetry feed at this scale.
- **Kinesis Data Streams:** Native AWS streaming. Ordered within a partition, replayable (records persist for the retention window, not consumed-and-gone), supports multiple independent consumers reading the same stream, and integrates directly with Firehose, Flink, and Lambda. On-demand mode removes shard-capacity planning for spiky dev traffic.

**Consequences:** We get ordered, replayable streaming with native fan-out to multiple consumers and minimal operational overhead. Trade-off: Kinesis has AWS-specific semantics (shards, partition keys, iterators) rather than the portable Kafka ecosystem — acceptable, since ATLAS is intentionally an AWS-native architecture. If throughput or multi-region streaming needs grow substantially, MSK becomes the reconsidering point.