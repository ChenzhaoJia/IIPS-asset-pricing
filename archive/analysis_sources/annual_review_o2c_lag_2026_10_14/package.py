from pathlib import Path
import json,zipfile,hashlib
from prepare import ROOT,digest,save

assert json.loads((ROOT/'publish_manifest.json').read_text())['status']=='published'
archive=ROOT.with_suffix('.zip');assert not archive.exists()
files=[p for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
hashes={p.relative_to(ROOT).as_posix():digest(p) for p in files}
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=5) as z:
    for p in files:z.write(p,p.relative_to(ROOT).as_posix())
    z.writestr('FILE_SHA256.json',json.dumps(hashes,ensure_ascii=False,indent=2))
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for name,expected in hashes.items():assert hashlib.sha256(z.read(name)).hexdigest()==expected,name
save('final_delivery.json',dict(status='CRC_and_all_member_SHA256_passed',archive=str(archive),bytes=archive.stat().st_size,files=len(files)+1,sha256=digest(archive)))
print(json.dumps(json.loads((ROOT/'final_delivery.json').read_text()),indent=2),flush=True)
