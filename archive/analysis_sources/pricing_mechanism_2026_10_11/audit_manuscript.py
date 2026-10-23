"""Static citation, number, artifact, and source checks for this revision."""
import re,json,hashlib
from pathlib import Path
from collections import Counter
import pandas as pd
ROOT=Path('D:/draft')
MAN=ROOT/'drafts/manuscript'
OUT=ROOT/'data/verification/pricing_mechanism_2026-10-11'
def expand(path):
    t=path.read_text(encoding='utf-8')
    t=re.sub(r'\\iffalse\b.*?\\fi\b','',t,flags=re.S)
    t=re.sub(r'(?<!\\)%[^\n]*','',t)
    return re.sub(r'\\input\{([^}]+)\}',lambda m:expand(MAN/m[1]),t)
text=expand(MAN/'main.tex')
bib=(MAN/'references.bib').read_text(encoding='utf-8')
keys=set(re.findall(r'@\w+\s*\{\s*([^,\s]+)\s*,',bib))
cites=set(k.strip() for s in re.findall(r'\\cite(?:p|t|author|year|yearpar)?(?:\[[^\]]*\])*\{([^{}]+)\}',text)
          for k in s.split(','))
labels=re.findall(r'\\label\{([^}]+)\}',text)
refs=set(re.findall(r'\\(?:ref|eqref|pageref)\{([^}]+)\}',text))
missing_cites=sorted(cites-keys);missing_refs=sorted(refs-set(labels))
duplicate_labels=[k for k,v in Counter(labels).items() if v>1]
assert not missing_cites,(missing_cites,'citation keys')
assert not missing_refs,(missing_refs,'references')
assert not duplicate_labels,duplicate_labels
main=(MAN/'main.tex').read_text(encoding='utf-8')
claims=[]
def check(name,value,shown,fragment):
    assert shown in main and fragment in main,(name,shown)
    assert format(value,'.2f')==shown,(name,value,shown)
    claims.append(dict(claim=name,unrounded=float(value),rendered=shown))
d=pd.read_csv(OUT/'return_path_regressions.csv')
for y,num in [('available_day','2.97'),('post1_5','4.04')]:
    v=d.loc[d['sample'].eq('window_available')&d.model.eq('ESI')&d.outcome.eq(y)&d.term.eq('ESI_z')].iloc[0].coef
    check(y,v,num,'Table \\ref{tab:public_return_paths}')
d=pd.read_csv(OUT/'risk_characteristic_fama_macbeth.csv')
for m,num in [('risk_ESI_characteristics','1.12'),('risk_ESI_full_text','0.31')]:
    v=d.loc[d.model.eq(m)&d.term.eq('ESI_z')].iloc[0].coef
    check(m,v,num,'Table \\ref{tab:risk_exposures}')
d=pd.read_csv(OUT/'risk_conditioned_portfolios.csv')
for sig,num in [('ESI_z','3.15'),('Manager_Tone_z','3.43')]:
    v=d.loc[d.rule.eq('beta_and_size')&d.signal.eq(sig)&d.target.eq('spread')].iloc[0].alpha_bps
    check('conditional_'+sig,v,num,'Table \\ref{tab:risk_conditional_sorts}')
d=pd.read_csv(OUT/'actual_announcements/fundamentals_and_confirmation.csv')
assert d.date_status.eq('ACTUAL_ANNODT').all()
for y,m,num in [('SUE','ESI','0.07'),('SUE','joint','0.19'),('CAR_CH4','joint','-22.59')]:
    v=d.loc[d.outcome.eq(y)&d.model.eq(m)&d.term.eq('ESI_z')].iloc[0].coef
    check('actual_'+y+'_'+m,v,num,'Table \\ref{tab:fundamental_sue}')
for stage in ['unit','prepare','analyze']:
    assert json.loads((OUT/'actual_announcements'/f'status_{stage}.json').read_text())['state']=='completed'
assert '\\input{tables/public_earnings_announcements.tex}' in main
assert '\\input{tables/public_earnings_updates.tex}' not in main
topics=ROOT/'data/verification/full_topic_2026-10-11'
w=pd.read_csv(topics/'topic_joint_wald.csv')
assert round(w.iloc[1].p,3)==.873 and '$p=0.873$' in main
receipt=json.loads((topics/'receipt_audit.json').read_text())
assert receipt['pairs']==5836158 and receipt['two_side_rows']==11672316
for stage in ['unit','paths','fundamentals','risks']:
    assert json.loads((OUT/f'status_{stage}.json').read_text())['state']=='completed'
artifact_paths=[MAN/'main.tex',MAN/'references.bib',*sorted((MAN/'tables').glob('*.tex')),
                MAN/'figures/full_topic_distribution_2026-10-11.png']
report=dict(state='STATIC_EVIDENCE_CHECKS_PASSED',missing_citation_keys=missing_cites,
 missing_reference_labels=missing_refs,duplicate_labels=duplicate_labels,
 new_numeric_claims=claims,topic_joint_p=float(w.iloc[1].p),
 old_false_earnings_claim_removed=('coefficient on aggregated ESI is 0.043' not in main),
 classification_accuracy_validated=False,announcement_dates_available=True,
 actual_announcement_estimation_status='COMPLETED_ACTUAL_ANNODT',
 actual_announcement_independent_validation=(
     json.loads((OUT/'actual_announcements/validation_report.json').read_text())['state']
     if (OUT/'actual_announcements/validation_report.json').exists() else 'PENDING'),
 hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in artifact_paths},
 software=dict(pandas=pd.__version__))
(OUT/'manuscript_integrity_audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({k:report[k] for k in ['state','missing_citation_keys','missing_reference_labels',
                'duplicate_labels','old_false_earnings_claim_removed']}))
