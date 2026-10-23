"""Frozen mechanism diagnostics. No return-selected parameters or specifications."""
from pathlib import Path
import sys, os, json, hashlib, time, argparse
os.environ['OPENBLAS_NUM_THREADS']='2'
os.environ['OMP_NUM_THREADS']='2'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import chi2
from statsmodels.stats.multitest import multipletests
import response_lag_pricing_suite as old
from fast_panel_ch4 import fit_panel
from reply_date_joint_horse_race import CONTROL_COLUMNS, CORE_TEXT_COLUMNS

ROOT=Path('D:/draft')
OUT=ROOT/'data/verification/pricing_mechanism_2026-10-11'
WORK=ROOT/'data/working/pricing_mechanism_2026-10-11'
CTRL=CONTROL_COLUMNS
TEXT=CORE_TEXT_COLUMNS
FACT=old.FACT
SIG=['ESI_z','Investor_Tone_z','Manager_Tone_z']

def log(x): print(time.strftime('%H:%M:%S'),x,flush=True)
def save(x,name): x.to_csv(OUT/name,index=False)
def bh(d,groups):
    d['p_bh']=d.groupby(groups,dropna=False).p.transform(lambda p:multipletests(p.fillna(1),method='fdr_bh')[1])
    return d
def load():
    p=old.panel()
    s=json.loads((old.OUT/'regression_scaling.json').read_text())
    p['ESI_z']=(p.ESI-s['ESI_mean'])/s['ESI_std']
    # Historical scales for tone from the frozen calibration.
    params=old.parameters()
    p['Manager_Tone_z']=(p.Manager_Tone-params.manager_mean)/params.manager_std
    p['Investor_Tone_z']=(p.Investor_Tone-params.investor_p30)/params.investor_std
    for c in set(CTRL+TEXT)-{'Investor_Tone','Manager_Tone'}:
        p[c+'_z']=(p[c]-p[c].mean())/p[c].std()
    return p
def result(r,term,unit=1):
    ci=r.conf_int().loc[term]
    return dict(term=term,coef=float(r.params[term]*unit),t=float(r.tstats[term]),p=float(r.pvalues[term]),
                ci_low=float(ci.iloc[0]*unit),ci_high=float(ci.iloc[1]*unit),n=int(r.nobs),
                adjusted_r2=float(1-(1-r.rsquared_inclusive)*(r.nobs-1)/r.df_resid))
def models(d,y,controls,unit=1):
    specs={'ESI':['ESI_z'],'tones':['Investor_Tone_z','Manager_Tone_z'],
           'joint':['ESI_z','Investor_Tone_z','Manager_Tone_z']}
    common=d.dropna(subset=[y,*SIG,*controls]).replace([np.inf,-np.inf],np.nan).dropna(subset=[y,*SIG,*controls])
    rows=[]
    for name,x in specs.items():
        r,_=fit_panel(common,y,x+controls)
        rows.extend(dict(model=name,outcome=y,**result(r,t,unit)) for t in x)
    return rows

def segment(a,i,j,lo,hi):
    """Full observed calendar interval, compounded excess total return."""
    y=np.full(len(i),np.nan)
    ok=(j+lo>=0)&(j+hi<len(a['dates']))
    ii=np.where(ok)[0]
    rr=np.stack([a['ret'][i[ii],j[ii]+k] for k in range(lo,hi+1)],axis=1)
    rf=np.stack([a['rf'][j[ii]+k] for k in range(lo,hi+1)],axis=1)
    good=np.isfinite(rr).all(1)&np.isfinite(rf).all(1)&(rr>=-1).all(1)
    y[ii[good]]=np.prod(1+rr[good],axis=1)-np.prod(1+rf[good],axis=1)
    return y

