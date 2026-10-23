"""Check revised source, unchanged LR, compiled labels and package coverage."""
from pathlib import Path
import json
import hashlib
import re
import sys
import zipfile
ROOT=Path("D:/draft")
V=ROOT/"data/verification/overleaf_update_2026-10-12"
M=ROOT/"drafts/manuscript"
main=(M/"main.tex").read_text(encoding="utf-8")
before=(V/"main_before_revision.tex").read_text(encoding="utf-8")
def active(s):return re.sub(r"\\iffalse\b.*?\\fi\b","",s,flags=re.S)
def section(s,start,end):return s[s.index(start):s.index(end,s.index(start))]
lr_same=section(main,r"\section{Literature review}",r"\section{Data")==section(before,r"\section{Literature review}",r"\section{Data")
assert lr_same
manifest=json.loads((V/"03_C2C_CH4_FF3_Overleaf_manifest.json").read_text())
archive=Path(manifest["archive"])
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for name,sha in manifest["files"].items():
        assert hashlib.sha256(z.read(name)).hexdigest()==sha
        assert hashlib.sha256((M/name).read_bytes()).hexdigest()==sha
    packed_bytes=z.read("main.tex")
assert packed_bytes==(M/"main.tex").read_bytes()
compiled=(V/"compiled/overleaf_update_2026_10_12.log").read_text(encoding="utf-8",errors="replace")
assert not re.search(r"undefined|Overfull|multiply defined|Label\(s\) may",compiled,re.I)
a=active(main)
removed=["fig:content_return_path","fig:topic_annual_coverage","fig:paired_topic_map","fig:topic_reply_lag"]
assert all(x not in a for x in removed)
assert "Examples from the frozen full archive classifier" not in a
assert len(re.findall(r"\\begin\{figure\}",a))==4
cases=(M/"tables/topic_nature_examples_2026-10-12.tex").read_text(encoding="utf-8")
assert len(re.findall(r"\\textbf\{Example \d+",cases))==24
report=dict(state="passed",literature_review_unchanged=lr_same,
    packaged_source_matches_disk=True,package_crc_and_all_hashes_passed=True,
    active_figures=4,new_cases=24,undefined_citations_or_refs=False,
    overfull_boxes=False,remaining_warning="Inherited variable definition long table infinite glue shrinkage",
    archive=str(archive),archive_sha256=manifest["sha256"],
    working_pdf=str(M/"Draft_C2C_CH4_FF3_2026-10-12.pdf"),
    main_sha256=hashlib.sha256((M/"main.tex").read_bytes()).hexdigest(),
    scientific_finalization=False,independent_human_classification_validation=False)
(V/"final_package_check.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(report,ensure_ascii=False,indent=2))
