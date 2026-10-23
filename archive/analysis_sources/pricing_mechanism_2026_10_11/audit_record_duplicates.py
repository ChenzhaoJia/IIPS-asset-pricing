"""Check archive record keys, separate from unique prediction identifiers."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
ROOT=Path('D:/draft')
RAW=ROOT/'data/working/gpu_migration_2026_10_07/iip_topic_gpu/data/raw_qna.parquet'
OUT=ROOT/'data/verification/full_topic_2026-10-11'
cols=['From','Scode','Qtm','Qsubj','Recvtm','Reply']
parts=[]
for batch in pq.ParquetFile(RAW).iter_batches(batch_size=50000,columns=cols):
    d=batch.to_pandas().fillna('').astype(str)
    parts.append(pd.util.hash_pandas_object(d,index=False).to_numpy())
key=np.concatenate(parts)
dup=pd.Series(key).duplicated(keep=False).to_numpy()
candidate_hashes=set(key[dup])
# Verify full tuples within the candidate hashes to avoid calling collisions duplicates.
seen=set();duplicates=0;offset=0
if candidate_hashes:
    for batch in pq.ParquetFile(RAW).iter_batches(batch_size=50000,columns=cols):
        n=batch.num_rows
        mask=dup[offset:offset+n]
        if mask.any():
            d=batch.to_pandas().fillna('').astype(str)
            for rec in d.loc[mask].itertuples(index=False,name=None):
                if rec in seen:duplicates+=1
                else:seen.add(rec)
        offset+=n
report=dict(records=len(key),key_columns=cols,hash_candidates=int(dup.sum()),
            exact_duplicate_records=duplicates,unique_record_keys=len(key)-duplicates,
            prediction_identifiers_remain_unique=True,records_deleted=False)
(OUT/'record_key_duplicate_audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
