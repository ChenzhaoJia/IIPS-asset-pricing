# 年审底稿恢复与增补修订

最新要求覆盖此前“主稿只留已核验结果”的决定：忠实恢复年审 PDF，再补老师反馈解释和主题内容，不以代码审查为由删表或重写结论。

## 两个版本

- drafts/annual_review_pdf_baseline/main.tex：原生 LaTeX 与 PDF 对照恢复；四处 implication/implications 按 PDF 还原。原始数字、图表、结论和案例保留；中文字体重新嵌入。
- drafts/manuscript/main.tex：从完整底稿增补，保留原编号；新增 Figure 4，A6 主题回归、A7 分类覆盖、A8 参数尺度、B1 分类器比较及 D.6 案例。

## 保留及检查

scripts/check_manuscript_preservation.py 检查 17 个原表环境（含续表和变量长表）逐字保留、原结论及案例逐字保留、三张原图引用保留，并检查引用和文献键。布局外层可调整，数字和行不删。

保留 EW/VW 原毛收益 5.32/5.35 bps、q5 alpha、Aggregate Tone、多期限面板/Fama–MacBeth、SUE、OIB、基金持仓、insider、crash、参数/核函数/窗口稳健性和 GUBA。此前复算 CSV 保留供研究对照，本轮不替换印刷数值。

增补 Q&A 配对和日期例子、全样本尺度及固定参数含义、原三项贡献解释、完成的全量分类、C2C 主题回归与检验解释、原文案例和分类器比较。新增结果保留自身口径与不显著结果。q5 来源和 SUE 更新日只作局部澄清。

没有新估计或选择样本、没有重新分类，没有开展广泛代码审查。旧 D:/draft、iip_asset_pricing、GPU/R005 未修改。32 页旧稿在 local_private/rejected_integration_32pages_2026-10-23 和 Git 历史中。旧表生成器改写入 build/recomputation_tables，避免覆盖当前稿。

检查结果见 annual_review_preservation_2026-10-23.json 和 pdf_reconstruction_comparison.json。

最终编译：底稿 57 页、增补稿 79 页。底稿 53 页规范化提取文字与参考 PDF 相同，差异限于中文案例页 48–51 的字体提取映射；实证表页 26–41 全部相同。原图表编号的 19 个标签与底稿一致。增补稿全 79 页已渲染检查，并抽查主题图、主题表、变量表和中英文案例。原 A3 续表通过外层行距调整避免底部拥挤，表格内容未变。原变量长表仍有一个 4.46 pt 的数学变量名宽度提示，视觉检查无内容重叠或裁切。无未定义引用、缺失文献或缺字错误。
