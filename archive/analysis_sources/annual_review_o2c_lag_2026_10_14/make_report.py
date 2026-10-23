from pathlib import Path
import json
import pandas as pd
from prepare import ROOT,GROUPS,save,digest

LABEL=dict(zip(GROUPS,['Same day','1 day','2 days','3–5 days','More than 5 days']))
r=pd.read_csv(ROOT/'regression_slopes.csv')
w=pd.read_csv(ROOT/'regression_joint_tests.csv')
p=pd.read_csv(ROOT/'portfolio_performance.csv')
d=pd.read_csv(ROOT/'portfolio_paired_differences.csv')
distribution=pd.read_csv(ROOT/'regression_common_sample_distribution.csv').set_index('lag_group').reindex(GROUPS)
reg_validation=json.loads((ROOT/'regression_validation.json').read_text())
port_validation=json.loads((ROOT/'portfolio_validation.json').read_text())
assert reg_validation['status']=='reported_statistics_passed_with_raw_control_unit_precision_note'
assert port_validation['status']=='passed'
text='''# Annual Review 旧稿：问题日 ESI × 最大自然日回复间隔，O2C 检验

完成日期：2026-10-14。用户明确要求以D:/iip_exchange/Annual_Review_Chenzhao Jia.pdf为基础，估计Same day、1 day、2 days、3–5 days、More than 5 days交互项回归及portfolio sorts，只看O2C。

本轮沿用该稿的旧notebook实现，不将问题日移到回复可得日，不施加④单一回复日筛选，不改变分类、ESI权重或组别切点。此处2010–2024全问题日样本不同于之前2017–2024回复可得日诊断；同日组样本数不能直接互换。没有修改main.tex或slides。

## 1. 先看回复间隔分布

L为同一公司原问题日队列内，最后记录回复的自然日期减问题自然日期。这相当于取该队列已记录回复的最大自然日间隔；不是平均时长，也不是24小时分箱。L=0要求该队列有效已记录回复全部在问题自然日。跨日组允许同一个队列的回复分散在多个自然日。未回复不能记成0；无法验证非负有效时间或计数一致性的整个队列不进入分组。

旧q5一日回归基准有920,584个公司日，865,309个可有效分组，55,275个仅留在未分组基准，不把缺失lag强行归类。分组回归的六个模型均使用同一个865,309公司日样本，覆盖3,593家公司、2,704个问题日期。

| 最大自然日回复间隔 | 回归公司日 | 占可分组回归样本 |
|---|---:|---:|
'''
for g,row in distribution.iterrows():text+=f'| {LABEL[g]} | {int(row.n):,} | {row.share_pct:.2f}% |\n'
text+='''
该回归样本L均值10.62日、中位数3日、P90为21日、最大3,313日。极长正间隔保留，业务含义尚未独立确认，不依据收益截尾。原代码输入已经聚合，部分未回复问题仍可能包含在问题端输入；分组只根据有记录回复的时间。

旧组合ESI完整输入2,553,356个公司日，其中2,386,487个可分组、166,869个仅留在未分组基准。这个分母未施加旧组合的下一期涨跌停筛选，也不要求回归控制齐全，所以不能当作回归分母。L均值12.90日、中位数3日、P90为22日、最大3,390日。

| 最大自然日回复间隔 | 组合ESI输入公司日 | 占可分组组合输入 |
|---|---:|---:|
'''
pdst=pd.read_csv(ROOT/'lag_distribution.csv').query("population=='portfolio_ESI_complete_before_legacy_tradability'").set_index('group').reindex(GROUPS)
for g,row in pdst.iterrows():text+=f'| {LABEL[g]} | {int(row.n):,} | {row.share_pct:.2f}% |\n'
text+='''
## 2. 基准复算与旧稿的差异

旧稿Table4和Table6对应原始03/04 notebooks，均读取01_Base_Daily_Panel_Advanced.parquet。复算保持原数据SHA256、日期归属、全期文本尺度、lambda=.5、gamma=5、q=.30、b=.8以及源代码中的非对称保护截断。组合未施加IPO筛选，回归施加上市至少半年筛选，这是原notebooks自身的差别。两套ESI尺度分别冻结在各自原全期输入中，不在lag组内重估。旧稿公式未明确列出源代码中的保护截断，本轮据源代码保留并记录。

| 基准 | 旧稿印刷值 | 当前原代码复算 |
|---|---:|---:|
| q5一日回归ESI β（bps） | 1.77 | 1.775299（按两位为1.78） |
| 对应t | 5.48 | 5.476057 |
| 回归n | 920,584 | 920,584 |
| ESI EW日毛收益（bps） | 5.32 | 5.308694 |
| ESI VW日毛收益（bps） | 5.35 | 5.256965 |
| ESI EW q5 alpha（bps） | 5.43 | 5.419728 |
| ESI VW q5 alpha（bps） | 5.50 | 5.404658 |

未完全复现旧稿印刷数值，不声称精确数值复现。原PanelOLS与本轮加速回归一致；原PortfolioSorter的选择与收益实现与本轮排序在当前运行时一致。排序类为适应pandas3恢复groupby.apply移除的Date列，仅跳过未使用的turnover计算，不改变股票选择、权重或收益。印刷值差异的完整原因仍未闭合，不通过调参、删变量或换样本去凑旧数。首轮逐位展示校验失败和复核记录保留，本轮分组结果以固定原实现的复算值为基准。

## 3. 交互项回归

以同日为省略组，估计：

R(i,t+1) = firm_FE(i) + date_FE(t) + β0 Z(i,t)
           + Σ[g≠same] ηg Dg(i,t)
           + Σ[g≠same] δg Z(i,t)Dg(i,t)
           + θ′X(i,t) + ε(i,t+1).

Z是按原04 notebook全期回归输入标准化、分组前冻结的ESI。X保留原11项基准控制。第二规格再加入Investor Tone和Manager Tone，使用同一完整样本，不把它称作包含所有文本特征的full horse race。

表中同日总斜率为β0，其余组为β0+δg；单位bps/原全期ESI标准差。括号内是公司与问题日双向聚类t。收益沿用旧代码的下一条公司交易记录O2C超额收益；q5和CH4异常收益由原全期公司OLS残差构造，不是实时可得的滚动beta。

### q5主口径

| 最大lag | ESI+基准控制 β（t） | 再加两端tone β（t） |
|---|---:|---:|
'''
for g in GROUPS:
    a=r.loc[r.outcome.eq('q5_next_O2C_residual')&r.specification.eq('baseline_controls')&r.group.eq(g)].iloc[0]
    b=r.loc[r.outcome.eq('q5_next_O2C_residual')&r.specification.eq('plus_both_tones')&r.group.eq(g)].iloc[0]
    text+=f'| {LABEL[g]} | {a.coef_bps:.2f} ({a.t:.2f}) | {b.coef_bps:.2f} ({b.t:.2f}) |\n'
