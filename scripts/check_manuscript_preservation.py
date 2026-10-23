"""Verify preservation of the Annual Review; no estimation or code review."""
from pathlib import Path
import hashlib, json, re

R = Path(__file__).resolve().parents[1]
B = R / 'drafts/annual_review_pdf_baseline/main.tex'
M = R / 'drafts/manuscript/main.tex'


def check():
    original = B.read_text(encoding='utf-8-sig')
    active = M.read_text(encoding='utf-8-sig')
    blocks = re.findall(r'\\begin\{(table|sidewaystable|xltabular)\}(.*?)\\end\{\1\}', original, re.S)
    ledger = []
    for i, (kind, body) in enumerate(blocks, 1):
        block = '\\begin{' + kind + '}' + body + '\\end{' + kind + '}'
        label = re.search(r'\\label\{([^}]+)\}', body)
        caption = re.search(r'\\caption(?:\[[^\]]*\])?\{([^}]+)\}', body)
        retained = block in active
        assert retained, f'Original table changed or missing: {label or caption or i}'
        ledger.append({'index': i, 'environment': kind,
                       'label': label.group(1) if label else '',
                       'caption': caption.group(1) if caption else '',
                       'sha256': hashlib.sha256(block.encode()).hexdigest(),
                       'retained_verbatim': retained})
    conclusion = original.split(r'\section{Conclusion}\label{sec:conclusion}',1)[1].split(r'\clearpage',1)[0]
    assert conclusion in active, 'Original conclusion was changed'
    original_cases = original.split(r'\section{Examples of platform dialogue across different scenarios}',1)[1].split(r'\bibliographystyle',1)[0]
    assert original_cases in active, 'Original dialogue examples were removed or changed'
    for path in ['Figure 2.png', 'Figure 4.png', 'Figure 5.png']:
        assert ('figures/' + path) in active
    def expand(text):
        def sub(m):
            p=M.parent/m.group(1)
            if not p.suffix:p=p.with_suffix('.tex')
            return expand(p.read_text(encoding='utf-8-sig'))
        return re.sub(r'\\input\{([^}]+)\}',sub,text)
    full=expand(active)
    labels=re.findall(r'\\label\{([^}]+)\}',full)
    refs=re.findall(r'\\(?:ref|eqref)\{([^}]+)\}',full)
    assert len(labels)==len(set(labels)), 'Duplicate labels'
    assert not set(refs)-set(labels),set(refs)-set(labels)
    bib=(M.parent/'references.bib').read_text(encoding='utf-8-sig')
    keys=set(re.findall(r'@\w+\s*\{\s*([^,]+)',bib))
    cited=set(k.strip() for g in re.findall(r'\\cite\w*(?:\[[^\]]*\])*\{([^}]+)\}',full) for k in g.split(','))
    assert not cited-keys,cited-keys
    result={'scope':'Document preservation and references only; not empirical revalidation.',
            'original_table_environments':len(ledger),'all_original_table_blocks_retained_verbatim':True,
            'original_conclusion_retained_verbatim':True,'original_dialogue_examples_retained_verbatim':True,
            'original_figures_retained':3,'active_resolved_labels':len(labels),
            'resolved_citation_keys':len(cited),'tables':ledger}
    target=R/'docs/revision/annual_review_preservation_2026-10-23.json'
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='tables'},indent=2))
    return result


if __name__=='__main__':check()
