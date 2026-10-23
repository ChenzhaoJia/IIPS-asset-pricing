"""Reproduce frozen one-day Annual Review results from local prepared inputs.

Run: python scripts/reproduce_baseline.py [--sort]
--sort reconstructs every daily portfolio; default checks saved daily series.
"""
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS', '2')
os.environ.setdefault('OMP_NUM_THREADS', '2')
from pathlib import Path
import sys, argparse, json
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from iip.paths import ROOT, DATA, RESULTS
from iip.legacy import hac, select, within_fit
CTRL = ['Size','BM','ROA','Lev','Illiqd','Dturn','Ret_t_1','Vol_t',
        'Ret_t_30_t_2','Newstone_t_30_t_3','Newsdummy_t_30_t_3']
FACT = {'CH4':['ch4_mktrf','ch4_SMB','ch4_VMG','ch4_PMO'],
        'q5':['q5_MKT','q5_ME','q5_IA','q5_ROE','q5_EG']}

def run(rebuild_sorts=False):
    work = DATA / 'processed/annual_review'
    out = DATA / 'temp/reproduction'
    out.mkdir(parents=True, exist_ok=True)
    p = pd.read_parquet(work / 'prepared_reg.parquet')
    expected = pd.read_csv(RESULTS / 'annual_review_o2c/regression_baselines.csv')
    rows = []
    for row in expected.itertuples():
        d = p.dropna(subset=[row.outcome, 'ESI_z', *CTRL])
        f, *_ = within_fit(d, row.outcome, ['ESI_z', *CTRL])
        coef = f['beta'][0] * 10000
        t = f['beta'][0] / np.sqrt(f['cov'][0,0])
        assert f['n'] == row.n
        assert abs(coef-row.coef_bps) < 1e-4 and abs(t-row.t) < 1e-4
        rows.append(dict(outcome=row.outcome,n=f['n'],coef_bps=coef,t=t,
                         coef_difference_bps=coef-row.coef_bps,t_difference=t-row.t))
        print('Verified regression:', row.outcome, flush=True)
    pd.DataFrame(rows).to_csv(out/'regressions.csv',index=False)
    daily = pd.read_parquet(work/'daily_portfolios.parquet')
    daily = daily.loc[daily.group.eq('all_original')]
    if rebuild_sorts:
        port = pd.read_parquet(work/'prepared_port.parquet')
        chunks=[]
        for signal in ['ESI_sort','Investor_Tone','Manager_Tone']:
            z,_=select(port,'all_original',signal,False)
            chunks.append(z)
        rebuilt=pd.concat(chunks,ignore_index=True)
        keys=['group','signal','weight','Date']
        check=daily.merge(rebuilt,on=keys,suffixes=('_saved','_new'),validate='one_to_one')
        assert len(check)==len(daily)==len(rebuilt)
        assert np.max(np.abs(check.LS_saved-check.LS_new))*1e4<1e-4
        daily=rebuilt
    factors=pd.read_parquet(work/'factors.parquet')
    expected=pd.read_csv(RESULTS/'annual_review_o2c/portfolio_baselines.csv')
    rows=[]
    for row in expected.itertuples():
        q=daily.loc[daily.signal.eq(row.signal)&daily.weight.eq(row.weight)].set_index('Date').sort_index()
        assert len(q)==row.n
        assert abs(q.LS.mean()*1e4-row.mean_bps)<1e-4
        for name,cols in FACT.items():
            fit=hac(q.LS,factors[cols])
            assert abs(fit['alpha_bps']-getattr(row,name+'_alpha_bps'))<1e-4
            assert abs(fit['t']-getattr(row,name+'_t'))<1e-4
            rows.append(dict(signal=row.signal,weight=row.weight,benchmark=name,
                             alpha_bps=fit['alpha_bps'],t=fit['t'],n=fit['n']))
    pd.DataFrame(rows).to_csv(out/'portfolios.csv',index=False)
    status={'status':'passed','regressions':3,'portfolio_factor_models':12,
            'full_daily_sort_rebuilt':rebuild_sorts,
            'scope':'Frozen prepared inputs; does not independently rebuild licensed raw ingestion.'}
    (out/'status.json').write_text(json.dumps(status,indent=2),encoding='utf-8')
    print(json.dumps(status),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--sort',action='store_true')
    run(parser.parse_args().sort)
