# Roadmap — PharmaVision AI

## Phase 1 (this release, v0.2.0) — working local MVP

Landing + registration, tenant isolation, secure local login, inventory batches with FEFO, point-of-sale, recall quarantine, customer profiles with basic consent flag, sales reports, baseline forecast, Tesseract OCR option, barcode lookup and rule-based inventory copilot. Tests included.

## Phase 2 — domain correctness and operations

- Product catalog normalized against a **licensed and verified** medicine knowledge base; validated active ingredients, dosage strength, manufacturer and registration numbers.
- External source comparison and human review for OCR (invoice and product packaging): field-level confidence, supplier reconciliation, structured invoice layouts, scanning history.
- Per-branch inventory, transfers, stocktakes and detailed access permissions.
- Customer privacy controls: consent versioning, retention periods, delete/export workflow, encryption at rest, immutable audit storage, secure backup and recovery.
- Hardened deployment: HTTPS/TLS, containerized web server, proper application server, reverse proxy, CSRF/CSP policies, structured monitoring and security testing.

## Phase 3 — validated intelligence

- Forecasting: collect a sufficient amount of clean historical sales and lead times; compare transparent baseline against seasonal statistics and trained ML with backtesting and confidence intervals.
- Pharmacy assistant connected to verified and licensed drug references, with clear citations and required pharmacist review. No clinical risk statements from a generic model alone.
- Role-aware alerts, alert workflow approval and controlled recall feed with document-level provenance.
- Prescription e-data integration only after legally required authorization, approved API and integration testing.

## Phase 4 — external integrations

- Compliant linkage to the National Pharmaceutical Database per official technical specifications **after authorization**.
- Zalo OA with customer consent and limits on sensitive information; no unsolicited medical marketing.
- Invoicing/payment integrations, API gateway, chain analytics and deployment/ops dashboards.

## Release acceptance criteria for real pharmacies

Security audit, legal compliance assessment, data protection impact analysis as applicable, medicine database validation, documented pharmacist SOPs, GPP workflow validation, API connectivity tests, backup restore drills and regression tests all need to be completed independently before any real-world rollout.
