# Classifier Documents

This directory contains curated, class-specific PDFs for targeted classifier ingestion with `policy_class` metadata.

These folders are intentionally separate from the broad legacy corpus. Do not ingest broad legacy corpus folders during classifier work unless duplicate chunks are intentionally accepted. Future classifier ingestion should point only at the curated class folder being tested.

Current readiness:

- `adu`: strong. Contains multiple Accessory Dwelling Unit sources suitable for targeted ingestion.
- `affordable_dwelling_unit`: provisional. Contains one affordable-unit program document useful for smoke testing, but not a clean Affordable Dwelling Unit Ordinance, WDU, or MPDU source.
- `density_bonus`: missing clean source. No local density-bonus-specific PDF was found.

Do not run ingestion with `--reset` for classifier work.
