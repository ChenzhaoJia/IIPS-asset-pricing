"""Independent date guards and PanelOLS numerical reproduction of all columns."""
import os,sys,json,hashlib,time,platform
from pathlib import Path
os.environ['OPENBLAS_NUM_THREADS']='2'
os.environ['OMP_NUM_THREADS']='2'
import numpy as np
import pandas as pd
from linearmodels.panel import PanelOLS
import linearmodels
from actual_earnings import WORK,OUT,EXPECTED,SOURCE
from mechanism_suite import load,SIG
import response_lag_pricing_suite as old

# Explicit user authorization on 2026-10-11. Numerical comparison criteria,
# not statistical significance levels or estimation settings.
TOLERANCES={'coef':1e-5,'t':1e-5,'p':1e-5,'adjusted_r2':1e-8}
PROTECTED=[
    SOURCE,WORK/'actual_announcement_signal_events.parquet',WORK/'unique_reports.parquet',
    OUT/'fundamentals_and_confirmation.csv',OUT/'analysis_status.json',
    Path('D:/draft/drafts/manuscript/main.tex'),
    Path('D:/draft/drafts/manuscript/tables/public_earnings_announcements.tex'),
    Path('D:/draft/data/verification/ch4_migration_2026-10-07/recalculation_manifest.json')]

def stars(p):
    return '***' if p<.01 else '**' if p<.05 else '*' if p<.1 else ''

