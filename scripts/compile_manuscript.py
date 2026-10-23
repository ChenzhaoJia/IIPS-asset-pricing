"""Compile the active manuscript with a local TeX Live/TinyTeX installation.

Set IIP_TEX_BIN when latexmk is not on PATH. Build outputs stay in build/latex.
"""
from pathlib import Path
import os, shutil, subprocess
R=Path(__file__).resolve().parents[1]

def run():
    env=os.environ.copy()
    if env.get('IIP_TEX_BIN'):env['PATH']=env['IIP_TEX_BIN']+os.pathsep+env['PATH']
    if (R/'build/texmf').exists():env['TEXMFHOME']=str(R/'build/texmf')
    exe=shutil.which('latexmk',path=env['PATH'])
    if not exe:raise SystemExit('Install TeX Live/TinyTeX or set IIP_TEX_BIN; see docs/REPRODUCING.md.')
    out=R/'build/latex';out.mkdir(parents=True,exist_ok=True)
    proc=subprocess.run([exe,'-norc','-pdf','-interaction=nonstopmode','-halt-on-error',
                         '-synctex=1','-outdir='+str(out),'main.tex'],
                        cwd=R/'drafts/manuscript',env=env,capture_output=True,text=True,errors='replace')
    (out/'compile_console.txt').write_text(proc.stdout+'\n'+proc.stderr,encoding='utf-8')
    if proc.returncode:raise SystemExit('Compilation failed: build/latex/compile_console.txt')
    log=(out/'main.log').read_text(errors='replace')
    bad=['Undefined control sequence','There were undefined references','Citation `','Overfull']
    if any(t in log for t in bad):raise SystemExit('Compile completed with issues requiring review; see main.log.')
    target=R/'drafts/manuscript/IIP_Integrated_2026-10-23.pdf'
    shutil.copy2(out/'main.pdf',target)
    print(target)

if __name__=='__main__':run()