def paths():
    p=load();a=old.market_arrays();i=p.firm_idx.to_numpy();j=p.date_idx.to_numpy()
    wins={'pre20':(-20,-1),'available_day':(0,0),'post1_5':(1,5),'post6_20':(6,20),'post21_60':(21,60)}
    for name,(lo,hi) in wins.items():p[name]=segment(a,i,j,lo,hi)
    controls=[c+'_z' for c in CTRL]
    text=[c+'_z' for c in TEXT]
    common=p.dropna(subset=[*wins,*SIG,*controls,*text])
    rows=[]
    for sample,d in [('window_available',p),('common_all_windows',common)]:
        for y in wins:
            if y not in ('available_day','pre20'):
                rs=models(d,y,controls,1e4)
                rows.extend(dict(sample=sample,**r) for r in rs)
                full=d.dropna(subset=[y,*SIG,*controls,*text])
                r,_=fit_panel(full,y,['ESI_z',*text,*controls])
                rows.append(dict(sample=sample,model='full_text',outcome=y,**result(r,'ESI_z',1e4)))
            else:
                # No day-a trading control for the contemporaneous/pre-event outcome.
                rows.extend(dict(sample=sample,**r) for r in models(d,y,
                       [c+'_z' for c in ['Size','BM','ROA','Lev','Newstone_t_30_t_3','Newsdummy_t_30_t_3']],1e4))
    save(bh(pd.DataFrame(rows),['sample','model']),'return_path_regressions.csv')
    save(pd.DataFrame([{'window':k,'available_n':int(p[k].notna().sum()),'common_all_windows_n':len(common)} for k in wins]),'path_sample_flow.csv')
    p[['Stkcd','Date',*wins,*SIG]].to_parquet(WORK/'event_path_outcomes.parquet',index=False)
    log('Return path regressions completed')

def beta_at(a,firm,at,lo=-251,hi=0):
    st=max(0,at+lo);en=at+hi+1
    if en<=st:return None
    yy=a['ret'][firm,st:en]-a['rf'][st:en]
    xx=a['factors'][st:en]
    good=np.isfinite(yy)&np.isfinite(xx).all(1)
    if good.sum()<120:return None
    design=np.column_stack([np.ones(good.sum()),xx[good]])
    if np.linalg.matrix_rank(design)<5:return None
    co=np.linalg.lstsq(design,yy[good],rcond=None)[0]
    return co

def fundamentals(earnings_file=None):
    p=load();a=old.market_arrays()
    cols=['Stkcd','Date','SUE','AdjEPS','Size','BM','ROA','Lev','Illiqd','Dturn','Firm_Age_Ln']
    base=pd.read_parquet(old.BASE,columns=cols).sort_values(['Stkcd','Date'])
    base['Stkcd']=pd.to_numeric(base.Stkcd).astype('int32')
    if earnings_file:
        path=Path(earnings_file)
        ea=pd.read_parquet(path) if path.suffix=='.parquet' else pd.read_csv(path)
        assert {'Stkcd','Annodt','SUE'}.issubset(ea)
        ea['Date']=pd.to_datetime(ea.Annodt)
        if 'TestPeriod' in ea:ea=ea.loc[ea.TestPeriod.eq(6)]
        state='ACTUAL_ANNOUNCEMENT_DATES'
    else:
        change=base.groupby('Stkcd')[['SUE','AdjEPS']].diff().abs().gt(0).any(axis=1)
        ea=base.loc[change & base.SUE.notna(),['Stkcd','Date','SUE','AdjEPS']].copy()
        state='UPDATE_DATE_PROXY_NOT_ACTUAL_ANNOUNCEMENT'
    ea['Stkcd']=pd.to_numeric(ea.Stkcd).astype('int32')
    ea=ea.sort_values(['Stkcd','Date']).drop_duplicates(['Stkcd','Date'])
    ea['Lag_SUE']=ea.groupby('Stkcd').SUE.shift(1)
    ea['date_idx']=np.searchsorted(a['dates'],ea.Date.to_numpy('datetime64[ns]'))
    ea=ea.loc[ea.date_idx.lt(len(a['dates']))].copy()
    ea['Date']=pd.to_datetime(a['dates'][ea.date_idx])
    ea=ea.loc[ea.Date.between(old.START,old.END)].copy()
    ea['firm_idx']=np.searchsorted(a['firms'],ea.Stkcd.to_numpy())
    records=[]
    controls=['Size','BM','ROA','Lev','Illiqd','Dturn','Firm_Age_Ln']
    pg={k:g.sort_values('date_idx') for k,g in p.groupby('Stkcd')}
    bg={k:g.sort_values('Date') for k,g in base.groupby('Stkcd')}
    for n,(firm,g) in enumerate(ea.groupby('Stkcd')):
        if firm not in pg:continue
        z=pg[firm];b=bg[firm]
        zi=z.date_idx.to_numpy();bd=b.Date.to_numpy('datetime64[ns]')
        for row in g.itertuples():
            j=int(row.date_idx);i=int(row.firm_idx)
            low=np.searchsorted(zi,j-30,'left');high=np.searchsorted(zi,j-3,'right')
            window=z.iloc[low:high]
            if len(window)<5:continue
            control_date=a['dates'][max(0,j-31)]
            bi=np.searchsorted(bd,control_date,'right')-1
            if bi<0:continue
            rec={'Stkcd':firm,'Date':row.Date,'SUE':row.SUE,'Lag_SUE':row.Lag_SUE,
                 'window_events':len(window),'Ret_pre':segment(a,np.array([i]),np.array([j]),-30,-3)[0]}
            rec.update({c:float(window[c].mean()) for c in SIG})
            rec.update({c:float(b.iloc[bi][c]) for c in controls})
            rec['CAR_market']=segment(a,np.array([i]),np.array([j]),-1,1)[0]-sum(a['factors'][j-1:j+2,0])
            bet=beta_at(a,i,j,lo=-252,hi=-31)
            if bet is None:rec['CAR_CH4']=np.nan
            else:
                rr=a['ret'][i,j-1:j+2]-a['rf'][j-1:j+2]
                ff=a['factors'][j-1:j+2]
                rec['CAR_CH4']=float(np.sum(rr-bet[0]-ff@bet[1:])) if np.isfinite(rr).all() and np.isfinite(ff).all() else np.nan
            records.append(rec)
        if n%500==0:log(f'Earnings proxy processed firms {n}')
    d=pd.DataFrame(records)
    c=['Lag_SUE','Ret_pre',*controls]
    rows=[]
    for y in ['SUE','CAR_CH4','CAR_market']:
        rows.extend(dict(date_status=state,**r) for r in models(d,y,c,1e4 if y.startswith('CAR') else 1))
    save(bh(pd.DataFrame(rows),['outcome','model']),'fundamentals_and_confirmation.csv')
    d.to_parquet(WORK/'earnings_signal_events.parquet',index=False)
    old.save_json(OUT/'fundamental_data_status.json',dict(date_status=state,events=len(ea),with_signal_window=len(d),
       forecast_error_status='NOT_ESTIMATED_ANALYST_FORECASTS_AND_ANNOUNCEMENT_EPS_MISSING',
       announcement_file=earnings_file,first_firm_rows_not_treated_as_announcements=True,
       minimum_preannouncement_public_signal_days=5))
    log('Fundamental joint regressions and update-day CAR diagnostic completed')

