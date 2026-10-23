"""Package only edited manuscript inputs, never raw data or existing user PDFs."""
from pathlib import Path
import hashlib,json,zipfile
ROOT=Path('D:/draft')
MAN=ROOT/'drafts/manuscript'
OUT=ROOT/'drafts/revision/overleaf_pricing_mechanism_2026-10-11.zip'
files=[MAN/'main.tex',MAN/'references.bib',*sorted((MAN/'tables').glob('*.tex')),
       MAN/'figures/full_topic_distribution_2026-10-11.png']
with zipfile.ZipFile(OUT,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in files:z.write(p,p.relative_to(MAN).as_posix())
    z.writestr('REVISION_README.md',
        'Upload these files at the existing Overleaf project root, keeping tables/ and figures/ paths.\n'
        'Keep all existing figures and unrelated inputs. Earnings tests now use original CSMAR Annodt dates.\n'
        'The active earnings table is tables/public_earnings_announcements.tex. The older proxy table is inactive.\n'
        'Independent topic accuracy and analyst forecast errors remain pending. No raw data are included.\n')
with zipfile.ZipFile(OUT) as z:
    assert z.testzip() is None
report=dict(archive=str(OUT),bytes=OUT.stat().st_size,
 sha256=hashlib.sha256(OUT.read_bytes()).hexdigest(),
 inputs={p.relative_to(MAN).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
(ROOT/'data/verification/pricing_mechanism_2026-10-11/overleaf_package_manifest.json').write_text(
    json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({k:report[k] for k in ['archive','bytes','sha256']}))
