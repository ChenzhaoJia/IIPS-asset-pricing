"""Reconcile full classifier output with raw identities and public signal cohorts."""
import os,sys,re,json,time,hashlib
from pathlib import Path
os.environ['OPENBLAS_NUM_THREADS']='2'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy.stats import chi2
from statsmodels.stats.multitest import multipletests
from fast_panel_ch4 import fit_panel
import response_lag_pricing_suite as old
from mechanism_suite import load,result

ROOT=Path('D:/draft')
SRC=ROOT/'data/working/full_topic_2026-10-11/accepted_R005_V002'
OUT=ROOT/'data/verification/full_topic_2026-10-11'
WORK=ROOT/'data/working/full_topic_2026-10-11'
FIG=ROOT/'drafts/manuscript/figures'

def log(s):print(time.strftime('%H:%M:%S'),s,flush=True)
def clean(t):return re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',str(t or ''))).strip()

def prepare():
    receipt=json.loads((OUT/'receipt_audit.json').read_text())
    assert receipt['pairs']==5836158
    assert old.digest(old.RAW)=='5578545b2fd290076b296e01997ccf57fc3ee40df2a1473b7c40ef3897b92502'
    timing=pd.read_parquet(old.WORK/'cohort_lags_verified.parquet',
          columns=['Stkcd','Question_Date','Availability_Date'])
    timing=timing.loc[timing.Availability_Date.notna()]
    timing['Stkcd']=pd.to_numeric(timing.Stkcd).astype('int32')
    lookup=timing.set_index(['Stkcd','Question_Date']).Availability_Date
    assert lookup.index.is_unique
    columns=['Qsubj','Reply','Scode','Qtm_dt','Atm_dt','Qtm_datetime','Qtm','year']
    batches=pq.ParquetFile(old.RAW).iter_batches(batch_size=5000,columns=columns)
    pieces=[];states=[];coverage=[];offset=0
    for shard,batch in enumerate(batches):
        raw=batch.to_pandas()
        pred=pd.read_parquet(SRC/f'predictions/shard_{shard:05d}.parquet')
        q=pred.loc[pred.side.eq('question')].sort_values('source_row_id').reset_index(drop=True)
        r=pred.loc[pred.side.eq('reply')].sort_values('source_row_id').reset_index(drop=True)
        assert q.source_row_id.tolist()==list(range(offset,offset+len(raw)))
        assert q.source_row_id.tolist()==r.source_row_id.tolist()
        firm=pd.to_numeric(raw.Scode).astype('int32')
        assert np.array_equal(pd.to_numeric(q.firm).to_numpy(),firm.to_numpy())
        for side,part,col in [('question',q,'Qsubj'),('reply',r,'Reply')]:
            # Arrow None stays None, exactly as in the frozen inference entry.
            hashes=[hashlib.sha256(clean(s).encode('utf-8')).hexdigest() for s in batch.to_pydict()[col]]
            assert hashes==part.text_sha256.tolist(),f'Text identity mismatch {shard} {side}'
        qd=pd.to_datetime(raw.Qtm_dt).combine_first(pd.to_datetime(raw.Qtm_datetime))
        qd=qd.combine_first(pd.to_datetime(raw.Qtm,format='mixed',errors='coerce')).dt.floor('D')
        idx=pd.MultiIndex.from_arrays([firm,qd])
        date=lookup.reindex(idx).to_numpy()
        d=pd.DataFrame({'Stkcd':firm,'Question_Date':qd,'Date':date,'N':1})
        for k in range(20):
            d[f'q{k}']=q.topic_code.eq(k).astype('int32')
            d[f'r{k}']=r.topic_code.eq(k).astype('int32')
        d['Both_Assigned']=q.topic_state.eq('assigned') & r.topic_state.eq('assigned')
        d['Same_Topic']=d.Both_Assigned & q.topic_code.eq(r.topic_code)
        d['Generic_Reply']=r.reply_status.eq('generic_template_only').astype('int32')
        d['Question_Assigned']=q.topic_state.eq('assigned').astype('int32')
        d['Reply_Assigned']=r.topic_state.eq('assigned').astype('int32')
        measures=['N',*[f'{s}{k}' for s in ['q','r'] for k in range(20)],
                  'Both_Assigned','Same_Topic','Generic_Reply','Question_Assigned','Reply_Assigned']
        use=d.loc[d.Date.notna()]
        pieces.append(use.groupby(['Stkcd','Date'],sort=False)[measures].sum().reset_index())
        for y,g in d.assign(year=raw.year).groupby('year'):
            coverage.append({'year':int(y),'raw_pairs':len(g),'matched_to_production_cohort':int(g.Date.notna().sum())})
        offset+=len(raw)
        if shard%100==0:log(f'Raw identities checked and reconciled {offset:,} pairs')
    assert offset==5836158
    data=pd.concat(pieces,ignore_index=True).groupby(['Stkcd','Date'],as_index=False).sum()
    for k in range(20):
        data[f'QShare_{k}']=data[f'q{k}']/data.N
        data[f'RShare_{k}']=data[f'r{k}']/data.N
    data['Generic_Reply_Share']=data.Generic_Reply/data.N
    data['Both_Assigned_Share']=data.Both_Assigned/data.N
    data['Same_Topic_Share']=data.Same_Topic/data.N
    # Unclassified is an explicit category, not a forced residual theme.
    data['Dominant_Topic']=data[[f'q{k}' for k in range(20)]].to_numpy().argmax(1)
    data.to_parquet(WORK/'production_availability_topic_features.parquet',index=False)
    pd.DataFrame(coverage).groupby('year',as_index=False).sum().to_csv(OUT/'source_to_analysis_coverage.csv',index=False)
    old.save_json(OUT/'raw_identity_reconciliation.json',dict(raw_pairs=offset,text_hashes_checked=2*offset,
       paired_firm_dates=len(data),matched_raw_pairs=int(data.N.sum()),
       date_reconstruction='Qtm_dt with Qtm_datetime and Qtm fallback, floored to natural date',
       analysis_cohort_mapping='existing frozen complete-score firm-question-date to first trading day after last reply',
       thresholds_changed=False,ESI_changed=False,independent_validation=False))

