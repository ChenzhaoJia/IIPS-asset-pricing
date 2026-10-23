# 两轮反馈处理清单（2026-10-23）

本文是当前整合稿的处理记录，不把撤下旧分析等同于完成其重估。原始批注只保存在 local_private。

## 年审六条

| ID | 反馈主题 | 当前处理 | 状态 |
|---|---|---|---|
| AR-01 | 完整文本 horse race | 附录 A1 保留现有共同样本 C2C 全模型及不显著 ESI；主文说明其不同校准。年审原尺度完整 horse race 尚待同口径估计。 | 部分完成 |
| AR-02 | 参数解释与分布 | Section 3.2、Table 1、Figures 1–3：全原池分布、两套尺度、固定常数与代码非对称项；不虚称最优或预注册。旧网格归档。 | 文字与分布完成；敏感性重核待办 |
| AR-03 | Q&A 日期与匹配 | Section 3.1 的 Day1/Day3 例子；Section 4.3 最大自然日 lag 分布、交互与组合；明确 C2C 不是只改变日期。 | 完成当前证据整合 |
| AR-04 | Topic modelling | 全量 19 主题/5 性质 Figure 4、完整 Table 7、公式、BH 与联合检验；不重新分类。 | 完成；独立人工语义检验待办 |
| AR-05 | RF/BERT/LLM 比较 | 附录 B / Table A3 同一 402 对 holdout；保留 production RF，不混用更优 BERT 打分。 | 完成已有比较；人工标签质量待办 |
| AR-06 | 贡献 | Introduction 三项具体贡献对应构建、比较口径、内容解释；删除超出证据的机制与稳定优势断言。 | 完成 |

## September 38 条文字意见

