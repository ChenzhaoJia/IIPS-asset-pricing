"""Generate LaTeX tables exclusively from saved, audited statistical output."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
import numpy as np
from mechanism_suite import load, SIG, CTRL, TEXT, FACT
ROOT=Path('D:/draft')
OUT=ROOT/'data/verification/pricing_mechanism_2026-10-11'
TOP=ROOT/'data/verification/full_topic_2026-10-11'
SRC=ROOT/'data/working/full_topic_2026-10-11/accepted_R005_V002'
TEX=ROOT/'drafts/manuscript/tables'
TEX.mkdir(parents=True,exist_ok=True)

def cell(r,c='coef'):
    if r is None:return '--'
    p=r['p'];star='***' if p<.01 else '**' if p<.05 else '*' if p<.1 else ''
    return f"{r[c]:.2f}{star}"
def tcell(r):
    return '--' if r is None else f"({r['t']:.2f})"
def row(label,cells):return label+' & '+' & '.join(cells)+r' \\'
def table(name,caption,label,headers,body,note,continued=False):
    n=len(headers)
    s=[r'\begin{table}[H]',r'\centering',*([r'\ContinuedFloat'] if continued else []),
       r'\caption{'+caption+'}',r'\label{'+label+'}',
       r'\footnotesize',r'\renewcommand{\arraystretch}{1.03}',r'\setlength{\tabcolsep}{3pt}',
       r'\begin{threeparttable}',r'\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}l '+('c '*(n-1))+r'@{}}',
       r'\toprule',row(' '.join([headers[0]]),headers[1:]),r'\midrule',*body,r'\bottomrule',
       r'\end{tabular*}\par',r'\begin{tablenoteblock}',note,r'\end{tablenoteblock}',
       r'\end{threeparttable}',r'\end{table}']
    (TEX/name).write_text('\n'.join(s)+'\n',encoding='utf-8')

def fundamentals():
    d=pd.read_csv(OUT/'actual_announcements/fundamentals_and_confirmation.csv')
    assert d.date_status.eq('ACTUAL_ANNODT').all()
    b=[]
    for y,title in [('SUE','Panel A: Subsequent SUE'),('CAR_CH4','Panel B: Earnings Announcement Return')]:
        b += [r'\multicolumn{4}{@{}l}{\textbf{'+title+r'}} \\',r'\midrule']
        for t,label in [('ESI_z','ESI'),('Investor_Tone_z','Investor Tone'),('Manager_Tone_z','Manager Tone')]:
            rs=[]
            for model in ['ESI','tones','joint']:
                q=d.loc[d.outcome.eq(y)&d.model.eq(model)&d.term.eq(t)]
                rs.append(None if q.empty else q.iloc[0])
            b.extend([row(label,[cell(r) for r in rs]),row('',[tcell(r) for r in rs])])
        b += [r'\midrule',row('Controls and Firm and Date FE',['Yes']*3)]
        rr=[d.loc[d.outcome.eq(y)&d.model.eq(m)].iloc[0] for m in ['ESI','tones','joint']]
        b += [row('Observations',[f"{int(r.n):,}" for r in rr]),
              row(r'Adjusted $R^2$',[f"{r.adjusted_r2:.3f}" for r in rr]),r'\midrule']
    table('public_earnings_announcements.tex','Public Interaction Signals and Subsequent Earnings','tab:fundamental_sue',
        ['Predictor','(1)','(2)','(3)'],b[:-1],
        r'Day $e$ is the first exchange trading day on or after the CSMAR report publication date, Annodt. Missing publication dates and multiple reports for a firm on the same event day are excluded. Different TestPeriod rows have identical earnings inputs and are counted once per report. Standardized signals are averaged over public interaction dates in $[e-30,e-3]$, requiring five signal dates. Each panel uses a common sample across its three columns. Controls include SUE published by $e-31$, the prior window return, and Size, BM, ROA, Lev, Illiqd, Dturn, and firm age available by $e-31$. Panel A uses the original CSMAR SUE. Panel B sums CH4 abnormal returns over $[e-1,e+1]$ in basis points. Loadings use $[e-252,e-31]$ and at least 120 observations. All regressions include firm and event date effects. Standard errors are clustered by firm and event date. ***, **, and * denote significance at 1\%, 5\%, and 10\%. Intraday announcement times and analyst forecasts are unavailable.')

def paths():
    d=pd.read_csv(OUT/'return_path_regressions.csv')
    ys=['pre20','available_day','post1_5','post6_20','post21_60']
    note=r'Day $a$ is the first trading day strictly after the last reply in a question cohort. Returns use the full exchange calendar and require observed total returns throughout each window. Coefficients are in basis points per historical standard deviation of ESI. Returns after $a$ begin at its close. Day $a$ uses its whole daily return. Prior returns and day $a$ use firm characteristics and prior media controls but no trading controls measured on $a$. Later windows use the baseline controls. Both tones enter jointly in the second specification. The full text specification also includes question volume, substantiveness, text lengths, and similarity. All models include firm and date effects and errors clustered by firm and date. Panel B is an attrition diagnostic selected on complete future return windows, not an implementable strategy. ***, **, and * denote significance at 1\%, 5\%, and 10\%. Confidence intervals and adjusted multiple comparison probabilities are retained in the replication output.'
    for sample,title in [('window_available','Panel A: Available Observations in Each Window'),
                         ('common_all_windows','Panel B: Common Complete Window Sample')]:
        b = [r'\multicolumn{6}{@{}l}{\textbf{'+title+r'}} \\',r'\midrule']
        for m,title2 in [('ESI','ESI with controls'),('joint','ESI with both tones'),('full_text','ESI with full text controls')]:
            rs=[]
            for y in ys:
                q=d.loc[d['sample'].eq(sample)&d.model.eq(m)&d.outcome.eq(y)&d.term.eq('ESI_z')]
                rs.append(None if q.empty else q.iloc[0])
            b += [row(title2,[cell(r) for r in rs]),row('',[tcell(r) for r in rs]),
                  row(r'Adjusted $R^2$',['--' if r is None else f'{r.adjusted_r2:.3f}' for r in rs]),
                  row('Observations',['--' if r is None else f'{int(r.n):,}' for r in rs]),r'\addlinespace']
        suffix='a' if sample=='window_available' else 'b'
        label='tab:public_return_paths' if suffix=='a' else 'tab:public_return_paths_continued'
        table('public_return_paths_'+suffix+'.tex','Return Associations Around Public Reply Availability',label,
          ['ESI Specification','Pre 20 Days','Day $a$','Days 1 to 5','Days 6 to 20','Days 21 to 60'],b,note,
          continued=(suffix=='b'))
    (TEX/'public_return_paths.tex').write_text(
        '\\input{tables/public_return_paths_a.tex}\n\\clearpage\n\\input{tables/public_return_paths_b.tex}\n',encoding='utf-8')

def risks():
    p=load()
    beta=pd.read_parquet(ROOT/'data/working/pricing_mechanism_2026-10-11/lagged_CH4_betas.parquet')
    p=p.merge(beta,on=['Stkcd','Date'],how='left',validate='one_to_one')
    guard=['C2C_1_1',*SIG,*['beta_'+k for k in FACT],
           *[c+'_z' for c in CTRL],*[c+'_z' for c in TEXT]]
    p=p.dropna(subset=list(dict.fromkeys(guard)))
    summary=pd.read_csv(OUT/'risk_characteristic_fama_macbeth.csv')
    fits=[]
    for m in summary.model.unique():
        daily=pd.read_csv(OUT/f'fmb_daily_{m}.csv',parse_dates=['Date'])
        x=[k for k in daily if k not in ['Date','N','const']]
        rs=[]
        for date,g in p.dropna(subset=['C2C_1_1',*x]).groupby('Date'):
            rec=daily.loc[daily.Date.eq(date)]
            if rec.empty:continue
            rec=rec.iloc[0]
            pred=rec['const']+g[x].to_numpy()@rec[x].to_numpy(float)
            y=g.C2C_1_1.to_numpy()
            assert len(y)==int(rec.N)
            rss=np.sum((y-pred)**2);tss=np.sum((y-y.mean())**2)
            rs.append(1-(rss/tss)*(len(y)-1)/(len(y)-len(x)-1))
        fits.append({'model':m,'average_adjusted_r2':np.mean(rs),'n_dates':len(rs)})
    fit=pd.DataFrame(fits);fit.to_csv(OUT/'risk_fmb_fit_statistics.csv',index=False)
    b=[r'\multicolumn{5}{@{}l}{\textbf{Panel A: Daily Fama and MacBeth Regressions}} \\',r'\midrule']
    models=['risk_only','risk_characteristics','risk_ESI_characteristics','risk_ESI_full_text']
    for t,label in [('ESI_z','ESI'),('Investor_Tone_z','Investor Tone'),('Manager_Tone_z','Manager Tone'),
                    ('beta_ch4_mktrf',r'Market $\beta$'),('beta_ch4_SMB',r'Size $\beta$'),
                    ('beta_ch4_VMG',r'Value $\beta$'),('beta_ch4_PMO',r'Profitability $\beta$')]:
        rs=[]
        for m in models:
            q=summary.loc[summary.model.eq(m)&summary.term.eq(t)]
            rs.append(None if q.empty else q.iloc[0])
        b += [row(label,[cell(r) for r in rs]),row('',[tcell(r) for r in rs])]
    b += [r'\midrule',row('Firm Controls',['No','Yes','Yes','Yes']),row('Competing Text Features',['No','No','No','Yes']),
          row('Firm Days',[f'{int(summary.loc[summary.model.eq(m)].iloc[0].n_firm_days):,}' for m in models]),
          row('Cross Sections',[f'{int(summary.loc[summary.model.eq(m)].iloc[0].n_dates):,}' for m in models]),
          row(r'Average Adjusted $R^2$',[f'{fit.loc[fit.model.eq(m)].iloc[0].average_adjusted_r2:.3f}' for m in models])]
    table('risk_exposures.tex','Risk Exposures and the Interaction Characteristic','tab:risk_exposures',
          ['Predictor','(1)','(2)','(3)','(4)'],b,
          r'Factor loadings use up to 252 prior trading days and at least 120 complete observations ending in the previous month. The outcome is the next close to close excess return after public reply availability. Each date uses a cross section with at least 30 observations and full column rank. The table reports average slopes in basis points. Controls and competing text features follow the baseline horse race. Average adjusted $R^2$ averages the estimable daily regressions. HAC standard errors use five exchange trading lags. A bootstrap resampling 199 calendar month blocks gives an ESI interval of [0.31, 2.00] in column (3) and [$-1.67$, 1.95] in column (4). These intervals do not correct all error from estimating factor loadings. ESI is a characteristic here, not an estimated risk price of an ESI factor. ***, **, and * denote significance at 1\%, 5\%, and 10\%.')
    d=pd.read_csv(OUT/'risk_conditioned_portfolios.csv')
    b=[]
    for rule,title in [('unconditional','Panel A: Unconditional Signal Terciles'),('beta_and_size','Panel B: Within Size and Market Beta Groups')]:
        b += [r'\multicolumn{4}{@{}l}{\textbf{'+title+r'}} \\',r'\midrule']
        for measure,name in [('alpha_bps',r'CH4 $\alpha$ (bps)'),('t',''),('n','Return Dates'),('adjusted_r2',r'Adjusted $R^2$')]:
            vals=[]
            for s in ['ESI_z','Investor_Tone_z','Manager_Tone_z']:
                r=d.loc[d.rule.eq(rule)&d.signal.eq(s)&d.target.eq('spread')].iloc[0]
                if measure=='alpha_bps':v=cell(r,'alpha_bps')
                elif measure=='t':v=tcell(r)
                elif measure=='n':v=f'{int(r.n):,}'
                else:v=f'{r.adjusted_r2:.3f}'
                vals.append(v)
            b.append(row(name,vals))
        b += [r'\midrule']
    table('risk_conditional_sorts.tex','Signal Portfolios Conditional on Size and Risk Exposure','tab:risk_conditional_sorts',
          ['Measure','ESI','Investor Tone','Manager Tone'],b[:-1],
          r'The sample contains firms with complete text features and previously estimated CH4 loadings after public reply availability. Panel A compares the upper and lower signal terciles. Panel B first assigns stocks to three size groups and three market beta groups. Cells require at least nine stocks. Within each cell, equal weights form upper and lower signal terciles. Daily spreads average across eligible cells. Both panels use the same 1,453 dates and close to close returns. CH4 factors cover the same holding day. Gross alpha regressions use HAC standard errors with five exchange trading lags. These portfolios differ from the baseline extreme stock selection and do not include trading costs. Individual leg results and confidence intervals are retained in the replication output. ***, **, and * denote significance at 1\%, 5\%, and 10\%.')

def topics():
    d=pd.read_csv(TOP/'classification_coverage_verified.csv')
    states=['assigned','low_confidence','generic_template_only','needs_context','empty']
    b=[]
    for s in states:
        vals=[]
        for side in ['question','reply']:
            q=d.loc[d.side.eq(side)&d.topic_state.eq(s)]
            n=0 if q.empty else int(q.iloc[0].n)
            vals.extend([f'{n:,}',f'{n/5836158*100:.2f}\\%'])
        b.append(row({'assigned':'Assigned Content','low_confidence':'Low Score','generic_template_only':'Generic Template','needs_context':'Requires Context','empty':'Empty Text'}[s],vals))
    table('full_topic_coverage.tex','Full Archive Classification Coverage','tab:full_topic_coverage',
          ['Classification State','Question N','Question Share','Reply N','Reply Share'],b,
          r'The denominator is 5,836,158 original questions or replies. Assigned content requires an eligible text and a largest classifier score of at least 0.50. Scores are not calibrated accuracy probabilities. Low scores retain a candidate but are not forced into any of the 19 themes. Reply status distinguishes content, generic templates, context dependent replies, and empty texts. Training and development labels are assistant judgments, not independent human gold labels. Classification does not change the sentiment or substantiveness measures in ESI.')
    d=pd.read_csv(TOP/'topic_slope_heterogeneity.csv')
    tax=json.loads((SRC/'task/docs/taxonomy_19_content.json').read_text(encoding='utf-8-sig'))
    lab={x['code']:x['paper_label'].replace('-',' ') for x in tax['content']}
    lab[0]='Unclassified or Low Score'
    b=[]
    for k in sorted(d.topic_code.unique()):
        qs=[d.loc[d.topic_code.eq(k)&d.model.eq(m)].iloc[0] for m in ['baseline','joint_tones']]
        b.append(row(lab[k],[f'{qs[0].coef_bps:.2f} ({qs[0].t:.2f})',f'{qs[1].coef_bps:.2f} ({qs[1].t:.2f})',
                              f'{qs[1].p_bh:.3f}',f'{int(qs[1].topic_n):,}']))
    w=pd.read_csv(TOP/'topic_joint_wald.csv')
    b.extend([r'\midrule',row('Joint Slope Equality $p$',[f'{w.iloc[0].p:.3f}',f'{w.iloc[1].p:.3f}','--','--']),
        row(r'Adjusted $R^2$',[f'{w.iloc[0].adjusted_r2:.3f}',f'{w.iloc[1].adjusted_r2:.3f}','--','--']),
        row('Total Observations',[f'{int(w.iloc[0].n):,}',f'{int(w.iloc[1].n):,}','--','--'])])
    table('full_topic_heterogeneity.tex','Exploratory Return Slopes Across Interaction Topics','tab:full_topic_heterogeneity',
          ['Dominant Question Content','ESI and Controls','Also Both Tones','BH $p$','Firm Days'],b,
          r'Questions are assigned to 19 fixed content themes and an explicit unclassified category. The dominant category at a firm and availability date is the largest count, including unclassified records. Coefficients are total ESI slopes in basis points per historical standard deviation, not differences from the unclassified reference. Models include category indicators, ESI interactions, baseline controls, and firm and date effects. Errors are clustered by firm and date. The last regression also includes both textual tones. BH probabilities adjust across all topic slopes in that regression. The joint Wald test compares topic slopes rather than counting individually significant estimates. Labels come from assistant supervision and the analysis is exploratory.')
    g=pd.read_csv(TOP/'generic_reply_interaction.csv')
    b=[]
    for term,label in [('ESI_z','ESI'),('Generic_Reply_Share','Generic Reply Share'),
                       ('ESI_x_Generic',r'ESI $\times$ Generic Reply Share')]:
        rs=[g.loc[g.model.eq(m)&g.term.eq(term)].iloc[0] for m in ['baseline','joint_tones']]
        b += [row(label,[cell(r) for r in rs]),row('',[tcell(r) for r in rs])]
    rs=[g.loc[g.model.eq(m)].iloc[0] for m in ['baseline','joint_tones']]
    b += [r'\midrule',row('Controls and Firm and Date FE',['Yes','Yes']),
          row('Both Textual Tones',['No','Yes']),row('Observations',[f'{int(r.n):,}' for r in rs]),
          row(r'Adjusted $R^2$',[f'{r.adjusted_r2:.3f}' for r in rs])]
    table('generic_reply_heterogeneity.tex','Generic Replies and the ESI Return Association','tab:generic_reply_heterogeneity',
          ['Predictor','(1)','(2)'],b,
          r'Generic reply share is the number of replies assigned to the generic template status divided by all original replies in the availability cohort. The outcome is the next close to close excess return after public reply availability. ESI is standardized using the historical calibration scale. Coefficients are in basis points. Firm and date effects and the baseline controls enter both specifications. Standard errors are clustered by firm and date. Assistant supervision does not establish that a generic reply is deliberately evasive. ***, **, and * denote significance at 1\%, 5\%, and 10\%.')

if __name__=='__main__':
    for stage in sys.argv[1:]:globals()[stage]()