def main():
    start=time.monotonic()
    before={str(p):old.digest(p) for p in PROTECTED}
    (OUT/'validation_input_hashes_before.json').write_text(
        json.dumps(before,indent=2),encoding='utf-8')
    d=pd.read_parquet(WORK/'actual_announcement_signal_events.parquet')
    results=pd.read_csv(OUT/'fundamentals_and_confirmation.csv')
    assert results.date_status.eq('ACTUAL_ANNODT').all()
    receipt=json.loads((OUT/'receipt_audit.json').read_text(encoding='utf-8'))
    assert old.digest(SOURCE)==EXPECTED
    assert receipt['formula_rounding_check']['outside_bound']==0
    assert not d.duplicated(['Stkcd','Date']).any()
    assert d.last_signal_date.lt(d.Annodt).all()
    assert d.control_date.lt(d.Annodt).all()
    a=old.market_arrays()
    j=np.searchsorted(a['dates'],d.Date.to_numpy('datetime64[ns]'))
    assert d.control_date.le(pd.to_datetime(a['dates'][j-31])).all()
    assert np.array_equal(j,np.searchsorted(a['dates'],d.Annodt.to_numpy('datetime64[ns]')))
    assert d.window_events.ge(5).all()
    # Independently check stored signal means from the public panel.
    p=load()
    for q in d.sample(20,random_state=20261011).itertuples():
        ix=np.searchsorted(a['dates'],np.datetime64(q.Date))
        # Match the original analysis order without relaxing numeric tolerance.
        w=p.loc[p.Stkcd.eq(q.Stkcd)&p.date_idx.between(ix-30,ix-3)].sort_values('date_idx')
        assert len(w)==q.window_events
        for s in SIG:
            assert abs(float(w[s].mean())-getattr(q,s))<1e-12
    controls=['Lag_SUE','Ret_pre','Size','BM','ROA','Lev','Illiqd','Dturn','Firm_Age_Ln']
    rows=[]
    for y in ['SUE','CAR_CH4']:
        common=d.replace([np.inf,-np.inf],np.nan).dropna(subset=[y,*SIG,*controls])
        for model,terms in [('ESI',['ESI_z']),('tones',SIG[1:]),('joint',SIG)]:
            z=common.set_index(['Stkcd','Date']).sort_index()
            r=PanelOLS(z[y],z[terms+controls],entity_effects=True,time_effects=True).fit(
                cov_type='clustered',cluster_entity=True,cluster_time=True,debiased=True)
            for term in terms:
                expected=results.loc[results.outcome.eq(y)&results.model.eq(model)&results.term.eq(term)].iloc[0]
                unit=1e4 if y=='CAR_CH4' else 1
                assert int(r.nobs)==int(expected.n)
                co=float(r.params[term]*unit);ts=float(r.tstats[term]);pv=float(r.pvalues[term])
                adjusted=float(1-(1-r.rsquared_inclusive)*(r.nobs-1)/r.df_resid)
                rec=dict(outcome=y,model=model,term=term,n=int(r.nobs))
                for metric,value in [('coef',co),('t',ts),('p',pv),('adjusted_r2',adjusted)]:
                    original=float(expected[metric])
                    rec[metric+'_original']=original
                    rec[metric+'_independent']=value
                    rec[metric+'_difference']=value-original
                    rec[metric+'_absolute_difference']=abs(value-original)
                    rec[metric+'_within_tolerance']=abs(value-original)<=TOLERANCES[metric]
                rec['coefficient_two_decimals_match']=format(co,'.2f')==format(expected.coef,'.2f')
                rec['t_two_decimals_match']=format(ts,'.2f')==format(expected.t,'.2f')
                rec['adjusted_r2_three_decimals_match']=format(adjusted,'.3f')==format(expected.adjusted_r2,'.3f')
                rec['significance_stars_match']=stars(pv)==stars(expected.p)
                rows.append(rec)
            print(f'Checked {y}: {model}',flush=True)
    excluded=pd.read_csv(OUT/'ambiguous_event_dates_excluded.csv',parse_dates=['Date','Annodt','EndDate'])
    in_study=excluded.Date.between(old.START,old.END)
    annual=d.groupby(d.Date.dt.year).size().to_dict()
    missing=d[[*SIG,*controls,'SUE','CAR_CH4']].isna().sum().astype(int).to_dict()
    assert int(in_study.sum())==8
    comparison=pd.DataFrame(rows)
    assert len(comparison)==len(results)==12
    comparison.to_csv(OUT/'validation_numeric_differences.csv',index=False)
    criterion_columns=[c for c in comparison if c.endswith('_within_tolerance') or c.endswith('_match')]
    passed=bool(comparison[criterion_columns].all().all())
    after={str(p):old.digest(p) for p in PROTECTED}
    assert before==after,'Protected original inputs or manuscript changed during validation'
    maxima={k:float(comparison[k+'_absolute_difference'].max()) for k in TOLERANCES}
    report=dict(state='NUMERICAL_AND_TIMING_CHECKS_PASSED' if passed else 'NUMERICAL_DIFFERENCES_REQUIRE_REVIEW',
        raw_archive_sha256=EXPECTED,
        code_sha256=old.digest(Path(__file__)),PanelOLS_reproduced_specs=6,reproduced_terms=rows,
        original_solver='accelerated pyhdfe projection with PanelOLS clustered covariance conventions',
        independent_solver='linearmodels PanelOLS with firm and event-date effects',
        comparison_type='Alternative-solver numerical equivalence, not byte-identical rerun of the full data pipeline',
        user_authorized_absolute_tolerances=TOLERANCES,maximum_absolute_differences=maxima,
        reported_rounding_and_significance_match=bool(comparison[[c for c in criterion_columns if c.endswith('_match')]].all().all()),
        protected_file_hashes_before=before,protected_file_hashes_after=after,protected_files_unchanged=True,
        finished=time.strftime('%Y-%m-%dT%H:%M:%S'),elapsed_seconds=time.monotonic()-start,
        software=dict(python=platform.python_version(),numpy=np.__version__,pandas=pd.__version__,
                      linearmodels=linearmodels.__version__),
        signals_checked_against_public_panel=20,
        signal_window_events=len(d),event_year_counts=annual,missing_fields_in_signal_window=missing,
        ambiguous_reports_in_2017_2024=int(in_study.sum()),
        ambiguity_counter_note='The broad analysis counter includes pre-2010 reports mapped to the first observed calendar day. Only eight excluded reports fall in the study period.',
        independent_semantic_topic_accuracy_validated=False,analyst_forecast_error_estimated=False,
        all_inference_observational=True)
    (OUT/'validation_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:report[k] for k in ['state','PanelOLS_reproduced_specs',
                                          'ambiguous_reports_in_2017_2024','signal_window_events']}))
    print(json.dumps(maxima))
    if not passed:
        raise SystemExit(1)

if __name__=='__main__':
    main()
