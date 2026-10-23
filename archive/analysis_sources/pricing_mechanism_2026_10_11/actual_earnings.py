"""Actual CSMAR announcement dates, with the previously frozen event design.

Raw archives and earlier proxy diagnostics remain unchanged. No outcome-guided
specification search. Distinct TestPeriod rows contain identical SUE inputs.
"""
from pathlib import Path
import os,sys,json,hashlib,zipfile,time,argparse,platform
os.environ['OPENBLAS_NUM_THREADS']='2'
os.environ['OMP_NUM_THREADS']='2'
import numpy as np
import pandas as pd
from mechanism_suite import load,segment,beta_at,models,bh,SIG
import response_lag_pricing_suite as old

ROOT=Path('D:/draft')
NAME='股票标准化未预期盈余表(半年)132045203.zip'
SOURCE=ROOT/'data/working/gpu_exchange/from_gpu'/NAME
WORK=ROOT/'data/working/pricing_mechanism_2026-10-11/actual_announcements'
OUT=ROOT/'data/verification/pricing_mechanism_2026-10-11/actual_announcements'
EXPECTED='6f25d884b4f3cf470b4088ac28a21e21a74eb19f45ee98d88e2a9d0b27d05f71'

def write(name,obj):
    old.save_json(OUT/name,obj)
def log(s):
    print(time.strftime('%H:%M:%S'),s,flush=True)

def rounding_consistency(sue,sigma,unexpected):
    """Product consistency for three independently rounded six-decimal fields."""
    x,y,z=map(lambda v:np.asarray(v,dtype=float),(sue,sigma,unexpected))
    error=np.abs(x*y-z)
    bound=0.5e-6*(1+np.abs(x)+np.abs(y))+0.25e-12
    valid=np.isfinite(x)&np.isfinite(y)&np.isfinite(z)&(y>0)
    return valid & (error<=bound+1e-12),error,bound

def prepare():
    manifest=json.loads(Path(str(SOURCE)+'.MANIFEST.json').read_text(encoding='utf-8-sig'))
    ready=json.loads(Path(str(SOURCE)+'.READY.json').read_text(encoding='utf-8-sig'))
    assert old.digest(SOURCE)==EXPECTED==manifest['zip_sha256']
    assert EXPECTED in Path(str(SOURCE)+'.sha256').read_text(encoding='utf-8-sig')
    assert EXPECTED in json.dumps(ready)
    assert SOURCE.stat().st_size==manifest['zip_bytes']
    with zipfile.ZipFile(SOURCE) as z:
        assert z.testzip() is None
        expected={m['sha256']:m for m in manifest['members']}
        verified=[]
        for m in z.infolist():
            p=Path(m.filename)
            assert not p.is_absolute() and '..' not in p.parts
            payload=z.read(m)
            h=hashlib.sha256(payload).hexdigest()
            assert h in expected and len(payload)==expected[h]['bytes']
            verified.append(h)
        assert set(verified)==set(expected)
        d=pd.read_csv(z.open('BF_Stock_SUE.csv'),dtype={'Stkcd':str})
        description=z.read('BF_Stock_SUE[DES][csv].txt').decode('utf-8-sig')
    assert len(d)==764703 and {'Stkcd','EndDate','Annodt','TestPeriod','SUE','AdjEPS'}.issubset(d)
    assert not d.duplicated(['Stkcd','EndDate','TestPeriod']).any()
    keys=['Stkcd','EndDate']
    fields=['Annodt','SUE','AdjEPS','Un_EPS','Sigma','EPS']
    differing=d.groupby(keys)[fields].nunique(dropna=False).gt(1).sum().to_dict()
    assert not any(differing.values()),differing
    # TestPeriod is a forward return evaluation horizon, not an earnings input.
    # Collapse only after proving that all earnings/date fields are identical.
    e=d.sort_values(keys+['TestPeriod'],kind='stable').drop_duplicates(keys).copy()
    e['Stkcd']=pd.to_numeric(e.Stkcd).astype('int32')
    for c in ['EndDate','Annodt']:
        e[c]=pd.to_datetime(e[c],errors='coerce')
    assert not (e.Annodt.notna() & e.Annodt.lt(e.EndDate)).any()
    consistent,formula_error,formula_bound=rounding_consistency(e.SUE,e.Sigma,e.Un_EPS)
    assert consistent.all(),f'{(~consistent).sum()} reports exceed the joint rounding bound'
    e[['Stkcd','EndDate','Annodt','SUE','AdjEPS','Un_EPS','Sigma','EPS','MarketType']].to_parquet(
        WORK/'unique_reports.parquet',index=False)
    (WORK/'field_description.txt').write_text(description,encoding='utf-8')
    # Preserve an immutable local copy in addition to the synchronization inbox.
    archived=WORK/NAME
    if archived.exists():
        assert old.digest(archived)==EXPECTED
    else:
        import shutil
        shutil.copyfile(SOURCE,archived)
        assert old.digest(archived)==EXPECTED
    write('receipt_audit.json',dict(state='ORIGINAL_ANNODT_FIELDS_VERIFIED',
        source=str(SOURCE),archive_sha256=EXPECTED,archive_bytes=SOURCE.stat().st_size,
        raw_rows=len(d),distinct_reports=len(e),distinct_stocks=int(e.Stkcd.nunique()),
        raw_missing_Annodt=int(d.Annodt.isna().sum()),
        distinct_report_missing_Annodt=int(e.Annodt.isna().sum()),
        missing_dates_imputed=False,member_hashes_verified=len(verified),
        identical_earnings_fields_across_TestPeriod=differing,
        formula_rounding_check=dict(reports_checked=len(e),outside_bound=int((~consistent).sum()),
            maximum_bound_ratio=float(np.max(formula_error/formula_bound)),
            bound='0.5e-6*(1+abs(SUE)+abs(Sigma))+0.25e-12',
            original_SUE_values_preserved=True,
            retry_authorization='Explicit user approval received on 2026-10-11'),
        testperiod_role='Forward return evaluation horizon. All distinct reports retained once.',
        annodt_definition='Report publication date, from the included field description.',
        teststart_used=False,analyst_forecast_data_present=False,
        vintage_warning='Archived accounting series. Historical point-in-time revisions and Sigma construction not independently reconstructed.'))
    log('Original dates, fields, all member hashes and report-level collapse verified')