def analysis():
    p=load()
    topics=pd.read_parquet(WORK/'production_availability_topic_features.parquet')
    p=p.merge(topics,on=['Stkcd','Date'],how='left',validate='one_to_one')
    controls=[c+'_z' for c in old.CONTROL_COLUMNS]
    tone=['Investor_Tone_z','Manager_Tone_z']
    y='C2C_1_1'
    guard=[y,'ESI_z',*tone,*controls,'Dominant_Topic']
    p=p.dropna(subset=guard)
    p['Dominant_Topic']=p.Dominant_Topic.astype(int)
    cats=sorted(p.Dominant_Topic.unique())
    assert cats[0]==0
    rows=[];joint=[]
    for k in cats[1:]:
        p[f'T_{k}']=p.Dominant_Topic.eq(k).astype(float)
        p[f'ESI_T_{k}']=p.ESI_z*p[f'T_{k}']
    inter=[f'ESI_T_{k}' for k in cats[1:]]
    dummy=[f'T_{k}' for k in cats[1:]]
    for model,extra in [('baseline',[]),('joint_tones',tone)]:
        r,s=fit_panel(p,y,['ESI_z',*inter,*dummy,*extra,*controls])
        beta=r.params[inter].to_numpy();cov=r.cov.loc[inter,inter].to_numpy()
        w=float(beta@np.linalg.pinv(cov)@beta)
        joint.append({'model':model,'wald':w,'df':len(inter),'p':chi2.sf(w,len(inter)),'n':len(s),
            'adjusted_r2':result(r,'ESI_z')['adjusted_r2'],
            'reference':'Dominant unclassified or low confidence question content'})
        for k in cats:
            vec=pd.Series(0.,index=r.params.index);vec['ESI_z']=1
            if k:vec[f'ESI_T_{k}']=1
            co=float(vec@r.params);se=float(np.sqrt(vec@r.cov@vec))
            from scipy.stats import norm
            rows.append({'model':model,'topic_code':k,'coef_bps':co*1e4,'t':co/se,
               'p':2*norm.sf(abs(co/se)),'ci_low_bps':(co-1.96*se)*1e4,'ci_high_bps':(co+1.96*se)*1e4,
               'topic_n':int(p.Dominant_Topic.eq(k).sum()),'n':len(s),
               'adjusted_r2':result(r,'ESI_z')['adjusted_r2'],
               'difference_from_reference':0 if k==0 else r.params[f'ESI_T_{k}']*1e4})
        log('Topic slope model completed '+model)
    d=pd.DataFrame(rows)
    d['p_bh']=d.groupby('model').p.transform(lambda s:multipletests(s,method='fdr_bh')[1])
    d.to_csv(OUT/'topic_slope_heterogeneity.csv',index=False)
    pd.DataFrame(joint).to_csv(OUT/'topic_joint_wald.csv',index=False)
    p.groupby('Dominant_Topic',as_index=False).agg(n=('ESI_z','size'),ESI_mean=('ESI_z','mean'),
       question_assigned_share=('Question_Assigned','sum'),raw_pairs=('N','sum')).to_csv(OUT/'analysis_dominant_topic_counts.csv',index=False)
    replyrows=[]
    p['ESI_x_Generic']=p.ESI_z*p.Generic_Reply_Share
    for model,extra in [('baseline',[]),('joint_tones',tone)]:
        r,_=fit_panel(p,y,['ESI_z','Generic_Reply_Share','ESI_x_Generic',*extra,*controls])
        for term in ['ESI_z','Generic_Reply_Share','ESI_x_Generic']:
            replyrows.append({'model':model,**result(r,term,1e4)})
    pd.DataFrame(replyrows).to_csv(OUT/'generic_reply_interaction.csv',index=False)
    log('Exploratory topic application completed')

