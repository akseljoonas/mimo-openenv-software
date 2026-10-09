"""Deterministic technical reference repair; never ship in training images."""
import os
from pathlib import Path
import subprocess

root = Path('/app/vendor/partitura/partitura/io')
path = root / 'importmusicxml.py'
source = path.read_text()
old = '''    chord = e.find("chord")
    is_grace_chord = False
    if chord is not None:'''
new = '''    chord = e.find("chord")
    is_grace_chord = False
    if chord is not None and prev_note is None:
        warnings.warn("Chord member has no preceding anchor; preserving a standalone note")
        chord = None
    if chord is not None:'''
assert source.count(old) == 1
path.write_text(source.replace(old, new))
path = root / 'exportmidi.py'
source = path.read_text()
old = '    ppq = get_ppq(parts)'
new = '''    import warnings
    parts = list(score.iter_parts(list(parts)))
    if not parts:
        raise ValueError("Score has no parts")
    ppq = get_ppq(parts)'''
assert source.count(old) == 1
source = source.replace(old, new)
old = '        ppq = ppq * 2\n'
new = '''        ppq = ppq * 2
    if ppq > 32767:
        warnings.warn("MIDI PPQ exceeds 32767; timing is rounded", RuntimeWarning)
        ppq = 32767
'''
assert source.count(old) == 1
path.write_text(source.replace(old, new))
environment = dict(os.environ, PYTHONPATH='/app/vendor/partitura')
subprocess.run(['python3', '/app/run_boundary_workflow.py'], env=environment, check=True)
