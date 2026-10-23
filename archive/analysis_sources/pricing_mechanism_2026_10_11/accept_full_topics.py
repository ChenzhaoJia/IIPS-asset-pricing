"""Read-only receipt audit and safe extraction of the completed GPU artifact."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import zipfile
import time
import pyarrow.parquet as pq
import pandas as pd

ROOT = Path('D:/draft')
ARCHIVE = ROOT/'data/working/gpu_exchange/from_gpu/R005_FULL_USER_ACCEPTED_V002_COMPLETE_20261011_125003_9bd8b68a142f.zip'
DEST = ROOT/'data/working/full_topic_2026-10-11/accepted_R005_V002'
OUT = ROOT/'data/verification/full_topic_2026-10-11'

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):
            h.update(b)
    return h.hexdigest()

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    ready = json.loads(Path(str(ARCHIVE)+'.READY.json').read_text(encoding='utf-8-sig'))
    observed = digest(ARCHIVE)
    assert observed == ready['sha256'] == Path(str(ARCHIVE)+'.sha256').read_text().split()[0]
    assert ARCHIVE.stat().st_size == ready['bytes']
    print('Archive SHA256 passed; extracting and checking internal files',flush=True)
    with zipfile.ZipFile(ARCHIVE) as z:
        manifest = json.loads(z.read('RESULT_MANIFEST.json'))
        assert manifest['state']=='completed' and manifest['entry_exit_code']==0
        assert manifest['total_pairs']==5836158 and manifest['two_side_rows']==11672316
        assert len(z.namelist()) == len(set(z.namelist()))
        assert set(z.namelist()) == set(manifest['files']) | {'RESULT_MANIFEST.json'}
        for i,info in enumerate(z.infolist()):
            p = PurePosixPath(info.filename)
            assert not p.is_absolute() and '..' not in p.parts and ':' not in info.filename and '\\' not in info.filename
            target = DEST.joinpath(*p.parts)
            assert target.resolve().is_relative_to(DEST.resolve())
            expected = manifest['files'].get(info.filename)
            if target.exists():
                assert expected is None or digest(target)==expected
            else:
                target.parent.mkdir(parents=True,exist_ok=True)
                h=hashlib.sha256()
                with z.open(info) as src, target.open('xb') as dst:
                    for b in iter(lambda:src.read(1024*1024),b''):
                        dst.write(b)
                        h.update(b)
                assert expected is None or h.hexdigest()==expected
            if i%400==0: print('checked files',i,flush=True)
    counts=[]
    last=-1
    for i,f in enumerate(sorted((DEST/'predictions').glob('*.parquet'))):
        d=pd.read_parquet(f)
        assert {'source_row_id','side','topic_code','topic_state'}.issubset(d)
        q=d[d.side.eq('question')].sort_values('source_row_id')
        r=d[d.side.eq('reply')].sort_values('source_row_id')
        assert len(q)==len(r) and q.source_row_id.tolist()==r.source_row_id.tolist()
        ids=q.source_row_id.to_numpy()
        assert ids[0]==last+1 and (ids[1:]-ids[:-1]==1).all()
        last=int(ids[-1])
        assert len(d)==2*len(q) and not d.duplicated(['source_row_id','side']).any()
        for side,g in d.groupby('side'):
            for state,n in g.topic_state.value_counts().items():
                counts.append({'side':side,'topic_state':state,'n':int(n)})
        if i==0:
            (OUT/'prediction_schema.json').write_text(json.dumps({c:str(d[c].dtype) for c in d},indent=2),encoding='utf-8')
            print('schema',list(d),flush=True)
    assert last==5836157 and i+1==1168
    count=pd.DataFrame(counts).groupby(['side','topic_state'],as_index=False).n.sum()
    count.to_csv(OUT/'classification_coverage_verified.csv',index=False)
    result={'state':'TECHNICAL_RECEIPT_VERIFIED_SEMANTIC_VALIDATION_PENDING','archive_sha256':observed,'files_verified':len(manifest['files']),'prediction_shards':i+1,'pairs':last+1,'two_side_rows':2*(last+1),'quality_status':manifest['quality_status'],'independent_human_validation':False,'final_semantic_test_opened':False,'accepted_directory':str(DEST),'checked_at':time.strftime('%Y-%m-%dT%H:%M:%S'),'code_sha256':digest(Path(__file__))}
    (OUT/'receipt_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=True),flush=True)
    print(count.to_string(index=False),flush=True)

if __name__=='__main__': main()