def plot():
    from html import escape
    d=pd.read_csv(SRC/'reports/CONTENT_DISTRIBUTION.csv')
    tax=json.loads((SRC/'task/docs/taxonomy_19_content.json').read_text(encoding='utf-8-sig'))
    labels={x['code']:x['paper_label'] for x in tax['content']}
    FIG.mkdir(parents=True,exist_ok=True)
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="835" viewBox="0 0 1000 835">',
         '<rect width="1000" height="835" fill="white"/>',
         '<g font-family="Georgia, Times New Roman, serif" font-size="17" fill="#222">']
    for v in range(0,26,5):
        x=350+v*23
        svg.append(f'<path d="M{x} 50 V770" stroke="#ddd" stroke-width="1"/><text x="{x}" y="795" text-anchor="middle">{v}</text>')
    for row,rec in enumerate(d.itertuples()):
        y=72+row*37
        svg.append(f'<text x="335" y="{y+6}" text-anchor="end">{escape(labels[rec.code])}</text>')
        for delta,value,color in [(-11,rec.question_assigned_count,'#245377'),(3,rec.reply_assigned_count,'#bb8a50')]:
            svg.append(f'<rect x="350" y="{y+delta}" width="{value/5836158*100*23:.3f}" height="12" fill="{color}"/>')
    svg.extend(['<text x="645" y="825" text-anchor="middle">Percentage of all raw question or reply records</text>',
                '<rect x="630" y="15" width="18" height="12" fill="#245377"/><text x="656" y="28">Questions</text>',
                '<rect x="790" y="15" width="18" height="12" fill="#bb8a50"/><text x="816" y="28">Replies</text>',
                '</g></svg>'])
    (FIG/'full_topic_distribution_2026-10-11.svg').write_text('\n'.join(svg),encoding='utf-8')
    log('Full topic distribution vector figure exported')

if __name__=='__main__':
    stage=sys.argv[1]
    WORK.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
    globals()[stage]()