def risks():
    p=load();a=old.market_arrays()
    months=pd.DatetimeIndex(a['dates']).to_period('M')
    # A beta at an event in month m only uses observations through month m-1.
    start=np.r_[0,np.where(months[1:]!=months[:-1])[0]+1]
    mindex=np.searchsorted(start,p.date_idx.to_numpy(),'right')-1
    p['beta_end']=start[mindex]-1
    records=[]
    for n,(key,g) in enumerate(p.groupby(['firm_idx','beta_end'])):
        i,end=map(int,key)
        b=beta_at(a,i,end)
        if b is not None:records.append({'firm_idx':i,'beta_end':end,**{f'beta_{k}':float(v) for k,v in zip(FACT,b[1:])}})
        if n%25000==0:log(f'Lagged beta groups {n}')
    b=pd.DataFrame(records)
    p=p.merge(b,on=['firm_idx','beta_end'],how='left',validate='many_to_one')
    beta=[f'beta_{k}' for k in FACT]
    cc=[c+'_z' for c in CTRL]
    tt=[c+'_z' for c in TEXT]
    specs={'risk_only':beta,'risk_characteristics':beta+cc,
           'risk_ESI_characteristics':beta+['ESI_z']+cc,
           'risk_ESI_full_text':beta+['ESI_z']+tt+cc}
    guard=list(dict.fromkeys(['C2C_1_1',*SIG,*beta,*cc,*tt]))
    sample=p.dropna(subset=guard)
    fmb=[]
    for name,x in specs.items():
        coefficients=[]
        for date,g in sample.groupby('Date'):
            if len(g)<max(30,len(x)+10):continue
            xx=sm.add_constant(g[x],has_constant='add').to_numpy(float)
            if np.linalg.matrix_rank(xx)<xx.shape[1]:continue
            co=np.linalg.lstsq(xx,g.C2C_1_1.to_numpy(float),rcond=None)[0]
            coefficients.append({'Date':date,**dict(zip(['const',*x],co)),'N':len(g)})
        cd=pd.DataFrame(coefficients).set_index('Date')
        cd.to_csv(OUT/f'fmb_daily_{name}.csv')
        rng=np.random.default_rng(20261011)
        mon=cd.index.to_period('M')
        groups=[cd.loc[mon==v,x].to_numpy() for v in mon.unique()]
        boot=np.array([np.vstack([groups[k] for k in rng.integers(0,len(groups),len(groups))]).mean(0) for _ in range(199)])
        for j,term in enumerate(x):
            h=old.hac(cd[term],lag=5)
            ci=h.conf_int().loc['const']
            fmb.append(dict(model=name,term=term,coef=h.params['const']*1e4,t=h.tvalues['const'],p=h.pvalues['const'],
              ci_low=ci.iloc[0]*1e4,ci_high=ci.iloc[1]*1e4,n_dates=len(cd),n_firm_days=int(cd.N.sum()),
              month_boot_ci_low=np.quantile(boot[:,j],.025)*1e4,month_boot_ci_high=np.quantile(boot[:,j],.975)*1e4))
        log(f'Risk FMB completed {name}')
    save(bh(pd.DataFrame(fmb),['model']),'risk_characteristic_fama_macbeth.csv')
    pool=[]
    for date,g in sample.groupby('Date'):
        if len(g)<50:continue
        g=g.copy()
        g['risk_bin']=pd.qcut(g.beta_ch4_mktrf.rank(method='first'),3,labels=False)
        g['size_bin']=pd.qcut(g.Size.rank(method='first'),3,labels=False)
        for rule in ['unconditional','beta_and_size']:
            cells=[g] if rule=='unconditional' else [h for _,h in g.groupby(['risk_bin','size_bin']) if len(h)>=9]
            for sig in SIG:
                dif=[];lh=[];sh=[]
                for h in cells:
                    ranks=h[sig].rank(pct=True)
                    l=h.loc[ranks.ge(2/3),'C2C_1_1'].mean();s=h.loc[ranks.le(1/3),'C2C_1_1'].mean()
                    if np.isfinite(l) and np.isfinite(s):dif.append(l-s);lh.append(l);sh.append(s)
                if dif:pool.append({'Date':date,'rule':rule,'signal':sig,'spread':np.mean(dif),'long':np.mean(lh),'short':np.mean(sh),'cells':len(dif)})
    pools=pd.DataFrame(pool)
    pools.to_parquet(WORK/'risk_conditioned_spreads.parquet',index=False)
    rows=[]
    for (rule,sig),g in pools.groupby(['rule','signal']):
        for target in ['long','short','spread']:
            h=old.hac(g.set_index('Date')[target],old.factors()[FACT],lag=5)
            rows.append(dict(rule=rule,signal=sig,target=target,**old.hacrow(h)))
    save(old.correct(pd.DataFrame(rows),['rule','target']),'risk_conditioned_portfolios.csv')
    p[['Stkcd','Date',*beta]].to_parquet(WORK/'lagged_CH4_betas.parquet',index=False)
    log('Risk exposure versus characteristic diagnostics completed')

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('stage',choices=['paths','fundamentals','risks','unit'])
    ap.add_argument('--earnings-file')
    args=ap.parse_args()
    OUT.mkdir(parents=True,exist_ok=True);WORK.mkdir(parents=True,exist_ok=True)
    old.save_json(OUT/f'status_{args.stage}.json',dict(state='running',pid=os.getpid(),started=time.strftime('%Y-%m-%dT%H:%M:%S')))
    if args.stage=='unit':
        a={'dates':np.arange(5),'ret':np.array([[.01,.02,.03,np.nan,.05]]),'rf':np.zeros(5)}
        assert abs(segment(a,np.array([0]),np.array([0]),1,2)[0]-(1.02*1.03-1))<1e-12
        assert np.isnan(segment(a,np.array([0]),np.array([0]),1,3)[0])
        assert np.isnan(segment(a,np.array([0]),np.array([0]),-1,1)[0])
        log('Compounding, missing-day, and boundary unit checks passed')
    elif args.stage=='fundamentals':fundamentals(args.earnings_file)
    else:globals()[args.stage]()
    old.save_json(OUT/f'status_{args.stage}.json',dict(state='completed',pid=os.getpid(),finished=time.strftime('%Y-%m-%dT%H:%M:%S'),
       code_sha256=old.digest(Path(__file__)),fixed_parameters=old.parameters().to_dict()))

if __name__=='__main__':main()
