# ADR-002: Terraform state backend

**Status:** Accepted

**Context:** Terraform needs a durable, shared home for state. Local state dies with the laptop, cannot be read by CI, and corrupts under concurrent applies. State can also contain sensitive values, so it must be encrypted. The classic AWS pattern pairs an S3 bucket (storage) with a DynamoDB table (locking).

**Decision:** Remote state in a versioned, encrypted, private S3 bucket, with locking via native S3 conditional writes (`use_lockfile = true`) rather than a DynamoDB table. Native S3 locking landed in Terraform 1.10 and the DynamoDB lock table was deprecated in 1.11. The bucket name is derived from the AWS account ID for deterministic global uniqueness. The bucket is bootstrapped with local state, then migrated to manage its own state remotely.

**Consequences:** One fewer resource to provision and pay for versus the DynamoDB pattern. State survives laptop loss, is readable by CI, and is recoverable via S3 versioning. Each environment (bootstrap, foundation, dev) uses a distinct `key` path in the same bucket, so they share storage without colliding. Trade-off: the bootstrap config holds the state of the bucket its own state lives in — acceptable, since the state bucket is permanent and never torn down.