[README(1).md](https://github.com/user-attachments/files/29427841/README.1.md)
# Mission ATLAS — Real-Time Aircraft Telemetry Platform

> Ingesting live ADS-B telemetry from real aircraft, built on AWS with Terraform

ATLAS pulls **live air traffic** from the OpenSky Network, streams it through a production-grade AWS pipeline, and is being built out toward real-time anomaly detection, tiered storage, and multi-region resilience. Every piece is Infrastructure as Code. Every architectural decision is documented.

---

## 🚦 Project Status

ATLAS is built in deployable phases. This is an **active build**

| Phase | Focus | Status |
|-------|-------|--------|
| **0 — Preflight** | IaC foundations, remote state, CI identity, cost guardrails | ✅ Complete |
| **1 — Ingestion** | Live ADS-B → Kinesis, partitioned by aircraft | ✅ Complete |
| 2 — Stream Processing | Windowed aggregation + anomaly detection (Managed Flink) | ⏳ Next |
| 3 — Storage & Serving | Hot/cold tiering, live dashboard | ⬜ Planned |
| 4 — Operational Excellence | Full CI/CD, observability, load testing | ⬜ Planned |
| 5 — Resilience Engineering | RTO/RPO targets, chaos testing, multi-region failover | ⬜ Planned |
| 6 — Debrief | Architecture writeup, Well-Architected review, demo | ⬜ Planned |

---

## 🏗️ Current Architecture

```
                  ┌──────────────────────────────────────────────┐
   OpenSky        │                  AWS (us-east-1)             │
   ADS-B API ───► │   Producer ──────► Kinesis Data Stream       │
   (live          │   (OAuth2,         (on-demand, KMS-encrypted, │
    aircraft)     │    Python)          partitioned by icao24)    │
                  │                                              │
                  └──────────────────────────────────────────────┘

   Everything = Terraform.   CI = GitHub Actions (OIDC, no static keys).
```

**What's live today:**

- **Authenticated ingestion** — a Python producer authenticates to OpenSky via the OAuth2 client-credentials flow, polls live aircraft state vectors over a geographic bounding box, and streams them into Kinesis. Tokens are cached and auto-refreshed; rate limits are handled with backoff.
- **Kinesis Data Stream** — on-demand capacity mode (auto-scaling, no idle shard cost), 24-hour retention for replayability, KMS encryption at rest, and partitioned by aircraft ID (`icao24`) so each aircraft's track stays ordered.
- **Synthetic data generator** — a parallel producer emits realistically-shaped fake telemetry, used as a demo fallback and for testing the pipeline independently of the live API.

A typical poll ingests **~180 live aircraft** per batch.

---

## 🔐 Engineering Foundations (Phase 0)

- **Remote Terraform state** — versioned, encrypted, private S3 bucket with native S3 state locking (no DynamoDB lock table; deprecated as of Terraform 1.11).
- **Secure CI identity** — GitHub Actions authenticates to AWS via **OpenID Connect (OIDC)**. No long-lived access keys are stored anywhere; trust is scoped to this repository via the token's `sub` claim, and credentials are short-lived and auto-expiring.
- **Cost guardrails** — an AWS Budget with layered actual + forecasted alerts enforces a hard monthly ceiling. The whole stack is designed to `terraform destroy` cleanly between work sessions, keeping idle cost near zero.
- **Automated validation** — a GitHub Actions workflow runs `fmt`, `validate`, and security checks on every pull request.

---

## 🗂️ Repository Structure

```
mission-atlas/
├── docs/adr/        # Architecture Decision Records — the "why" behind every choice
├── infra/
│   ├── bootstrap/   # One-time: S3 state backend
│   ├── foundation/  # Permanent account baseline: OIDC identity, budget
│   └── dev/         # Application infrastructure: Kinesis (disposable, torn down between sessions)
├── src/             # Producers (live OpenSky + synthetic fallback)
├── runbooks/        # Operational procedures (grows in Phase 5)
└── .github/workflows/
```

A deliberate choice worth noting: **modules/environments are kept separate**, and each environment (`bootstrap`, `foundation`, `dev`) has its own isolated Terraform state under a distinct key in the same S3 bucket. This is the structure that scales to multi-environment deployment.

---

## 📐 Architecture Decision Records

The highest-signal artifacts in this repo. Architects are graded on whether they think in tradeoffs — these document the reasoning behind each major decision:

- **[ADR-001](docs/adr/ADR-001-github-oidc-vs-access-keys.md)** — GitHub OIDC vs. static IAM access keys
- **[ADR-002](docs/adr/ADR-002-terraform-state-backend.md)** — Terraform state backend (S3 + native locking)
- **[ADR-003](docs/adr/ADR-003-kinesis-vs-sqs-vs-msk.md)** — Streaming transport: Kinesis vs. SQS vs. MSK
- **[ADR-004](docs/adr/ADR-004-partition-key-icao24.md)** — Kinesis partition key strategy

---

## 🛠️ Tech Stack

**Infrastructure:** Terraform · AWS (Kinesis, S3, IAM, KMS, Budgets)
**Ingestion:** Python · boto3 · OpenSky Network API (OAuth2)
**CI/CD:** GitHub Actions · OIDC federation
**Coming:** Managed Service for Apache Flink · Timestream · Firehose · Athena · Managed Grafana · Fault Injection Service

---

## ▶️ Running It

> Requires AWS credentials configured locally and an OpenSky API client (`credentials.json`, gitignored).

```bash
# Provision the streaming infrastructure
cd infra/dev
terraform init
terraform apply

# Stream live aircraft into Kinesis
cd ../../src
pip install boto3 requests
python producer_live.py        # real OpenSky data
# or
python producer_synthetic.py   # synthetic fallback

# Tear it all down when finished (cost discipline)
cd infra/dev
terraform destroy
```

---

*Live air traffic data provided by the [OpenSky Network](https://opensky-network.org/).*
