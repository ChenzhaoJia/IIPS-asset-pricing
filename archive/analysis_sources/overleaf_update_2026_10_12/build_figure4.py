"""Render the unchanged content counts and plain question-nature totals."""
from pathlib import Path
from html import escape
import json
import pandas as pd

ROOT=Path("D:/draft")
SRC=ROOT/"data/working/full_topic_2026-10-11/accepted_R005_V002"
VER=ROOT/"data/verification/figure4_and_sep_feedback_2026-10-11"
FIG=ROOT/"drafts/manuscript/figures"
OUT=ROOT/"data/verification/overleaf_update_2026-10-12"

def main():
    content=pd.read_csv(SRC/"reports/CONTENT_DISTRIBUTION.csv")
    nature=pd.read_csv(VER/"nature_distribution_independently_recounted.csv")
    taxonomy=json.loads((SRC/"task/docs/taxonomy_19_content.json").read_text(encoding="utf-8-sig"))
    labels={x["code"]:x["paper_label"] for x in taxonomy["content"]}
    labels.update({5:"Infringement and disputes",12:"Operation: assets",13:"Operation: products",
                   14:"Operation: industry",15:"Operation: macroeconomy",16:"Operation: others"})
    assert int(nature.candidate_count.sum())==5836155
    assert int(content.question_assigned_count.sum())==3182822
    assert int(content.reply_assigned_count.sum())==3763518
    blue,orange="#245377","#bb8a50"
    w,h,left,extent=1100,1000,435,610
    svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
         f'<rect width="{w}" height="{h}" fill="white"/>',
         '<g font-family="Georgia, Times New Roman, serif" font-size="21" fill="#222">']
    def text(x,y,s,anchor="start",bold=False):
        svg.append(f'<text x="{x}" y="{y}" text-anchor="{anchor}"'+
                   (' font-weight="bold"' if bold else '')+f'>{escape(s)}</text>')
    def rect(x,y,ww,hh,color):
        svg.append(f'<rect x="{x}" y="{y}" width="{ww:.3f}" height="{hh}" fill="{color}"/>')
    def grid(start,end,ticks,maximum):
        for v in ticks:
            x=left+extent*v/maximum
            svg.append(f'<path d="M{x} {start} V{end}" stroke="#dedede" stroke-width="1"/>')
            text(x,end+28,str(v),"middle")
    text(12,28,"Panel A: Content of questions and replies",bold=True)
    rect(670,14,20,13,blue);text(699,28,"Questions")
    rect(885,14,20,13,orange);text(914,28,"Replies")
    grid(49,554,range(0,26,5),25)
    for j,r in enumerate(content.itertuples()):
        y=66+j*26
        text(left-15,y+7,labels[r.code],"end")
        rect(left,y-10,extent*(r.question_assigned_count/5836158*100)/25,10,blue)
        rect(left,y+3,extent*(r.reply_assigned_count/5836158*100)/25,10,orange)
    text(left+extent/2,611,"Percentage of all records on each side","middle")
    svg.append('<path d="M12 641 H1086" stroke="#777" stroke-width="1"/>')
    text(12,679,"Panel B: Nature of investor questions",bold=True)
    grid(702,907,range(0,101,20),100)
    for j,r in enumerate(nature.itertuples()):
        y=722+j*38
        text(left-15,y+7,"Inappropriate questions" if j==3 else r.label,"end")
        size=extent*r.candidate_count/5836155
        rect(left,y-12,size,24,blue)
        text(left+size+8,y+7,f"{r.candidate_percent:.2f}%")
    text(left+extent/2,980,"Percentage of all nonempty questions","middle")
    svg.append("</g></svg>")
    target=FIG/"full_content_and_nature_distribution_2026-10-12.svg"
    target.write_text("\n".join(svg),encoding="utf-8")
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"figure4_change.json").write_text(json.dumps({
        "output":str(target),"content_counts_unchanged":True,"nature_counts_unchanged":True,
        "review_flag_not_plotted":True,"internal_review_flags_unchanged":True,
        "independent_accuracy_not_claimed":True},indent=2),encoding="utf-8")
    print(target)

if __name__=="__main__": main()
