"""Independent fixed-effect projection, cluster scores, sorting and HAC."""
import os
os.environ['OPENBLAS_NUM_THREADS']='2'
os.environ['OMP_NUM_THREADS']='2'
import json,time
import numpy as np,pandas as pd
from scipy.stats import t as student_t,chi2,norm
from prepare import ROOT,save,log,digest

def codes(s):return pd.factorize(s,sort=True)[0]

def independent_fe(d,ycol,xcols,df):
    ids=[codes(d.Stkcd),codes(d.Date)]
    z=d[[ycol,*xcols]].to_numpy(float)
    for it in range(10000):
        old=z.copy()
        for idx in ids:
            count=np.bincount(idx)
            mu=np.column_stack([np.bincount(idx,weights=z[:,k])/count for k in range(z.shape[1])])
            z-=mu[idx]
        if np.max(abs(z-old))<2e-11:break
    else:raise AssertionError('Ordinary demeaning did not converge')
    y,x=z[:,0],z[:,1:]
    gram=x.T@x;inv=np.linalg.inv(gram)
    beta=np.linalg.solve(gram,x.T@y)
    influence=(x@inv)*(y-x@beta)[:,None]
    V=np.zeros_like(gram)
    pair=codes(pd.MultiIndex.from_arrays([d.Stkcd,d.Date]))
    for idx,sign in [(ids[0],1),(ids[1],1),(pair,-1)]:
        S=np.column_stack([np.bincount(idx,weights=influence[:,k]) for k in range(influence.shape[1])])
        V+=sign*S.T@S
    return beta,V*(len(d)/df),it+1

def regressions():
    p=pd.read_parquet(ROOT/'prepared_reg.parquet')
    for g in ['one_day','two_days','three_to_five','over_five']:
        p['D_'+g]=p.lag_group.eq(g).astype(float)
        p['ESI_x_'+g]=p.ESI_z*p['D_'+g]
    models=json.loads((ROOT/'regression_model_index.json').read_text())
    rows=[]
    for m in models:
        a=np.load(ROOT/m['file'])
        d=p.loc[a['row_ids']].copy();xcols=a['xcols'].tolist();df=int(a['df'])
        beta,cov,it=independent_fe(d,m['outcome'],xcols,df)
        se=np.sqrt(np.diag(cov));se0=np.sqrt(np.diag(a['cov']))
        t=beta/se;t0=a['beta']/se0
        pp=2*student_t.sf(abs(t),df);pp0=2*student_t.sf(abs(t0),df)
        errors=dict(max_coefficient_difference_bps=float(np.max(abs(beta-a['beta']))*1e4),max_se_difference_bps=float(np.max(abs(se-se0))*1e4),max_t_difference=float(np.max(abs(t-t0))),max_p_difference=float(np.max(abs(pp-pp0))))
        assert errors['max_coefficient_difference_bps']<1e-4,(m['id'],errors)
        assert errors['max_t_difference']<1e-4 and errors['max_p_difference']<1e-5,(m['id'],errors)
        if m['specification']!='all_sample_baseline':
            inter=[xcols.index('ESI_x_'+g) for g in ['one_day','two_days','three_to_five','over_five']]
            for j in [None,*inter]:
                w=np.zeros(len(xcols));w[0]=1
                if j is not None:w[j]=1
                b=w@beta;b0=w@a['beta'];s=np.sqrt(w@cov@w);s0=np.sqrt(w@a['cov']@w)
                assert abs((b-b0)*1e4)<1e-4 and abs(b/s-b0/s0)<1e-4
            u=beta[inter];V=cov[np.ix_(inter,inter)];u0=a['beta'][inter];V0=a['cov'][np.ix_(inter,inter)]
            wald=float(u@np.linalg.solve(V,u));wald0=float(u0@np.linalg.solve(V0,u0))
            assert abs(chi2.sf(wald,4)-chi2.sf(wald0,4))<1e-5
        rows.append(dict(model=m['id'],iterations=it,**errors));log('Independent regression check '+m['id'])
    pd.DataFrame(rows).to_csv(ROOT/'independent_regression_checks.csv',index=False)
    save('regression_validation.json',dict(status='passed',models=len(rows),all_coefficients_checked=True,all_group_slopes_and_Wald_checked=True,max_errors={k:max(r[k] for r in rows) for k in ['max_coefficient_difference_bps','max_se_difference_bps','max_t_difference','max_p_difference']}))

