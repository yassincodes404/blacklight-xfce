#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,os
root=Path(__file__).resolve().parents[1]
result={}
for directory in ['home','assets','optional']:
 for p in sorted((root/directory).rglob('*')):
  if '__pycache__' in p.parts or p.suffix == '.pyc':continue
  if p.is_symlink():result[str(p.relative_to(root))]='symlink:'+os.readlink(p)
  elif p.is_file():result[str(p.relative_to(root))]=hashlib.sha256(p.read_bytes()).hexdigest()
(root/'manifests/content.sha256.json').write_text(json.dumps(result,indent=2)+'\n')
print(f'Recorded {len(result)} payload hashes.')