| ID | 意见摘要 | 整合稿处理与位置 | 状态 |
|---|---|---|---|
| SEP-01 | 首次定义 ESI | Abstract 首次定义 ESI，不使用未解释的 q5 alpha 简称。 | 完成 |
| SEP-02 | 解释风险调整术语 | Abstract 首次定义 ESI，不使用未解释的 q5 alpha 简称。 | 完成 |
| SEP-03 | 强化互动研究动机 | Introduction 研究问题、制度背景、可支持结果及三项贡献逐段对齐。 | 完成 |
| SEP-04 | 连接中国市场制度与信息/压力解释 | Introduction 研究问题、制度背景、可支持结果及三项贡献逐段对齐。 | 完成 |
| SEP-05 | 引言 alpha 术语 | Introduction 研究问题、制度背景、可支持结果及三项贡献逐段对齐。 | 完成 |
| SEP-06 | 具体说明贡献 | Introduction 研究问题、制度背景、可支持结果及三项贡献逐段对齐。 | 完成 |
| SEP-07 | 主数据与辅助数据分开 | Section 3.1 分开来源、输入池、日期问题和 availability；因子来源移到 4.1。 | 完成 |
| SEP-08 | 精简常识性缺失筛选 | Section 3.1 分开来源、输入池、日期问题和 availability；因子来源移到 4.1。 | 完成 |
| SEP-09 | 因子说明放在结果规格 | Section 3.1 分开来源、输入池、日期问题和 availability；因子来源移到 4.1。 | 完成 |
| SEP-10 | 明确互动日与缺失 tone | Section 3.1 分开来源、输入池、日期问题和 availability；因子来源移到 4.1。 | 完成 |
| SEP-11 | 先解释回复时点问题 | Section 3.1 分开来源、输入池、日期问题和 availability；因子来源移到 4.1。 | 完成 |
| SEP-12 | 重排数据段逻辑 | Section 3.1 分开来源、输入池、日期问题和 availability；因子来源移到 4.1。 | 完成 |
| SEP-13 | ESI 先给总流程 | Section 3.2、Figure 1 流程、参数公式、Table 1 与 Figures 2–3；使用原全样本尺度。 | 完成 |
| SEP-14 | 用公式说明参数 | Section 3.2、Figure 1 流程、参数公式、Table 1 与 Figures 2–3；使用原全样本尺度。 | 完成 |
| SEP-15 | 变量按用途分组 | Table A4 按文本/基准/补充用途排序；3.3 解释控制目的，保留真实字段口径。 | 完成 |
| SEP-16 | 解释特殊控制目的 | Table A4 按文本/基准/补充用途排序；3.3 解释控制目的，保留真实字段口径。 | 完成 |
| SEP-17 | 描述统计紧随构建 | Section 3.2、Figure 1 流程、参数公式、Table 1 与 Figures 2–3；使用原全样本尺度。 | 完成 |
| SEP-18 | 提供国内 FF3 对照 | Appendix A2 保留已有国内 FF3，正文明确其为 C2C 补充；不重命名美国 q5。 | 完成限定范围 |
| SEP-19 | 表格 Panel 导航 | Section 4 及 Appendix A 表文统一，生成表取复算 CSV；不再宣称原 O2C 增量 R²，C2C 完整表保留。 | 完成 |
| SEP-20 | EW 文字与数值一致 | Section 4 及 Appendix A 表文统一，生成表取复算 CSV；不再宣称原 O2C 增量 R²，C2C 完整表保留。 | 完成 |
| SEP-21 | 替换生僻措辞 | Section 4 及 Appendix A 表文统一，生成表取复算 CSV；不再宣称原 O2C 增量 R²，C2C 完整表保留。 | 完成 |
| SEP-22 | 增量拟合度及占位符 | Section 4 及 Appendix A 表文统一，生成表取复算 CSV；不再宣称原 O2C 增量 R²，C2C 完整表保留。 | 完成 |
| SEP-23 | 避免回归段跳回旧组合表 | Section 4 及 Appendix A 表文统一，生成表取复算 CSV；不再宣称原 O2C 增量 R²，C2C 完整表保留。 | 完成 |
| SEP-24 | 简化长句 | Section 4 及 Appendix A 表文统一，生成表取复算 CSV；不再宣称原 O2C 增量 R²，C2C 完整表保留。 | 完成 |
| SEP-25 | 交易规模不等同账户类别 | 旧 OIB/insider/crash 表按用户决定归档；Appendix D 保留定义与解释限制。对应数字和窗口需在恢复该分析时逐项重核。 | 归档，研究复核待办 |
| SEP-26 | 公式引导标点 | Section 5.2 与 Table 6 使用真实 Annodt 控制和窗口；现用公式标点核对。 | 完成 |
| SEP-27 | 盈利控制说明准确 | Section 5.2 与 Table 6 使用真实 Annodt 控制和窗口；现用公式标点核对。 | 完成 |
| SEP-28 | 公式结束标点 | Section 5.2 与 Table 6 使用真实 Annodt 控制和窗口；现用公式标点核对。 | 完成 |
| SEP-29 | OIB 一日与五日窗口 | 旧 OIB/insider/crash 表按用户决定归档；Appendix D 保留定义与解释限制。对应数字和窗口需在恢复该分析时逐项重核。 | 归档，研究复核待办 |
| SEP-30 | OIB 控制说明 | 旧 OIB/insider/crash 表按用户决定归档；Appendix D 保留定义与解释限制。对应数字和窗口需在恢复该分析时逐项重核。 | 归档，研究复核待办 |
| SEP-31 | Difference 提前定义 | 旧 OIB/insider/crash 表按用户决定归档；Appendix D 保留定义与解释限制。对应数字和窗口需在恢复该分析时逐项重核。 | 归档，研究复核待办 |
| SEP-32 | 统一 Large/Small 命名 | 旧 OIB/insider/crash 表按用户决定归档；Appendix D 保留定义与解释限制。对应数字和窗口需在恢复该分析时逐项重核。 | 归档，研究复核待办 |
| SEP-33 | 修正不存在的基金 Panel | 旧 OIB/insider/crash 表按用户决定归档；Appendix D 保留定义与解释限制。对应数字和窗口需在恢复该分析时逐项重核。 | 归档，研究复核待办 |
| SEP-34 | OIB 结果非流水账 | 旧 OIB/insider/crash 表按用户决定归档；Appendix D 保留定义与解释限制。对应数字和窗口需在恢复该分析时逐项重核。 | 归档，研究复核待办 |
| SEP-35 | 列号与实际表结构一致 | 旧 OIB/insider/crash 表按用户决定归档；Appendix D 保留定义与解释限制。对应数字和窗口需在恢复该分析时逐项重核。 | 归档，研究复核待办 |
| SEP-36 | insider 数字对齐 | 旧 OIB/insider/crash 表按用户决定归档；Appendix D 保留定义与解释限制。对应数字和窗口需在恢复该分析时逐项重核。 | 归档，研究复核待办 |
| SEP-37 | insider 解释关注交互差异 | 旧 OIB/insider/crash 表按用户决定归档；Appendix D 保留定义与解释限制。对应数字和窗口需在恢复该分析时逐项重核。 | 归档，研究复核待办 |
| SEP-38 | crash 文表一致 | 旧 OIB/insider/crash 表按用户决定归档；Appendix D 保留定义与解释限制。对应数字和窗口需在恢复该分析时逐项重核。 | 归档，研究复核待办 |

15 处高亮作为相关文字意见的定位材料，不额外计作 15 个已解决研究问题。当前没有宣称“所有老师反馈都已实证完成”。
