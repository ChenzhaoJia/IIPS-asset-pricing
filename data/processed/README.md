# Accepted local prepared data

01_Base_Daily_Panel_Advanced.parquet: original master panel.
cohort_lags_verified.parquet: verified matched-cohort timing.
annual_review/: prepared_reg, prepared_port, factors, daily_portfolios.

Licensed/record-level files are git-ignored. Reproduce the main baseline with scripts/reproduce_baseline.py. Rebuild inputs into data/temp/rebuilt_annual_review with scripts/prepare_original.py; compare before promoting any rebuild. Current copies have hashes in data/manifests/input_manifest.json.
