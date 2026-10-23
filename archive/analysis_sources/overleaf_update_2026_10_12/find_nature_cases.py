"""Find genuine short nature examples without returns or model-score selection."""
from pathlib import Path
import json
import re
import pandas as pd
import pyarrow.parquet as pq

ROOT=Path("D:/draft")
RAW=ROOT/"data/working/gpu_migration_2026_10_07/iip_topic_gpu/data/raw_qna.parquet"
OUT=ROOT/"data/working/overleaf_update_2026-10-12"
rows=[]
offset=0
for b in pq.ParquetFile(RAW).iter_batches(batch_size=100000,columns=["Scode","Coname","Qtm","Recvtm","Qsubj","Reply"]):
    d=b.to_pandas()
    q=d.Qsubj.fillna("").astype(str)
    r=d.Reply.fillna("").astype(str)
    mask=q.str.contains("提前.{0,5}(透露|告知|公布)|未公开|未披露|商业秘密|是不是.{0,12}(不|没有)",regex=True)
    mask&=q.str.len().between(15,200)&r.str.len().between(5,360)
    for index,row in d.loc[mask].iterrows():
        rows.append({"source_row_id":offset+int(index),**row.to_dict()})
        if len(rows)>=35:break
    offset+=len(d)
    if len(rows)>=35:break
OUT.mkdir(parents=True,exist_ok=True)
(OUT/"nature_candidates.json").write_text(json.dumps(rows,ensure_ascii=False,indent=2,default=str),encoding="utf-8")
print(json.dumps(rows,ensure_ascii=False,indent=2,default=str))
