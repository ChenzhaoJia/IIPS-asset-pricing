import os
os.environ['OPENBLAS_NUM_THREADS']='2'
os.environ['OMP_NUM_THREADS']='2'
from pathlib import Path
import hashlib,importlib.util,json,sys,time
import numpy as np,pandas as pd
from scipy.stats import t as student_t,chi2
from statsmodels.stats.multitest import multipletests
from prepare import ROOT,PROJECT,GROUPS,CONTROL,save,log

def main():
    assert not (ROOT/'grouped_regression_models').exists()
    (ROOT/'grouped_regression_models').mkdir()
    source=PROJECT/'data/analysis/revision/response_lag_stratified_2026_10_13/analysis.py'
    spec=importlib.util.spec_from_file_location('original_two_way_estimator',source)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    p=pd.read_parquet(ROOT/'prepared_reg.parquet')
    checks=[];baselines=pd.read_csv(ROOT/'regression_baselines.csv').to_dict('records');models=[];slopes=[];differences=[];joints=[]
    for outcome in ['q5_next_O2C_residual','CH4_next_O2C_residual','raw_next_O2C']:
        ident='baseline_'+outcome
        native=np.load(ROOT/'regression_models'/f'{ident}.npz')
        models.append(dict(id=ident,file='regression_models/'+ident+'.npz',outcome=outcome,specification='all_sample_baseline',n=int(native['n']),fe_rank=int(native['n'])-int(native['df'])-len(native['xcols']),xcols=native['xcols'].tolist()))
    b=next(v for v in baselines if v['outcome']=='q5_next_O2C_residual')
    preflight=dict(quoted_pdf_coef_bps=1.77,quoted_pdf_t=5.48,quoted_pdf_n=920584,computed=b,
                  coefficient_display_matches=f"{b['coef_bps']:.2f}"=='1.77',t_display_matches=f"{b['t']:.2f}"=='5.48',n_matches=b['n']==920584)
    original=json.loads((ROOT/'original_PanelOLS_preflight.json').read_text())
    assert original['original_PanelOLS_n']==920584 and original['max_all_beta_difference_bps']<1e-4
    assert abs(original['original_PanelOLS_ESI_bps']-b['coef_bps'])<1e-4
    assert abs(original['original_PanelOLS_t']-b['t'])<1e-4
    save('regression_preflight_resolution.json',dict(status='original_estimator_verified_publication_rounding_difference_retained',quoted_display_preflight=preflight,original_PanelOLS=original,scientific_rules_changed=False,ESI_scales_changed=False,grouped_results_previously_estimated=False))
    p=p.loc[p.lag_clean.fillna(False)].copy()
    for g in GROUPS[1:]:
        p['D_'+g]=p.lag_group.eq(g).astype(float)
        p['ESI_x_'+g]=p.ESI_z*p['D_'+g]
    common=p.dropna(subset=['ESI_z','Investor_Tone_z','Manager_Tone_z',*CONTROL,'raw_next_O2C','q5_next_O2C_residual','CH4_next_O2C_residual']).copy()
    for outcome in ['q5_next_O2C_residual','CH4_next_O2C_residual','raw_next_O2C']:
        for name,extra in [('baseline_controls',[]),('plus_both_tones',['Investor_Tone_z','Manager_Tone_z'])]:
            xcols=['ESI_z',*['ESI_x_'+g for g in GROUPS[1:]],*['D_'+g for g in GROUPS[1:]],*extra,*CONTROL]
            ident='lag_'+outcome+'_'+name
            fit,d,_,_=module.within_fit(common,outcome,xcols)
            np.savez_compressed(ROOT/'grouped_regression_models'/f'{ident}.npz',beta=fit['beta'],cov=fit['cov'],df=fit['df'],n=fit['n'],row_ids=d.index.to_numpy(),xcols=np.array(xcols))
            models.append(dict(id=ident,file='grouped_regression_models/'+ident+'.npz',outcome=outcome,specification=name,n=len(d),fe_rank=fit['fe_rank'],firms=fit['firms'],dates=fit['dates'],xcols=xcols))
            weights=[];quantile=student_t.ppf(.975,fit['df'])
            for g in GROUPS:
                w=np.zeros(len(xcols));w[0]=1
                if g!=GROUPS[0]:w[xcols.index('ESI_x_'+g)]=1
                weights.append(w)
                b=float(w@fit['beta']);se=float(np.sqrt(w@fit['cov']@w));t=b/se
                dd=d.loc[common.loc[d.index,'lag_group'].eq(g)]
                slopes.append(dict(model=ident,outcome=outcome,specification=name,group=g,coef_bps=b*1e4,se_bps=se*1e4,t=t,p=2*student_t.sf(abs(t),fit['df']),ci_low_bps=(b-quantile*se)*1e4,ci_high_bps=(b+quantile*se)*1e4,n_group=len(dd),n_total=len(d),firms=dd.Stkcd.nunique(),dates=dd.Date.nunique()))
            restriction=np.vstack([weights[j]-weights[0] for j in range(1,5)])
            u=restriction@fit['beta'];V=restriction@fit['cov']@restriction.T
            assert np.linalg.eigvalsh(V).min()>0
            W=float(u@np.linalg.solve(V,u))
            joints.append(dict(model=ident,outcome=outcome,specification=name,wald=W,df=4,p=chi2.sf(W,4),n=len(d),family='primary' if outcome=='q5_next_O2C_residual' else 'supplement'))
            for i in range(5):
                for j in range(i+1,5):
                    w=weights[i]-weights[j];b=float(w@fit['beta']);se=float(np.sqrt(w@fit['cov']@w));t=b/se
                    differences.append(dict(model=ident,outcome=outcome,specification=name,contrast=GROUPS[i]+' minus '+GROUPS[j],difference_bps=b*1e4,se_bps=se*1e4,t=t,p=2*student_t.sf(abs(t),fit['df']),ci_low_bps=(b-quantile*se)*1e4,ci_high_bps=(b+quantile*se)*1e4,n=len(d)))
            log('Grouped regression completed '+ident+' N='+str(len(d)))
    slope=pd.DataFrame(slopes)
    slope['p_bh_within_model']=slope.groupby('model').p.transform(lambda x:multipletests(x,method='fdr_bh')[1])
    slope.to_csv(ROOT/'regression_slopes.csv',index=False)
    dif=pd.DataFrame(differences);dif['p_bh_all_60']=multipletests(dif.p,method='fdr_bh')[1]
    dif.to_csv(ROOT/'regression_pairwise_differences.csv',index=False)
    wald=pd.DataFrame(joints);wald['p_adjusted']=np.nan
    for family,method in [('primary','holm'),('supplement','fdr_bh')]:
        ix=wald.family.eq(family);wald.loc[ix,'p_adjusted']=multipletests(wald.loc[ix,'p'],method=method)[1]
    wald.to_csv(ROOT/'regression_joint_tests.csv',index=False)
    save('regression_model_index.json',models)
    counts=common.groupby('lag_group',observed=True).agg(n=('Stkcd','size'),firms=('Stkcd','nunique'),dates=('Date','nunique')).reset_index()
    counts['share_pct']=counts.n/len(common)*100;counts.to_csv(ROOT/'regression_common_sample_distribution.csv',index=False)
    save('regression_status.json',dict(status='complete',models=len(models),grouped_models=6,slopes=30,pairwise=60,common_n=len(common)))
    log('Regression stage complete')

if __name__=='__main__':main()
