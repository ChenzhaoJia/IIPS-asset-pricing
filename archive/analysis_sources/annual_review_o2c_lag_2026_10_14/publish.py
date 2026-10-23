from pathlib import Path
import json,shutil,hashlib
from prepare import ROOT,PROJECT,digest,save

summary=json.loads((ROOT/'final_scientific_summary.json').read_text())
assert summary['status']=='estimation_and_reported_statistics_validation_complete'
manifest=json.loads((ROOT/'input_manifest.json').read_text())
for entry in manifest.values():assert digest(entry['path'])==entry['sha256']
code=PROJECT/'data/analysis/revision/annual_review_o2c_lag_2026_10_14'
audit=PROJECT/'data/verification/annual_review_o2c_lag_2026-10-14'
work=PROJECT/'data/working/annual_review_o2c_lag_2026-10-14'
note=PROJECT/'drafts/revision/annual_review_o2c_lag_2026-10-14.md'
for target in [code,audit,work,note]:
    assert target.resolve().is_relative_to(PROJECT.resolve())
    assert not target.exists(),'Preserve existing versions: '+str(target)
for target in [code,audit,work]:target.mkdir()
for file in ROOT.iterdir():
    if file.is_file() and file.suffix=='.py':shutil.copy2(file,code/file.name)
    elif file.is_file() and file.suffix=='.parquet':shutil.copy2(file,work/file.name)
    elif file.is_file() and file.suffix in ['.csv','.json','.md','.log']:
        shutil.copy2(file,audit/file.name)
for name in ['regression_models','grouped_regression_models','portfolio_models','portfolio_models_v002']:
    shutil.copytree(ROOT/name,audit/name)
shutil.copy2(ROOT/'RUN_REPORT.md',note)
rq=PROJECT/'research-question.md'
entry='''## 2026-10-14 Annual Review旧稿问题日O2C的五组lag检验

- 用户明确要求以Annual_Review_Chenzhao Jia.pdf旧稿为基础估计Same day、1 day、2 days、3–5 days、>5 days交互及portfolio sorts，只看O2C。本轮保留2010–2024问题日归属与原03/04实现，取原公司问题日队列最大自然日lag，不先施加④单一回复日条件。
- 原q5回归920584，865309可分组，同日100022，占11.56%；原组合ESI输入2553356，其中2386487可分组、同日267767。不能与回复可得日2017–2024的④⑤样本混用。两套原全期ESI尺度分组前冻结，lambda=.5、gamma=5、q=.30、b=.8及原非对称保护保留，未重估组参数。
- 6个交互模型：q5/CH4/raw × 基准控制/加两端tone；q5五组联合p=.1213/.1247，未达5%。30斜率和60差异全保留，后者BH无5%显著。
- ESI五组q5 alpha EW/VW分别4.47/5.28、2.91/3.12、4.12/2.70、3.31/3.07、2.50/5.29 bps；40项跨lag配对alpha差异全部原p>.05，最小.2015。>5日VW相对manager tone有局部BH显著差，完整保存，不概括为普遍优势。
- 原PanelOLS和原排序类与本轮实现核对一致，但未精确复现旧稿印刷值：β=1.7753而旧稿1.77，组合EW/VW毛收益5.3087/5.2570而旧稿5.32/5.35。差异原因未闭合，未凑旧数。问题日含后续回复、未来涨跌停筛选、旧信号日因子及next-record窗口均作为历史回溯局限披露。
- 所有展示ESI/group系数、联合Wald和t/p通过独立复核；控制原单位绝对误差门槛未全通过，失败记录保留，控制每SD效应及t/p通过。278个HAC模型及1080分散日期权重排序核验通过，非全部持仓独立重建。
- 主稿、slides、原数据、分类、旧GPU/R005未改。说明drafts/revision/annual_review_o2c_lag_2026-10-14.md；核验data/verification/annual_review_o2c_lag_2026-10-14/；中间数据data/working/annual_review_o2c_lag_2026-10-14/；新回传ANNUAL_REVIEW_O2C_LAG_20261014_V001.zip。

'''
old=rq.read_text(encoding='utf-8')
assert '## 2026-10-14 Annual Review旧稿问题日O2C的五组lag检验' not in old
shutil.copy2(rq,audit/'research_question_before.md')
heading='# Research Question and Progress\n\n'
new=heading+entry+old[len(heading):] if old.startswith(heading) else entry+old
rq.write_text(new,encoding='utf-8',newline='\n')
save('publish_manifest.json',dict(status='published',code=str(code),audit=str(audit),work=str(work),report=str(note),source_inputs_main_slides_unchanged=True))
print('Published native code, working data, complete results and revision record',flush=True)
