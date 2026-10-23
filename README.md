# IIP sentiment and asset pricing

中国 A 股投资者互动平台（IIP）情绪与资产定价研究。当前指标名称为 **Effective Sentiment Index (ESI)**。

## 当前工作稿与结论边界

- [整合稿 PDF](drafts/manuscript/IIP_Integrated_2026-10-23.pdf) · [LaTeX 入口](drafts/manuscript/main.tex)
- 主文采用年审原程序的已复核 O2C 结果；EW/VW 日毛收益为 5.3087/5.2570 bps，原算术年化为 12.8470%/12.7219%。旧印刷值不再混用。
- 这是问题日期的回溯关联：匹配的后续回复归回提问 cohort；保留原全期尺度、next-record 窗口、原因子日期与未来涨跌停筛选。不能直接当成实时可交易收益。
- 现有公开回复后 C2C 检验单列：完整文本 horse race 的 ESI 与 VW alpha 不显著；真实 Annodt 盈利结果、完整主题结果均保留。
- Qwen3 全量分类已完成，本轮没有重新编码。分类覆盖率不是准确率。
- [反馈逐项处理](docs/revision/feedback_tracker.md) · [复现说明](docs/REPRODUCING.md) · [来源与论点](docs/provenance/claim_evidence.csv)

## 项目结构

```text
data/
  raw/          本地授权原始数据；按互动、财务、交易、因子、补充分类
  processed/    本地冻结 master panel、cohort lag 和回归/组合输入
  results/      可公开的汇总结果、置信区间、p 值和验证差异
  temp/         重建输出；不覆盖接受过的结果
  manifests/    文件哈希、数据可用性和旧 raw 目录清单
notebooks/
  01_data_ingestion/
  02_data_description_and_summary/
  03_portfolio_sorts_and_performance/
  04_baseline_predictability_regressions/
  05_mechanism_fundamentals_and_microstructure/
  06_topic_classification/
  07_response_lag/
  08_manuscript_and_validation/
src/iip/        可复用的原公式、排序、HAC 和双固定效应算法
scripts/        输入重建、复算、图表生成、编译和发布检查
archive/        年审源稿和原程序；不是当前结论或推荐入口
drafts/manuscript/ 当前论文及依赖
docs/           数据口径、反馈、核验和交接
local_private/  原批注 PDF、受限逐行数据与私有完整来源记录（不上传）
build/          编译、渲染及本地依赖（不上传）
```

前五个 notebook 阶段对应旧项目；新加主题、回复间隔、文稿核验三个阶段。Notebook 默认读取汇总结果，重估入口写明且需本地授权数据。旧 notebook 输出已清空，保留在 archive 供程序追溯；其旧解释和绝对路径不作为当前说明。

## 使用

Python 3.12；核心依赖版本见 requirements.txt。

```bash
python -m pip install -r requirements.txt
python -m pip install -e .
python scripts/build_tables.py
python scripts/reproduce_baseline.py --sort   # 需要本地 processed 文件
python scripts/build_figures.py               # 另需 matplotlib
python scripts/compile_manuscript.py          # 需要 TeX Live / TinyTeX + latexmk
```

从完整原始授权数据重建 ingestion 尚需原数据与环境；当前可移植重建从冻结 master panel 和 cohort panel 开始：`python scripts/prepare_original.py`。重建写入 data/temp，不覆盖 accepted 输入。各层复现能力和未决研究任务见 docs/REPRODUCING.md。

## 数据与发布

本仓库为公开仓库。只同步源码、文稿、图片、汇总结果和元数据。CSMAR/CNRDS 原始及公司日面板、问答原文、持仓明细、模型权重、老师原始批注不公开。旧项目原始数据保留原位置，没有迁移或改写。代码许可证不赋予第三方数据的再分发权。

本稿是研究工作版本，不是已完成机制识别或最终投稿认证。不要按显著性调参、删变量、换样本，或用旧更新日 SUE 代替真实公告日检验。
