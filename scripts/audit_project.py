"""Check the active document, notebook entry points and public release boundary."""
from pathlib import Path
import ast, json, re, subprocess, sys
R=Path(__file__).resolve().parents[1]

def active_tex(path):
    s=path.read_text(encoding='utf-8-sig')
    def expand(m):
        child=R/'drafts/manuscript'/m.group(1)
        if not child.suffix:child=child.with_suffix('.tex')
        assert child.is_file(),child
        return active_tex(child)
    return re.sub(r'\\input\{([^}]+)\}',expand,s)

def run():
    s=active_tex(R/'drafts/manuscript/main.tex')
    labels=re.findall(r'\\label\{([^}]+)\}',s)
    refs=re.findall(r'\\(?:ref|eqref)\{([^}]+)\}',s)
    assert len(labels)==len(set(labels)),'Duplicate labels'
    assert not set(refs)-set(labels),set(refs)-set(labels)
    bib=(R/'drafts/manuscript/references.bib').read_text(encoding='utf-8-sig')
    keys=set(re.findall(r'@\w+\s*\{\s*([^,]+)',bib))
    cited=set(k.strip() for group in re.findall(r'\\cite\w*(?:\[[^\]]*\])*\{([^}]+)\}',s) for k in group.split(','))
    assert not cited-keys,cited-keys
    from check_manuscript_preservation import check
    check()
    # All active notebooks execute their light, aggregate-only entry cells.
    notebook_count=0
    for p in sorted((R/'notebooks').rglob('*.ipynb')):
        nb=json.loads(p.read_text(encoding='utf-8'))
        ns={'display':lambda *_args,**_kwargs:None,'__name__':'__notebook_check__'}
        for cell in nb['cells']:
            if cell['cell_type']=='code':
                code=''.join(cell['source']);ast.parse(code)
                exec(compile(code,str(p),'exec'),ns)
        notebook_count+=1
    for p in list((R/'scripts').glob('*.py'))+list((R/'src').rglob('*.py')):
        ast.parse(p.read_text(encoding='utf-8'))
    # Audit only intended Git content, not ignored licensed local material.
    raw=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=R)
    files=[Path(x.decode('utf-8')) for x in raw.split(b'\0') if x]
    forbidden=[];total=0
    for rel in files:
        p=R/rel
        if not p.is_file():continue
        total+=p.stat().st_size
        if p.stat().st_size>20_000_000:forbidden.append(str(rel)+' (large)')
        if any(x in rel.parts for x in ['local_private','build','__pycache__']):forbidden.append(str(rel))
        if p.suffix.lower() in ['.parquet','.npz','.pkl','.pt','.safetensors','.key','.pem']:forbidden.append(str(rel))
        if rel.parts[:2] in [('data','raw'),('data','processed'),('data','temp')] and p.name!='README.md':forbidden.append(str(rel))
        if p.suffix.lower()=='.csv':
            header=p.open(encoding='utf-8-sig').readline().strip().split(',')
            if any(x in header for x in ['Stkcd','source_row_id','Question','Reply','question_text','reply_text']):forbidden.append(str(rel)+' (record-level schema)')
    assert not forbidden,forbidden
    result={'active_labels':len(labels),'resolved_citation_keys':len(cited),
            'active_notebooks_executed':notebook_count,'public_candidate_files':len(files),
            'public_candidate_bytes':total,'forbidden_files':forbidden,
            'scope':'Structural, runtime and release checks; not a new literature or semantic audit.'}
    (R/'docs/provenance/project_audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))

if __name__=='__main__':run()
