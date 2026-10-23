"""Format curated genuine Q&A examples and emit a scoped main.tex patch."""
from pathlib import Path
import difflib
import hashlib
import json
import re
import pandas as pd
import pyarrow.parquet as pq

ROOT=Path("D:/draft")
MAN=ROOT/"drafts/manuscript"
SRC=ROOT/"data/working/full_topic_2026-10-11/accepted_R005_V002"
RAW=ROOT/"data/working/gpu_migration_2026_10_07/iip_topic_gpu/data/raw_qna.parquet"
OUT=ROOT/"data/verification/overleaf_update_2026-10-12"
curated=json.loads(Path(__file__).with_name("case_translations.json").read_text(encoding="utf-8"))
taxonomy=json.loads((SRC/"task/docs/taxonomy_19_content.json").read_text(encoding="utf-8-sig"))
topics={t["code"]:t["paper_label"] for t in taxonomy["content"]}
natures={1:"Answers or explanations",2:"Correct misunderstandings",3:"Verify rumors",
         4:"Inappropriate questions",5:"Suggestions or others"}
assert [r["code"] for r in curated["topics"]]==list(range(1,20))
assert [r["code"] for r in curated["natures"]]==list(range(1,6))
ids={r["id"] for group in curated.values() for r in group}
assert max(ids)<100000
data=next(pq.ParquetFile(RAW).iter_batches(batch_size=100000,
           columns=["Scode","Coname","Qtm","Recvtm","Qsubj","Reply"])).to_pandas()

def clean(s):
    return re.sub(r"\s+"," ",re.sub(r"<[^>]+>"," ",str(s))).strip()
def tex(s):
    mapping={"\\":r"\textbackslash{}","&":r"\&","%":r"\%","$":r"\$","#":r"\#",
             "_":r"\_","{":r"\{","}":r"\}","~":r"\textasciitilde{}","^":r"\textasciicircum{}"}
    return "".join(mapping.get(c,c) for c in s)
def day(s):
    return pd.Timestamp(s).strftime("%d %B %Y").lstrip("0")

frozen=json.loads((SRC/"examples/topic_examples.json").read_text(encoding="utf-8"))
for case in frozen["examples"]:
    r=data.loc[case["source_row_id"]]
    assert clean(r.Qsubj)==case["question_cleaned"]
    assert clean(r.Reply)==case["reply_cleaned"]

blocks=[r"\textit{Characteristics: Content describes the subject discussed, while question nature describes the purpose of the inquiry. The examples cover all 19 content categories and all five nature categories. Labels illustrate assistant interpretation rather than independent validation. English text summarizes the Chinese wording. Chinese text preserves the source wording after removing HTML and normalizing whitespace. Longer replies are explicitly marked as excerpts. Firm names follow the supplier records. Examples were not selected using stock returns.}",
        "",r"\subsubsection*{Content categories}",""]
records=[]
number=10
for group in ["topics","natures"]:
    if group=="natures":
        blocks.extend([r"\clearpage",r"\subsubsection*{Question nature categories}",""])
    for j,c in enumerate(curated[group]):
        r=data.loc[c["id"]]
        label=(topics if group=="topics" else natures)[c["code"]]
        q=clean(r.Qsubj)
        fragments=c.get("excerpt")
        if fragments:
            fragments=[fragments] if isinstance(fragments,str) else fragments
            assert all(clean(s) in clean(r.Reply) for s in fragments), c["id"]
            reply=r" \ldots{} ".join(tex(clean(s)) for s in fragments)
            reply_header=r"\textbf{Reply (excerpt):}"
        else:
            reply=tex(clean(r.Reply))
            reply_header=r"\textbf{Reply:}"
        if j%2==0 and j>0:
            blocks.append(r"\clearpage")
        elif j>0:
            blocks.append(r"\vspace{0.4cm}")
        blocks.extend([
            r"\noindent \textbf{Example "+str(number)+": "+tex(label)+r"} \\",
            r"\textbf{"+tex(clean(r.Coname))+r"} [Stock Code: "+str(r.Scode)+r"]. Question: "+day(r.Qtm)+". Reply: "+day(r.Recvtm)+r". \\",
            r"\textit{"+("Content" if group=="topics" else "Question nature")+": "+tex(label)+r". Source record: "+str(c["id"])+r".} \\",
            r"\textbf{Question:} "+tex(c["q"])+" ("+tex(q)+r") \\",
            reply_header+" "+tex(c["r"])+" ("+reply+r") \\",
            r"\textbf{Classification rationale:} "+tex(c["why"]),"",
        ])
        records.append(dict(example=number,group=group,code=c["code"],source_row_id=c["id"],
            question_sha256=hashlib.sha256(q.encode()).hexdigest(),
            reply_sha256=hashlib.sha256(clean(r.Reply).encode()).hexdigest(),
            excerpt=bool(fragments),source_question_date=str(r.Qtm),source_reply_date=str(r.Recvtm)))
        number+=1
target=MAN/"tables/topic_nature_examples_2026-10-12.tex"
target.write_text("\n".join(blocks)+"\n",encoding="utf-8")
main=MAN/"main.tex"
old=main.read_text(encoding="utf-8")
start=old.index(r"\subsection{Examples of content and question nature classification}")
end=old.index(r"\bibliographystyle",start)
replacement=(r"\subsection{Examples of content and question nature classification}\label{app:topic_cases}"+"\n\n"+
             r"\input{tables/topic_nature_examples_2026-10-12.tex}"+"\n\n"+r"\clearpage"+"\n")
new=old[:start]+replacement+old[end:]
diff=list(difflib.unified_diff(old.splitlines(),new.splitlines(),n=3))
patch="*** Begin Patch\n*** Update File: D:/draft/drafts/manuscript/main.tex\n"
for line in diff[2:]:
    patch+=("@@\n" if line.startswith("@@") else line+"\n")
patch+="*** End Patch\n"
OUT.mkdir(parents=True,exist_ok=True)
(OUT/"main_d6.patch").write_text(patch,encoding="utf-8")
(OUT/"case_sources.json").write_text(json.dumps({
    "raw_source":str(RAW),"topic_cases":19,"nature_cases":5,
    "unique_raw_pairs":len(ids),"all_frozen_topic_texts_match_raw":True,
    "all_excerpts_substrings_of_original":True,"independent_validation":False,
    "records":records},ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps({"tex":str(target),"topic_cases":19,"nature_cases":5,"pairs":len(ids),"patch":str(OUT/"main_d6.patch")}))