text+='''
| q5规格 | 五组总斜率相等原始p | 两项主联合检验Holm p |
|---|---:|---:|
'''
for row in w.loc[w.family.eq('primary')].itertuples():text+=f'| {row.specification} | {row.p:.4f} | {row.p_adjusted:.4f} |\n'
text+='''
同日与1日组点估计较大，但五组相等的两个主检验均未达到5%。不能因为某组有星号、另一个没有就认定它们显著不同。全部60项回归两两差异经统一BH后也没有达到5%，最低BH p约0.1913。

CH4对照的联合p为0.1016和0.1043；原始超额收益为0.0932和0.0961。它们没有在5%拒绝五组相等。全部30个斜率、95%区间、名义p及组内BH，以及60项差异完整保留在CSV。

## 4. 按lag分组的O2C portfolio sorts

沿用旧03 notebook：在每组每个问题日计算30/70分位点，正分做多、负分做空，每腿最多50只；EW等权，VW使用原MktCap_B。每个组分别排序，不按lag重新计算ESI参数。下表使用ESI自己的完整组合日期，与旧稿主表的口径一致；不同组有效日期不同，正式比较用配对日期。

q5 alpha单位bps/日，括号内原HAC(5) t，均为未扣交易与借券成本的历史毛组合。附CSV另列原始收益、年化、Sharpe、CH4/q5 alpha、CI、p、日期数及腿宽；同时保留Investor Tone和Manager Tone对照及三信号共同日期。

| 最大lag | EW q5 alpha（t） | VW q5 alpha（t） | ESI组合日期数 | 平均每腿股票数（多/空） |
|---|---:|---:|---:|---:|
'''
for g in GROUPS:
    a=p.loc[p.group.eq(g)&p.signal.eq('ESI_sort')&p.weight.eq('EW')&p.scope.eq('own_signal_dates')].iloc[0]
    b=p.loc[p.group.eq(g)&p.signal.eq('ESI_sort')&p.weight.eq('VW')&p.scope.eq('own_signal_dates')].iloc[0]
    text+=f'| {LABEL[g]} | {a.q5_alpha_bps:.2f} ({a.q5_t:.2f}) | {b.q5_alpha_bps:.2f} ({b.q5_t:.2f}) | {int(a.n):,} | {a.average_long_n:.1f}/{a.average_short_n:.1f} |\n'