def portfolios():
    models=json.loads((ROOT/'portfolio_model_index.json').read_text())
    rows=[]
    for m in models:
        a=np.load(ROOT/m['file']);x=a['x'];y=a['y']
        b=np.linalg.solve(x.T@x,x.T@y);e=y-x@b
        score=x*e[:,None];meat=score.T@score
        for k in range(1,6):
            if k>=len(score):break
            cross=score[k:].T@score[:-k];meat+=(1-k/6)*(cross+cross.T)
        bread=np.linalg.inv(x.T@x);cov=bread@meat@bread
        se=np.sqrt(np.diag(cov));t=b/se;t0=a['beta']/np.sqrt(np.diag(a['cov']))
        diff=dict(beta_max_bps=float(np.max(abs(b-a['beta']))*1e4),t_max=float(np.max(abs(t-t0))),p_max=float(np.max(abs(2*norm.sf(abs(t))-2*norm.sf(abs(t0))))))
        assert diff['beta_max_bps']<1e-4 and diff['t_max']<1e-4 and diff['p_max']<1e-5,(m['id'],diff)
        rows.append(dict(model=m['id'],**diff))
    pd.DataFrame(rows).to_csv(ROOT/'independent_portfolio_HAC_checks.csv',index=False)
    # Fixed spread of dates across all group/signal series, independent stable
    # selection except tied cutoff dates are documented and use original quicksort.
    p=pd.read_parquet(ROOT/'prepared_port.parquet')
    daily=pd.read_parquet(ROOT/'daily_portfolios.parquet');h=pd.read_parquet(ROOT/'selected_holdings.parquet')
    results=[]
    for (group,sig),q in daily.groupby(['group','signal'],sort=True):
        group_holdings=h.loc[h.group.eq(group)&h.signal.eq(sig)]
        dates=np.sort(q.Date.unique())
        positions=np.unique(np.linspace(0,len(dates)-1,min(30,len(dates)),dtype=int))
        sub=p if group=='all_original' else p.loc[p.lag_clean.fillna(False)&p.lag_group.eq(group)]
        for date in dates[positions]:
            pool=sub.loc[sub.Date.eq(date)&sub[sig].notna()&sub[sig].ne(0)&sub.port_next.notna()&sub.MktCap_B.notna()&sub.Next_LimitStatus.eq(0)]
            lo,hi=np.quantile(pool[sig].to_numpy(),[.3,.7])
            top=pool.loc[pool[sig].gt(0)&pool[sig].ge(hi)].sort_values(sig,ascending=False).head(50)
            low=pool.loc[pool[sig].lt(0)&pool[sig].le(lo)].sort_values(sig,ascending=True)
            low=low.loc[~low.Stkcd.isin(top.Stkcd)].head(50)
            for weight in ['EW','VW']:
                selected=group_holdings.loc[group_holdings.weight.eq(weight)&group_holdings.Date.eq(date)]
                assert set(selected.loc[selected.leg.eq('Long'),'Stkcd'])==set(top.Stkcd)
                assert set(selected.loc[selected.leg.eq('Short'),'Stkcd'])==set(low.Stkcd)
                returns=[]
                for leg,data in [('Long',top),('Short',low)]:
                    w=np.ones(len(data))/len(data) if weight=='EW' else data.MktCap_B.to_numpy()/data.MktCap_B.to_numpy().sum()
                    saved=selected.loc[selected.leg.eq(leg)].set_index('Stkcd').allocation.reindex(data.Stkcd).to_numpy()
                    assert np.max(abs(w-saved))<1e-7
                    returns.append(float(np.dot(w,data.port_next.to_numpy())))
                native=q.loc[q.Date.eq(date)&q.weight.eq(weight)].iloc[0]
                error=abs((returns[0]-returns[1]-native.LS)*1e4);assert error<1e-4
                results.append(dict(group=group,signal=sig,Date=str(date),weight=weight,LS_difference_bps=error))
    pd.DataFrame(results).to_csv(ROOT/'independent_sort_checks.csv',index=False)
    save('portfolio_validation.json',dict(status='passed',HAC_models=len(rows),sort_date_weight_checks=len(results),all_holdings_independently_rebuilt=False,max_sort_difference_bps=max(r['LS_difference_bps'] for r in results)))

if __name__=='__main__':
    import sys
    if sys.argv[1]=='regressions':regressions()
    elif sys.argv[1]=='portfolios':portfolios()