def analyze():
    p=load()
    a=old.market_arrays()
    e=pd.read_parquet(WORK/'unique_reports.parquet')
    flow={'raw_distinct_reports':len(e),'missing_Annodt':int(e.Annodt.isna().sum())}
    e=e.loc[e.Annodt.notna() & e.MarketType.isin([1,4,16,32])].copy()
    flow['nonmissing_SZ_SH_A_share_reports']=len(e)
    # Event center is the first exchange session on or after the actual date.
    # Time of day is unavailable. No attempt to call the day an exact instant.
    e['date_idx']=np.searchsorted(a['dates'],e.Annodt.to_numpy('datetime64[ns]'),side='left')
    e=e.loc[e.date_idx.lt(len(a['dates'])) & e.Stkcd.isin(a['firms'])].copy()
    e['Date']=pd.to_datetime(a['dates'][e.date_idx])
    e['firm_idx']=np.searchsorted(a['firms'],e.Stkcd.to_numpy())
    ambiguous=e.duplicated(['Stkcd','Date'],keep=False)
    flow['ambiguous_same_trading_day_reports_excluded']=int(ambiguous.sum())
    e.loc[ambiguous].to_csv(OUT/'ambiguous_event_dates_excluded.csv',index=False)
    e=e.loc[~ambiguous].sort_values(['Stkcd','Date']).copy()
    histories={firm:g for firm,g in e.groupby('Stkcd')}
    e=e.loc[e.Date.between(old.START,old.END)].copy()
    flow['announcement_candidates_2017_2024']=len(e)
    e[['Stkcd','EndDate','Annodt','Date','SUE']].to_parquet(WORK/'announcement_candidates.parquet',index=False)
    controls=['Size','BM','ROA','Lev','Illiqd','Dturn','Firm_Age_Ln']
    base=pd.read_parquet(old.BASE,columns=['Stkcd','Date',*controls]).sort_values(['Stkcd','Date'])
    base['Stkcd']=pd.to_numeric(base.Stkcd).astype('int32')
    pg={firm:g.sort_values('date_idx') for firm,g in p.groupby('Stkcd')}
    bg={firm:g for firm,g in base.groupby('Stkcd')}
    rows=[]
    for n,(firm,g) in enumerate(e.groupby('Stkcd')):
        if firm not in pg or firm not in bg:
            continue
        z=pg[firm];b=bg[firm];hist=histories[firm]
        zi=z.date_idx.to_numpy();bd=b.Date.to_numpy('datetime64[ns]')
        for q in g.itertuples():
            j=int(q.date_idx);i=int(q.firm_idx)
            if j<252 or j+1>=len(a['dates']):
                continue
            window=z.iloc[np.searchsorted(zi,j-30,'left'):np.searchsorted(zi,j-3,'right')]
            if len(window)<5:
                continue
            anchor=pd.Timestamp(a['dates'][j-31])
            bi=np.searchsorted(bd,np.datetime64(anchor),'right')-1
            if bi<0:
                continue
            earlier=hist.loc[hist.Annodt.le(anchor)]
            lag=np.nan if earlier.empty else float(earlier.iloc[-1].SUE)
            assert pd.Timestamp(window.Date.max())<q.Annodt
            rec={'Stkcd':firm,'Date':q.Date,'Annodt':q.Annodt,'EndDate':q.EndDate,
                 'SUE':q.SUE,'Lag_SUE':lag,'window_events':len(window),
                 'last_signal_date':window.Date.max(),'control_date':b.iloc[bi].Date,
                 'Ret_pre':segment(a,np.array([i]),np.array([j]),-30,-3)[0]}
            assert rec['control_date']<=anchor
            rec.update({c:float(window[c].mean()) for c in SIG})
            rec.update({c:float(b.iloc[bi][c]) for c in controls})
            bet=beta_at(a,i,j,lo=-252,hi=-31)
            rr=a['ret'][i,j-1:j+2]-a['rf'][j-1:j+2]
            ff=a['factors'][j-1:j+2]
            rec['CAR_CH4']=float(np.sum(rr-bet[0]-ff@bet[1:])) if (
                bet is not None and np.isfinite(rr).all() and np.isfinite(ff).all()) else np.nan
            rows.append(rec)
        if n%500==0:
            log(f'Processed actual announcement firms {n}')
    d=pd.DataFrame(rows)
    d.to_parquet(WORK/'actual_announcement_signal_events.parquet',index=False)
    c=['Lag_SUE','Ret_pre',*controls]
    results=[]
    for y in ['SUE','CAR_CH4']:
        log(f'Fitting common-sample {y}')
        results.extend(dict(date_status='ACTUAL_ANNODT',**r)
                       for r in models(d,y,c,1e4 if y.startswith('CAR') else 1))
    res=bh(pd.DataFrame(results),['outcome','model'])
    res.to_csv(OUT/'fundamentals_and_confirmation.csv',index=False)
    flow.update(signal_window_events=len(d),minimum_public_signal_dates=5,
        signal_window=[-30,-3],control_anchor=-31,CAR_window=[-1,1],CH4_estimation_window=[-252,-31],
        minimum_CH4_estimation_observations=120,
        SUE_common_sample=int(res.loc[res.outcome.eq('SUE')].iloc[0].n),
        CAR_common_sample=int(res.loc[res.outcome.eq('CAR_CH4')].iloc[0].n),
        non_trading_announcement_dates=int(e.Annodt.ne(e.Date).sum()),
        announcement_time_of_day_available=False,actual_announcement_dates_used=True,
        missing_Annodt_imputed=False,analyst_forecast_error_estimated=False,
        ESI_parameters_changed=False,earlier_proxy_output_preserved=True)
    write('analysis_status.json',flow)
    log('Actual announcement SUE and CH4 confirmation regressions completed')

