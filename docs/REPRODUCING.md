# Reproduction and environment

## Layer 1: public results and manuscript

Install requirements.txt; notebooks 01–08 inspect aggregate files. `python scripts/build_tables.py` regenerates seven manuscript tables from CSV/JSON. C2C and full-topic source tables are retained with their matching aggregate CSVs. No classifier is rerun.

For PDF compilation install a full TeX Live/TinyTeX with latexmk, pdflatex and BibTeX. Required packages include geometry, setspace, graphicx, amsmath, amssymb, booktabs, threeparttable, float, tabularx, longtable, ragged2e, natbib, fontenc, inputenc, lmodern, microtype, caption and hyperref. Set IIP_TEX_BIN if executables are not on PATH. `python scripts/compile_manuscript.py` writes the review PDF in drafts/manuscript and build logs in build/latex. It does not install anything globally.

## Layer 2: frozen prepared inputs

Requires local data/processed/annual_review/*.parquet. `python scripts/reproduce_baseline.py --sort` recomputes 3 one-day regressions, reconstructs all daily baseline portfolios for 3 signals × 2 weights, and checks 12 CH4/q5 alpha models. Tolerances are 1e-4 bps for reported coefficients and 1e-4 for t statistics; sample sizes and daily series are checked. The 2026-10-23 run passed. This is not a fresh independent audit of every control coefficient or raw ingestion.

## Layer 3: master-panel reconstruction

Requires the local master and cohort files. `python scripts/prepare_original.py` preserves original preparation arithmetic, separate ESI pools, dates and sample rules and writes a fresh data/temp/rebuilt_annual_review directory. It refuses to overwrite prepared_reg.parquet. This portable adaptation is syntax-checked; the full preparation stage was not rerun in the integration session. Baseline reproduction uses already-accepted inputs instead. The historical preparation source is archived for comparison.

## Layer 4: licensed raw ingestion and other analyses

Raw files remain in the earlier reference project and are not in Git. Original ingestion and analysis notebooks are preserved without outputs; they retain historical machine paths and are not directly portable. Existing C2C/topic/announcement results are imported, with original programs archived and aggregate verification retained. Their full source-data pipelines and model environments are not rebuilt here. Qwen classification is complete and must not be repeated just to use these results.

## Remaining dependencies and research choices

- Local Python before takeover provides pinned statistical packages. Jupyter and plotting are optional additions; no new environment is imposed on the old project.
- The project-local plotting dependencies and five missing TeX packages are in build/ and excluded from Git.
- Independent human semantic labels, analyst EPS forecasts, intraday announcement times, and independently rebuilt accounting vintages are not available.
- Historical multi-horizon/Fama–MacBeth reconciliation, a matched historical full-text horse race, and the old supplementary mechanisms remain open. No estimate is imputed or substituted to fill those gaps.
