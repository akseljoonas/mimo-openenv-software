"""Deterministic reference repair; verification fixture only."""
from pathlib import Path

path = Path('/workspace/repo/src/pyromat/__init__.py')
source = path.read_text()
assert '\ndef get(' not in source
source += '''

def get(idstr):
    try:
        return dat.data[idstr]
    except KeyError:
        utility.print_error('No substance named ' + str(idstr) + ' was found.')
        raise utility.PMParamError('Invalid substance ID: ' + str(idstr))
'''
path.write_text(source)
