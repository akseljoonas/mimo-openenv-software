"""Deterministic technical reference repair; never ship in training images."""
from pathlib import Path
import subprocess

for relative, indent in [('rfc7515/jws.py', '        '), ('rfc7516/jwe.py', '    ')]:
    path = Path('/app/vendor/authlib/authlib/jose') / relative
    source = path.read_text()
    old = indent + 'elif key is None and "jwk" in header:\n' + indent + '    key = header["jwk"]'
    new = indent + 'if key is None:\n' + indent + '    raise ValueError("An explicit trusted key is required")'
    assert source.count(old) == 1
    path.write_text(source.replace(old, new))
subprocess.run(['python3', '/app/run_repair_check.py'], check=True)
