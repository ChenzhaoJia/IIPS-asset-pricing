# IIP sentiment and asset pricing

中国 A 股投资者互动平台情绪与资产定价研究。当前工作稿以 **Annual Review 全文为基础增补**，保留其原有结果、表格与结论。

## 论文入口

- [增补修订稿 PDF](drafts/manuscript/Annual_Review_Additive_Revision_2026-10-23.pdf) · [主稿 LaTeX](drafts/manuscript/main.tex)
- [年审底稿恢复 PDF](drafts/annual_review_pdf_baseline/Annual_Review_Reconstructed.pdf) · [底稿 LaTeX](drafts/annual_review_pdf_baseline/main.tex)
- [具体改动](docs/revision/ANNUAL_REVIEW_RESTORATION_2026-10-23.md) · [两轮反馈清单](docs/revision/feedback_tracker.md) · [原表保留检查](docs/revision/annual_review_preservation_2026-10-23.json)

最新用户决定取代此前 32 页精简整合稿：原主表 1–9、附录 A1–A5（含续表）、变量定义、原案例与结论保留，数字沿用年审 PDF。新增参数和 Q&A 匹配解释、Figure 4 主题分类、完整主题回归、覆盖率及主题案例。没有新估回归、调参或重做 Qwen 分类。

原主结果是问题日期的 O2C，现有主题回归作为公开后 C2C 补充，明确区分样本和校准。两端文本分别在匹配的提问 cohort 内聚合，迟到回复归回提问日期。参数尺度用全原样本，非 2010–2018 训练期。保留历史表并不把更新日 SUE 改称真实公告日检验；q5 的美国来源已说明。

## 项目结构

```text
data/
  raw/          本地授权原始数据（互动、财务、交易、因子、补充）
  processed/    本地冻结面板及原回归/组合输入，不上传
  results/      汇总统计与原程序复算对照；不会自动替换论文印刷值
  temp/         重建输出
  manifests/    数据来源和文件哈希
notebooks/
  01_data_ingestion/
  02_data_description_and_summary/
  03_portfolio_sorts_and_performance/
  04_baseline_predictability_regressions/
  05_mechanism_fundamentals_and_microstructure/
  06_topic_classification/
  07_response_lag/
  08_manuscript_and_validation/
src/iip/        原公式、排序及统计算法
scripts/        重建、复算对照、文稿保留检查和编译
drafts/
  annual_review_pdf_baseline/ 忠实恢复底稿
  manuscript/                当前增补稿
archive/        历史来源
docs/           口径、反馈、来源和交接
local_private/  原批注、受限数据及被替代稿件，不上传
build/          编译、渲染、比较输出及本地依赖，不上传
```

## 使用

```bash
python scripts/check_manuscript_preservation.py
python scripts/compile_manuscript.py --baseline
python scripts/compile_manuscript.py
```

编译需要 XeLaTeX、latexmk、BibTeX 和 ctex 等宏包。可通过 IIP_TEX_BIN 指定已有 TeX 目录。Python 研究环境见 requirements.txt；各层复现能力见 [说明](docs/REPRODUCING.md)。Notebook 08 只检查原稿保留与编译入口。build_tables.py 输出为 build/recomputation_tables 中的研究对照，不覆盖主稿。

## 数据与发布

公开仓库只含文稿、源码、图片、汇总结果和元数据。CSMAR/CNRDS 原始及公司日面板、完整问答语料、持仓明细、模型权重、老师原批注不公开。论文已有及本次授权增加的精选案例属于附录内容，不代表开放原始语料授权。旧项目目录未改动。
