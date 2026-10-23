"""Reconstruct the cited Annual Review notebook inputs without rewriting sources."""
import os
os.environ['OPENBLAS_NUM_THREADS']='2'
os.environ['OMP_NUM_THREADS']='2'
from pathlib import Path
import gc,hashlib,json,platform,sys,time
import numpy as np,pandas as pd,pyarrow.parquet as pq

ROOT=Path(__file__).resolve().parent
PROJECT=Path(r'D:\draft')
BASE=PROJECT/'data/analysis/iip_asset_pricing 1/data/processed/01_Base_Daily_Panel_Advanced.parquet'
COHORT=PROJECT/'data/working/response_lag_2026-10-10/cohort_lags_verified.parquet'
GROUPS=['same_day','one_day','two_days','three_to_five','over_five']
CONTROL=['Size','BM','ROA','Lev','Illiqd','Dturn','Ret_t_1','Vol_t','Ret_t_30_t_2','Newstone_t_30_t_3','Newsdummy_t_30_t_3']
CH4=['ch4_mktrf','ch4_SMB','ch4_VMG','ch4_PMO']
Q5=['q5_MKT','q5_ME','q5_IA','q5_ROE','q5_EG']

def log(s):print(time.strftime('%H:%M:%S'),s,flush=True)
def save(name,obj):(ROOT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
def digest(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        while b:=f.read(4194304):h.update(b)
    return h.hexdigest()

def esi(d):
    valid=d[['Investor_Tone','Manager_Tone','Substantiveness_ML']].notna().all(axis=1)
    inv=d.loc[valid,'Investor_Tone'];mgr=d.loc[valid,'Manager_Tone']
    log_attn=np.log1p(d.Num_Questions.fillna(0));den=log_attn.max()
    theta=inv.quantile(.30);sigma=inv.std()*.8
    base=d.Investor_Tone*(1+.5*log_attn/den)
    impact=(d.Manager_Tone-mgr.mean())/mgr.std()*d.Substantiveness_ML*np.exp(-((d.Investor_Tone-theta)**2)/(2*sigma**2))
    impact.loc[(d.Investor_Tone>0)&(impact<0)]=0
    score=(base+5.*impact).astype('float32')
    return score,dict(complete_text_n=int(valid.sum()),manager_mean=float(mgr.mean()),manager_std=float(mgr.std()),investor_p30=float(theta),investor_std=float(inv.std()),sigma=float(sigma),attention_log_max=float(den),lambda_attention=.5,gamma_manager=5.,bandwidth_multiplier=.8,asymmetric_truncation=True,score_mean=float(score.mean()),score_std=float(score.std()),scope='Full original notebook pre-group pool, 2010-2024; frozen once before lag classification')

def attach_lag(d,c):
    n=len(d)
    p=d.merge(c,on=['Stkcd','Date'],how='left',validate='one_to_one',sort=False)
    assert len(p)==n
    p['lag_group']=pd.cut(p.calendar_max,[-1,0,1,2,5,np.inf],labels=GROUPS)
    return p

def main():
    assert not (ROOT/'prepared_reg.parquet').exists()
    inputs={'base':BASE,'cohorts':COHORT,'reference_pdf':Path(r'D:\iip_exchange\Annual_Review_Chenzhao Jia.pdf'),
            'portfolio_notebook':PROJECT/'data/analysis/iip_asset_pricing 1/notebooks/03_portfolio sorts_and_performance/03_portfolio_sorts_and_performance.md',
            'regression_notebook':PROJECT/'data/analysis/iip_asset_pricing 1/notebooks/04_baseline_predictability_regressions/04_baseline_predictability_regressions.md',
            'main':PROJECT/'drafts/manuscript/main.tex','slides':PROJECT/'drafts/presentations/meeting_2026-10-15_v003/phd_meeting_3.tex'}
    manifest={k:dict(path=str(p),bytes=p.stat().st_size,sha256=digest(p)) for k,p in inputs.items()}
    assert manifest['base']['sha256']=='a6b0f143dda2c811e2b5f073343c68a87202e9f232d0667c533ba01a66b5cb0d'
    assert manifest['reference_pdf']['sha256']=='59ec782e158bdd89a864e82cfa5c8709c238dd8fed5c89e59dea2e3808204719'
    save('input_manifest.json',manifest)
    save('protocol.json',dict(authorized='2026-10-14 user requests five-group ESI interactions and portfolio sorts based on the cited Annual Review draft, O2C only',
        construction='Original company-question-date aggregates; no move to reply availability date',
        groups=GROUPS,lag_clock='Maximum calendar-date lag among recorded replies within each original company-question-date cohort',
        single_reply_date_restriction=False,same_day_definition='All valid recorded replies in the original cohort share the question calendar date',
        unclassifiable_lag='Retain in all-sample reproduction; exclude from grouped estimates with explicit flow counts',
        invalid_timestamp='Exclude whole cohort from grouped analysis; do not alter its stored scores',
        ESI='lambda .5, gamma 5, q .30, bandwidth .8, original asymmetric protection; preserve separate notebook portfolio and regression full-pool scales',
        group_parameter_reestimation=False,period='2010-2024',horizon=1,
        regression=dict(outcomes=['raw_next_O2C','q5_next_O2C_residual','CH4_next_O2C_residual'],primary='q5 as cited Table 6',
            models=['baseline_controls','plus_both_tones'],fe='common firm and question-date effects',clusters='firm and question-date',controls=CONTROL,
            design='ESI plus four group dummies and four ESI interactions; common controls and FE',
            standardization='Original full regression-pool ESI SD, fixed before grouping; raw baseline controls',
            primary_family='Two q5 joint tests of equality across all five slopes; Holm',other_Wald='4 supplemental raw/CH4 tests, BH',pairwise='All ten group pairs across six specifications; exploratory BH'),
        portfolios=dict(signals=['ESI','Investor_Tone','Manager_Tone'],weights=['EW','VW'],top_n=50,quantiles=[.3,.7],signs='positive long and negative short',
            legacy_sample='No IPO filter in original 03 portfolio notebook; original next-record return availability and next closing-limit status filter preserved',
            scales='Original 03 cleaned pool, frozen before grouping',factor_dates='Original signal-date CH4/q5 mapping preserved for historical replication',
            hac='Original statsmodels HAC(5), observed sequence, no small-sample correction',factors=['CH4','q5'],annualization=242,
            both_legs_required=True,report='All-sample baseline, five lag groups, and unclassified-lag coverage; own and common signal dates',
            group_differences='All ten ESI group pairs, two weights, two factor benchmarks; Holm over 40 paired comparisons',
            tone_differences='ESI minus each tone within five groups, two weights and two benchmarks; BH over 40 comparisons',gross=True),
        limitations=['Retrospective reply information on question dates','Full-period text calibration and outcome residual loadings','Legacy factor dates and next-record windows','Future closing-limit selection in original portfolio rules'],
        protected='Raw inputs, labels, Qwen3, old GPU/R005, manuscript and slides not modified',
        independent_tolerances=dict(coef_bps=1e-4,t=1e-4,p=1e-5),new_manuscript_or_slide_edits=False))
    log('Protocol saved before scores or estimates; loading original panel')
    columns=['Stkcd','Date','Dretwd','OpenPrice','ClosePrice','Rf_Daily','Dsmvtll','LimitStatus','Firm_Age_Ln',
             'Investor_Tone','Manager_Tone','Substantiveness_ML','Num_Questions','TotalResponses',
             'Size','BM','ROA','Lev','Illiqd','Dturn','Newstone_t_30_t_3','Newsdummy_t_30_t_3',*CH4,*Q5]
    d=pd.read_parquet(BASE,columns=columns)
    d.Date=pd.to_datetime(d.Date);d=d.sort_values(['Stkcd','Date']).reset_index(drop=True)
    d.Stkcd=pd.to_numeric(d.Stkcd).astype('int32')
    assert not d.duplicated(['Stkcd','Date']).any()
    factors=d[['Date',*CH4,*Q5]].drop_duplicates('Date').set_index('Date').sort_index()
    factors.to_parquet(ROOT/'factors.parquet')
    grouped=d.groupby('Stkcd',sort=False)
    # Match the original 03 order and arithmetic, then float64 -> float32 conversion.
    d['port_o2c']=np.where(d.OpenPrice.notna()&d.ClosePrice.notna()&d.OpenPrice.gt(0),(d.ClosePrice-d.OpenPrice)/d.OpenPrice,np.nan)
    d['port_next']=grouped.port_o2c.shift(-1)-grouped.Rf_Daily.shift(-1).fillna(0)
    d['Execution_Date']=grouped.Date.shift(-1)
    d['MktCap_B']=grouped.Dsmvtll.ffill(limit=1)/1e6
    d['Next_LimitStatus']=grouped.LimitStatus.shift(-1).fillna(0)
    port=d.loc[d.port_next.notna()&d.MktCap_B.notna()].copy()
    for col in port.select_dtypes(include='float64'):port[col]=port[col].astype('float32')
    port['ESI_sort'],portscale=esi(port)
    port=port.loc[port[['ESI_sort','Investor_Tone','Manager_Tone']].notna().any(axis=1),
                  ['Stkcd','Date','Execution_Date','ESI_sort','Investor_Tone','Manager_Tone','Substantiveness_ML','Num_Questions','TotalResponses','port_next','MktCap_B','Next_LimitStatus']].copy()
    log('Original portfolio ESI scale frozen; reconstructing original regression inputs')
    reg=d.loc[d.Firm_Age_Ln.ge(np.log(.5))].copy().reset_index(drop=True)
    reg['reg_o2c']=np.where(reg.OpenPrice.notna()&reg.ClosePrice.notna()&reg.OpenPrice.gt(0),reg.ClosePrice/reg.OpenPrice-1,np.nan).astype('float32')
    group=reg.groupby('Stkcd',sort=False)
    reg['raw_next_O2C']=(group.reg_o2c.shift(-1)-group.Rf_Daily.shift(-1).fillna(0)).astype('float32')
    reg['Ret_t_1']=group.Dretwd.shift(1).astype('float32')
    reg['Ret_t_30_t_2']=group.Dretwd.transform(lambda v:v.shift(2).rolling(29,min_periods=10).sum()).astype('float32')
    reg['Vol_t']=group.Dretwd.transform(lambda v:v.shift(1).rolling(30,min_periods=10).std()).astype('float32')
    reg['ESI_reg'],regscale=esi(reg)
    reg['ESI_z']=((reg.ESI_reg-reg.ESI_reg.mean())/reg.ESI_reg.std()).astype('float32')
    for c in ['Investor_Tone','Manager_Tone']:
        reg[c+'_z']=((reg[c]-reg[c].mean())/reg[c].std()).astype('float32')
    parameters=dict(portfolio=portscale,regression=regscale,python=platform.python_version(),n_original=len(d),n_regression_IPO_pool=len(reg))
    save('frozen_scales.json',parameters)
    del d;gc.collect()
    for label,xcols in [('q5',Q5),('CH4',CH4)]:
        y=reg.raw_next_O2C.to_numpy(float);x=reg[xcols].to_numpy(float)
        residual=np.full(len(reg),np.nan,dtype='float32')
        for firm,indices in reg.groupby('Stkcd',sort=False).indices.items():
            valid=np.isfinite(y[indices])&np.isfinite(x[indices]).all(1)
            if valid.sum()<30:continue
            ix=indices[valid];X=np.column_stack([np.ones(len(ix)),x[ix]])
            b=np.linalg.lstsq(X,y[ix],rcond=None)[0]
            residual[ix]=(y[ix]-X@b).astype('float32')
        reg[label+'_next_O2C_residual']=residual
        log(label+' original full-firm outcome residuals calculated')
    c=pd.read_parquet(COHORT,columns=['Stkcd','Question_Date','First_Reply_Date','Last_Reply_Date','Reply_Date_Count','TotalResponses','Question_Count_Match','Response_Count_Match','N_Answered','Valid_Lag_N','Invalid_Lag_N'])
    c.Stkcd=pd.to_numeric(c.Stkcd).astype('int32');c['Date']=pd.to_datetime(c.Question_Date)
    c['calendar_max']=(pd.to_datetime(c.Last_Reply_Date).dt.floor('D')-c.Date.dt.floor('D')).dt.days
    c['calendar_min']=(pd.to_datetime(c.First_Reply_Date).dt.floor('D')-c.Date.dt.floor('D')).dt.days
    c['lag_clean']=c.Question_Count_Match&c.Response_Count_Match&c.Valid_Lag_N.gt(0)&c.Invalid_Lag_N.eq(0)&c.N_Answered.eq(c.Valid_Lag_N)&c.calendar_min.ge(0)&c.calendar_max.notna()
    c['single_reply_date']=c.Reply_Date_Count.eq(1)
    c=c[['Stkcd','Date','calendar_max','lag_clean','single_reply_date','N_Answered']]
    assert not c.duplicated(['Stkcd','Date']).any()
    # Preserve the baseline ESI regression pool before imposing any lag validity.
    reg=reg.loc[reg.ESI_z.notna(),['Stkcd','Date','ESI_reg','ESI_z','Investor_Tone_z','Manager_Tone_z',*CONTROL,'raw_next_O2C','q5_next_O2C_residual','CH4_next_O2C_residual']].copy()
    reg=attach_lag(reg,c);port=attach_lag(port,c)
    reg.to_parquet(ROOT/'prepared_reg.parquet',index=False)
    port.to_parquet(ROOT/'prepared_port.parquet',index=False)
    rows=[]
    def counts(pop,pool):
        eligible=pool.loc[pool.lag_clean.fillna(False)]
        for g in GROUPS:
            q=eligible.loc[eligible.lag_group.eq(g)]
            rows.append(dict(population=pop,group=g,n=len(q),denominator=len(eligible),share_pct=100*len(q)/len(eligible),firms=q.Stkcd.nunique(),dates=q.Date.nunique(),multi_reply_date_n=int((~q.single_reply_date).sum())))
    counts('portfolio_ESI_complete_before_legacy_tradability',port.loc[port.ESI_sort.notna()])
    counts('regression_q5_baseline_complete',reg.dropna(subset=['q5_next_O2C_residual','ESI_z',*CONTROL]))
    counts('regression_q5_full_tone_complete',reg.dropna(subset=['q5_next_O2C_residual','ESI_z','Investor_Tone_z','Manager_Tone_z',*CONTROL]))
    pd.DataFrame(rows).to_csv(ROOT/'lag_distribution.csv',index=False)
    flow=[]
    for pop,pool in [('portfolio',port.loc[port.ESI_sort.notna()]),('regression',reg.dropna(subset=['q5_next_O2C_residual','ESI_z',*CONTROL]))]:
        flow.extend([dict(population=pop,stage='legacy_ESI_complete',n=len(pool)),dict(population=pop,stage='clean_lag_classifiable',n=int(pool.lag_clean.fillna(False).sum())),dict(population=pop,stage='excluded_only_from_grouped_tests',n=int((~pool.lag_clean.fillna(False)).sum()))])
    pd.DataFrame(flow).to_csv(ROOT/'sample_flow.csv',index=False)
    save('prepare_status.json',dict(status='complete',parameters_frozen_before_groups=True,n_reg=len(reg),n_port=len(port),source_input_unchanged=digest(BASE)==manifest['base']['sha256']))
    log('Prepared original-date inputs and saved separate lag distributions')

if __name__=='__main__':main()