text+='''
同日EW/VW、3–5日EW、>5日VW的q5 alpha名义显著，但排序没有形成严格单调的回复速度关系。40项跨lag配对alpha差异（10组对×2权重×2基准）原始p全部>0.05，最小为0.2015，Holm p全部为1。

补充40项ESI减单边tone的配对比较中，>5日VW相对Manager Tone在q5和CH4下经BH后显著，差值分别5.874和5.931 bps，BH p均0.0274；其他比较经BH未达5%。这是局部探索结果，不能概括为ESI在所有lag组稳定优于两端tone。

## 5. 历史口径和解释限制

- 原问题日ESI可包含后续才公开的回复，最终lag同样可能在问题日未知。本轮是回溯关联诊断，不能解释为当时可交易的快慢回复组合或加快回复的因果效果。
- 原组合规则以未来收盘涨跌停状态筛选股票，并在读入下一条记录收益之后计算分位数；下一条公司记录不保证为严格下一市场交易日。因子仍按原信号日匹配，不是实际持有日。这些旧规则为本轮历史规格保留并披露，未静默修正，也不称为无前视基准。
- 原组合与回归的全期文本校准、IPO规则及因子调整不同；因此不能把两套尺度混成一份统一参数，或直接与之前回复可得日的④⑤比较。
- 逐条旧情绪分数到公司日聚合的完整血缘仍未闭合；本轮直接沿用权威聚合输入，不重新训练/编码Qwen3，不据原始文本生成新的tone。

## 6. 数值复核

9个回归（3个未分组基准及6个交互）用独立普通交替去均值、normal equations与聚类influence scores核验。所有展示ESI及组别系数最大差1.01e-9 bps，全部t最大差1.64e-9、p最大差9.14e-10，组总斜率与联合Wald按原容差通过。

控制变量原单位的绝对系数校验没有全部通过1e-4 bps门槛，最大差0.0009582 bps，失败标记与两次记录保留。极小单位控制变量的每1SD经济效应最大差3.47e-9 bps，全部t/p通过；没有把原单位失败改写成全通过，也未调整ESI系数的核验容差或任何估计结果。

全部278个组合/差异HAC模型通过独立显式Bartlett协方差复核，1080条固定分散日期×权重排序/收益检查通过，最大收益差7.45e-5 bps。这不是7859854条全部持仓的独立重建。

原数据、参数来源、主稿、slides、分类与旧GPU/R005目录未改。所有输入哈希及原代码/原稿版本记录保存。

## 文件与重放

主要CSV：regression_slopes、regression_joint_tests、regression_pairwise_differences、portfolio_performance、portfolio_paired_differences、lag_distribution、sample_flow。prepared_reg/port保留完整本轮输入；daily_portfolios和selected_holdings保留组合与全部所选股票。protocol、frozen_scales、基准差异、独立验证及全部模型保留。

本轮原生报告：D:/draft/drafts/revision/annual_review_o2c_lag_2026-10-14.md。
本轮代码：D:/draft/data/analysis/revision/annual_review_o2c_lag_2026_10_14/。
本轮结果与核验：D:/draft/data/verification/annual_review_o2c_lag_2026-10-14/。
本轮中间数据：D:/draft/data/working/annual_review_o2c_lag_2026-10-14/。
完整回传：D:/iip_exchange/from_gpu/ANNUAL_REVIEW_O2C_LAG_20261014_V001.zip。

代码和模型均保留，不覆盖原结果重跑。重新执行需复制到新的工作目录，并保留相同原始输入；初始印刷值校验未通过的脚本也保留，后续版本使用原PanelOLS/原排序类一致性作为重建验证，明确不声称印刷值精确复现。
'''
(ROOT/'RUN_REPORT.md').write_text(text,encoding='utf-8')
protected=json.loads((ROOT/'input_manifest.json').read_text())
for item in protected.values():assert digest(item['path'])==item['sha256'],item['path']
save('final_scientific_summary.json',dict(status='estimation_and_reported_statistics_validation_complete',regression_models=9,grouped_models=6,portfolio_models=278,
    regression_common_n=865309,portfolio_classifiable_input_n=2386487,main_and_slides_unchanged=True,exact_publication_values_reproduced=False,
    source_implementations_verified=True,regression_raw_control_absolute_checks_all_passed=False,
    regression_primary_Wald_p=w.loc[w.family.eq('primary'),'p'].tolist(),portfolio_group_difference_min_raw_p=float(d.loc[d.family.eq('lag_differences'),'p'].min()),
    group_distribution_before_results=True,all_null_results_retained=True))
print('Full report saved and protected hashes verified',flush=True)
