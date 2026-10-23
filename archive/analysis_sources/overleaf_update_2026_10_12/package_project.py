"""Build a complete, minimal Overleaf project from active local dependencies."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil
import zipfile

ROOT = Path("D:/draft")
MAN = ROOT / "drafts/manuscript"
OUT = ROOT / "drafts/revision/overleaf_packages/2026-10-12"
VERIFY = ROOT / "data/verification/overleaf_update_2026-10-12"

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def active(s):
    return re.sub(r"\\iffalse\b.*?\\fi\b", "", s, flags=re.S)

def build(name):
    OUT.mkdir(parents=True, exist_ok=True)
    VERIFY.mkdir(parents=True, exist_ok=True)
    files = set()
    def add(p):
        p = p.resolve()
        assert p.is_relative_to(MAN.resolve()), str(p)
        assert p.is_file(), str(p)
        if p in files:
            return
        files.add(p)
        if p.suffix != ".tex":
            return
        s = active(p.read_text(encoding="utf-8"))
        for x in re.findall(r"\\(?:input|include)\{([^}]+)\}", s):
            target = MAN / x
            add(target if target.suffix else target.with_suffix(".tex"))
        for x in re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", s):
            target = MAN / x
            if not target.suffix:
                matches = [target.with_suffix(e) for e in [".pdf",".png",".jpg",".jpeg"] if target.with_suffix(e).exists()]
                assert len(matches) == 1, (x, matches)
                target = matches[0]
            add(target)
        for x in re.findall(r"\\bibliography\{([^}]+)\}", s):
            for bib in x.split(","):
                add(MAN / (bib + ".bib"))
        for x in re.findall(r"\\bibliographystyle\{([^}]+)\}", s):
            bst = MAN / (x + ".bst")
            if bst.exists():
                add(bst)
    add(MAN / "main.tex")
    target = OUT / (name + ".zip")
    assert not target.exists(), "Do not overwrite an earlier package"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in sorted(files):
            z.write(p, p.relative_to(MAN).as_posix())
        z.writestr("OVERLEAF_README.md",
            "# Overleaf upload\n\nUpload this ZIP as a new project. Select main.tex as the main document and XeLaTeX as the compiler. "
            "Keep tables/ and figures/ paths. The project uses natbib and BibTeX, not biber. "
            "ctex selects its available CJK font set on the host.\n\n"
            "This is a working manuscript, not a scientific certification. Raw data, model files, private notes and compiled auxiliary files are excluded. "
            "Assistant topic labels have not received independent human validation. Existing empirical limitations remain applicable.\n")
        z.writestr(".latexmkrc", "$pdf_mode = 5;\n")
    with zipfile.ZipFile(target) as z:
        assert z.testzip() is None
        for p in files:
            assert hashlib.sha256(z.read(p.relative_to(MAN).as_posix())).hexdigest() == digest(p)
    report = dict(archive=str(target),bytes=target.stat().st_size,sha256=digest(target),
                  main_sha256=digest(MAN/"main.tex"),source_file_count=len(files),
                  files={p.relative_to(MAN).as_posix():digest(p) for p in sorted(files)},
                  raw_data_included=False,compiler="XeLaTeX",bibliography="BibTeX")
    (VERIFY/(name+"_manifest.json")).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    if name.startswith("01_"):
        shutil.copy2(MAN/"main.tex",VERIFY/"main_before_revision.tex")
        shutil.copy2(MAN/"references.bib",VERIFY/"references_before_revision.bib")
    print(json.dumps({k:v for k,v in report.items() if k!="files"},ensure_ascii=False,indent=2))

if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--name",required=True)
    build(parser.parse_args().name)
