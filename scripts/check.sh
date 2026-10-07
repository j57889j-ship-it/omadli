#!/usr/bin/env bash
set -euo pipefail
python -m compileall -q app alembic
PYTHONPATH=. pytest -q
python - <<'PY'
from pathlib import Path
import re
root = Path('app')
callbacks = set()
for p in root.rglob('*.py'):
    s = p.read_text(encoding='utf-8', errors='ignore')
    callbacks.update(re.findall(r"['\"]((?:admin|user|rank|book|books|quiz|answer|report|profile|favorite|cat|sub|setting|cleanup):[^'\"]*)['\"]", s))
patterns = []
for p in (root / 'handlers').rglob('*.py'):
    s = p.read_text(encoding='utf-8', errors='ignore')
    patterns += re.findall(r"F\.data\s*==\s*['\"]([^'\"]+)['\"]", s)
    patterns += [x + '*' for x in re.findall(r"F\.data\.startswith\(['\"]([^'\"]+)['\"]\)", s)]
missing = [c for c in sorted(callbacks) if not any((p.endswith('*') and c.startswith(p[:-1])) or (not p.endswith('*') and c == p) for p in patterns)]
if missing:
    raise SystemExit(f'Callback route mismatch: {missing}')
text = '\n'.join(p.read_text(encoding='utf-8', errors='ignore') for p in root.rglob('*.py'))
for phrase in ('HAFTALIK TOP', 'OYLIK TOP', 'MAVSUM TOP'):
    if phrase in text:
        raise SystemExit(f'Removed ranking still present: {phrase}')
print('V29 static checks: PASS')
PY
