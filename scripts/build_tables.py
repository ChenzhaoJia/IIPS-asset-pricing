"""Generate active manuscript tables from stored, identified aggregate results."""
from pathlib import Path
import json
import pandas as pd
R=Path(__file__).resolve().parents[1]
D=R/'data/results'; T=R/'drafts/manuscript/tables'

def table(name,caption,label,header,rows,note,align=None):
    n=len(header);align=align or ('l'+'r'*(n-1))
    text='\\begin{table}[H]\n\\centering\\footnotesize\n'
    text+=f'\\caption{{{caption}}}\\label{{{label}}}\n'
    text+='\\begin{threeparttable}\n\\renewcommand{\\arraystretch}{1.12}\n'
    text+=f'\\begin{{tabular*}}{{\\textwidth}}{{@{{\\extracolsep{{\\fill}}}}{align}@{{}}}}\n\\toprule\n'
    text+=' & '.join(header)+r' \\'+'\n\\midrule\n'
    text+='\n'.join(' & '.join(map(str,row))+r' \\' for row in rows)
    text+='\n\\bottomrule\n\\end{tabular*}\n\\begin{tablenoteblock}\n'+note+'\n\\end{tablenoteblock}\n\\end{threeparttable}\n\\end{table}\n'
    (T/name).write_text(text,encoding='utf-8')

