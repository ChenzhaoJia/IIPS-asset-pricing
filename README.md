## 📖 Overview

This repository contains the empirical asset pricing codebase investigating the informational value of high-frequency textual interactions on the Chinese A-share Investor Interactive Platforms (IIPs). 

Drawing from *Ke, Kelly, & Xiu (2026)* and *Lopez-Lira & Tang (2026)*, we introduce a new factor: the **Effective Soothing Index (ESI)**. The project systematically demonstrates that retail investor sentiment, when interacted with NLP-parsed, substantive managerial responses, possesses significant predictive power for future stock returns, orthogonal to traditional asset pricing anomalies and mainstream media hype.


## 🗂 Project Structure

The project strictly separates reusable quantitative engineering logic (`src/`) from empirical research presentation (`notebooks/`).

```text
├── data/                    # Local data directories (git-ignored)
│   ├── raw/                 # CSMAR / Alternative datasets
│   └── processed/           # Highly optimized Parquet Panels
├── notebooks/               # Research pipeline
│   ├── 01_data_ingestion.ipynb                 # Extreme memory-safe panel merging
│   ├── 02_data_description_and_summary.ipynb   # Stylized facts, sparsity & Trust Bankruptcy
│   ├── 03_portfolio_sorts_and_performance.ipynb# Factor building (ESI) & Top-N sorts
│   ├── 04_baseline_predictability_regressions.ipynb # Panel OLS & Fama-MacBeth
│   └── 05_mechanism_fundamentals_and_microstructure.ipynb # Microstructure order flows
├── src/                     # Core quantitative codebase
│   ├── data/                # Parquet loaders and anti-look-ahead merging
│   ├── features/            # ESI construction and return timing decomposition
│   ├── models/              # OOP Sorting Engines (Top/Bottom N, Decile, Double Sorts)
│   ├── evaluation/          # Factor model evaluations (CH4, q5, Newey-West)
│   └── utils/               # Academic table formatters
├── requirements.txt         # Dependency specifications
└── README.md
```


**Data Preparation:**
   Please ensure your raw data is placed in `data/raw/`. The data structure expects standard CSMAR formats (Trading Data, Financials, Governance) alongside pre-calculated NLP platform data (`QnA_Slim_Panel.parquet`).

## 📊 Pipeline Walkthrough

### 1. Data Ingestion (`01_data_ingestion`)
A massive-scale recursive scanner that converts slow Excel files into memory-efficient Parquet format. It resolves cross-market listing issues and utilizes `pd.merge_asof` to guarantee strictly **zero look-ahead bias** when merging accounting data.

### 2. Stylized Facts (`02_data_description_and_summary`)
Proves the extreme sparsity of textual signals (validating the Top/Bottom N sorting methodology) and visualizes the macroeconomic "Trust Bankruptcy" during extreme market crashes (2015, 2018, 2022).

### 3. Portfolio Sorting & ESI Generation (`03_portfolio_sorts`)
Features Object-Oriented sorting engines. We evaluate baseline NLP signals and use conditional double sorts to uncover the "Cheap Talk" hypothesis, leading to the formulation of the **Effective Soothing Index (ESI)**. Features dynamic transaction cost and short-selling friction analyses.

### 4. Asset Pricing Regressions (`04_baseline_predictability`)
Conducts high-frequency Panel OLS regressions with double-clustered standard errors (Petersen, 2009) and Fama-MacBeth robustness checks. Proves that ESI predicts up to 40 days of future Open-to-Close returns, orthogonal to CH4 and q5 factors.

### 5. Mechanism Channels (`05_mechanism`)
Traces the true economic drivers of the ESI alpha:
- **Fundamentals**: Predicts upcoming Standardized Unexpected Earnings (SUE).
- **Microstructure**: Demonstrates ESI predicts institutional "Smart Money" order flows rather than retail "Noise Trader" flows.
- **Corporate Governance**: Shows high-substantiveness ESI mitigates Left-Tail Crash Risk.