def units():
    dates=np.array(['2020-01-03','2020-01-06','2020-01-07'],dtype='datetime64[ns]')
    assert np.searchsorted(dates,np.datetime64('2020-01-04'),side='left')==1
    assert np.searchsorted(dates,np.datetime64('2020-01-06'),side='left')==1
    x=pd.DataFrame({'Annodt':pd.to_datetime(['2019-12-20','2020-01-01','2020-01-06']),
                    'SUE':[1.,2.,3.]})
    assert x.loc[x.Annodt.le('2020-01-02')].iloc[-1].SUE==2
    rng=np.random.default_rng(20261011)
    exact_sue=rng.normal(0,5,10000);exact_sigma=np.exp(rng.normal(-3,2,10000))
    valid,_,_=rounding_consistency(np.round(exact_sue,6),np.round(exact_sigma,6),
                                  np.round(exact_sue*exact_sigma,6))
    assert valid.all()
    assert not rounding_consistency([3.],[.01],[.1])[0].any()
    log('Trading alignment, historical SUE, rounded identity and corruption rejection checks passed')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['prepare','analyze','unit'])
    args=ap.parse_args()
    OUT.mkdir(parents=True,exist_ok=True);WORK.mkdir(parents=True,exist_ok=True)
    write('status_'+args.stage+'.json',dict(state='running',pid=os.getpid(),stage=args.stage,
        started=time.strftime('%Y-%m-%dT%H:%M:%S')))
    if args.stage=='unit':
        units()
    else:
        globals()[args.stage]()
    write('status_'+args.stage+'.json',dict(state='completed',pid=os.getpid(),stage=args.stage,
        finished=time.strftime('%Y-%m-%dT%H:%M:%S'),code_sha256=old.digest(Path(__file__)),
        archive_sha256=EXPECTED,parameters=old.parameters().to_dict(),
        software=dict(python=platform.python_version(),numpy=np.__version__,pandas=pd.__version__)))

if __name__=='__main__':
    main()