def run():
    p=pd.read_csv(D/'annual_review_o2c/portfolio_baselines.csv')
    names={'ESI_sort':'ESI','Investor_Tone':'Investor tone','Manager_Tone':'Manager tone'}
    rows=[]
    for weight in ['EW','VW']:
        for signal in names:
            x=p.loc[p.weight.eq(weight)&p.signal.eq(signal)].iloc[0]
            rows.append([names[signal]+' ('+weight+')',f'{x.mean_bps:.2f} ({x.raw_t:.2f})',f'{x.annualized_return_pct:.2f}',f'{x.sharpe:.2f}',f'{x.CH4_alpha_bps:.2f} ({x.CH4_t:.2f})',f'{x.q5_alpha_bps:.2f} ({x.q5_t:.2f})'])
    table('legacy_portfolios.tex','Historical O2C Portfolio Performance','tab:horse_race',
          ['Signal','Mean (bps)','Annual (\\%)','Sharpe',r'CH4 $\alpha$',r'U.S. q5 $\alpha$'],rows,
          r'Gross long-minus-short returns; 3,642 dates for each row. Parentheses contain HAC(5) $t$ statistics. Up to 50 positive-signal stocks in the upper 30 percent form the long leg; up to 50 negative-signal stocks in the lower 30 percent form the short leg. Both legs must exist. Annualization is the historical arithmetic convention, $242\bar r\times100$, with Sharpe scaled by $\sqrt{242}$. Candidate pools are signal-specific, not a common-stock-pool horse race. Next-record O2C excess returns, future closing-limit exclusions, full-period text scales, and signal-date factors reproduce the original implementation. CH4 is domestic; q5 is the U.S. Global-q series. The intraday outcome and daily factor intervals differ. These are historical diagnostic alphas, not implementable profits. All figures are recomputed values rather than copied PDF numbers.')
    p=pd.read_csv(D/'annual_review_o2c/regression_baselines.csv')
    labels=['U.S. q5 residual','China CH4 residual','Raw O2C excess return']
    table('legacy_regressions.tex','Historical One-Day O2C Regressions','tab:panel_horse_race',
          ['Dependent variable','ESI (bps)',r'$t$','Firm days','Firms'],
          [[label,f'{x.coef_bps:.2f}',f'{x.t:.2f}',f'{x.n:,}',f'{x.firms:,}'] for label,x in zip(labels,p.itertuples())],
          r'Each row is a separate regression with the eleven baseline controls, firm effects, and question-date effects; standard errors are clustered by firm and date. ESI is standardized once using the original full regression pool. Residual outcomes use full-sample firm loadings and original signal-date factors. Controls and outcomes determine each row\textquotesingle s sample; these are not common-sample factor comparisons. Positive one-day associations do not establish independent text information or real-time forecasting. The unverified multi-horizon O2C and Fama--MacBeth tables remain in the historical archive.')
    scales=json.loads((D/'annual_review_o2c/frozen_scales.json').read_text())
    fields=[('Complete text observations','complete_text_n',0),(r'$\bar M$','manager_mean',4),(r'$\sigma_M$','manager_std',4),(r'$Q_I(0.30)$','investor_p30',4),(r'$\sigma_I$','investor_std',4),(r'$0.8\sigma_I$','sigma',4),(r'$\max\log(1+N)$','attention_log_max',4),(r'$\overline{ESI}$','score_mean',4),(r'$\sigma_{ESI}$','score_std',4)]
    table('parameters.tex','Frozen Full-Sample Text Scales','tab:parameters',['Quantity','Regression pool','Portfolio pool'],
          [[label,*[f'{scales[k][field]:,.{digits}f}' for k in ['regression','portfolio']]] for label,field,digits in fields],
          r'The original 2010--2024 analysis pools are retained separately. Regression construction excludes the first six months after listing; portfolio preparation uses its original return and market-capitalization availability rules. These are full-sample distributional scales, not an early training window or externally estimated economic parameters. $\lambda=0.5$, $\gamma=5$, $q=0.30$, and $b=0.8$ remain fixed. No per-lag recalibration is performed. The full-period construction overlaps the evaluation period.')
    dist=pd.read_csv(D/'annual_review_o2c/regression_common_sample_distribution.csv')
    slopes=pd.read_csv(D/'annual_review_o2c/regression_slopes.csv')
    perf=pd.read_csv(D/'annual_review_o2c/portfolio_performance.csv')
    groupnames={'same_day':'Same day','one_day':'1 day','two_days':'2 days','three_to_five':'3--5 days','over_five':'More than 5 days'}
    rows=[]
    for g,label in groupnames.items():
        x=dist.loc[dist.lag_group.eq(g)].iloc[0]
        vals=[]
        for spec in ['baseline_controls','plus_both_tones']:
            z=slopes.loc[slopes.group.eq(g)&slopes.outcome.eq('q5_next_O2C_residual')&slopes.specification.eq(spec)].iloc[0]
            vals.append(f'{z.coef_bps:.2f} ({z.t:.2f})')
        rows.append([label,f'{x.n:,}',f'{x.share_pct:.2f}',*vals])
    table('lag_regressions.tex','Reply Lag Distribution and Historical O2C Slopes','tab:lag_regressions',
          ['Maximum lag','Firm days','Share (\\%)','Baseline','Also both tones'],rows,
          r'The maximum calendar-day interval among recorded replies in each original company-question-date cohort defines the group. All matched replies must have valid nonnegative lags; no single-reply-date restriction is imposed. The common grouped sample is 865,309 firm days, not the 328,695 observations of the separate public-availability diagnostic. Slopes are total ESI slopes in bps per frozen full-regression-pool standard deviation, with $t$ statistics in parentheses. The pooled regression includes group indicators, ESI-by-group terms, eleven controls and firm/date effects; errors are clustered by firm/date. Joint slope-equality $p$ values are 0.1213 and 0.1247 (Holm-adjusted 0.2425 for both).')
    rows=[]
    for g,label in groupnames.items():
        vals=[]
        for w in ['EW','VW']:
            z=perf.loc[perf.group.eq(g)&perf.signal.eq('ESI_sort')&perf.weight.eq(w)&perf.scope.eq('own_signal_dates')].iloc[0]
            vals += [f'{z.q5_alpha_bps:.2f} ({z.q5_t:.2f})',f'{int(z.n):,}']
        rows.append([label,*vals])
    table('lag_portfolios.tex','ESI Portfolios within Reply Lag Groups','tab:lag_portfolios',
          ['Maximum lag',r'EW q5 $\alpha$','Dates',r'VW q5 $\alpha$','Dates'],rows,
          r'The original O2C sorting and frozen portfolio ESI rules apply separately within each maximum-calendar-lag group. Alphas are in bps and HAC(5) $t$ statistics are in parentheses. Dates are own-strategy dates, so a comparison of separate estimates is not a test of their difference. All 40 paired alpha differences across five groups, two weights and two factor benchmarks have unadjusted $p>0.05$ (minimum 0.2015); the complete results are retained in the repository. The U.S. q5 source and historical timing limitations remain applicable.')
    p=pd.read_csv(D/'classifier_benchmark/substantiveness_common_benchmark_summary_2026-09-28.csv')
    table('classifier_benchmark.tex','Reply Substantiveness: Common-Holdout Model Comparison','tab:substantiveness_benchmark',
          ['Model','Macro F1','Balanced acc.','AUC','Brier','ECE'],
          [[x.model,*[f'{getattr(x,v):.3f}' for v in ['macro_f1','balanced_accuracy','roc_auc','brier_score','ece_10_bins']]] for x in p.itertuples()],
          r'The same 402 existing-label test pairs are used for every model. The 1,999 usable labels are split into 1,280 training, 317 validation and 402 test pairs with no normalized reply template shared across partitions. Higher F1, balanced accuracy and AUC, and lower Brier and ECE, indicate better agreement with these labels. Annotator identifiers, a complete labeling protocol, and inter-rater agreement are unavailable; this is not independent semantic ground truth. The original Random Forest score is retained in the return tests, with no selective replacement by BERT predictions.')
    print('Generated seven manuscript tables from aggregate sources.')

if __name__=='__main__':run()
