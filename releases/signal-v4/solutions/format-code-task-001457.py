"""Deterministic reference repair; verification fixture only."""
from pathlib import Path

path = Path('/testbed/src/action.js')
source = path.read_text()
old = "core.getInput('secrets', { required: true })"
assert source.count(old) == 1
source = source.replace(old, "core.getInput('secrets', { required: false })")
assert source.count('const secrets = secretsInput\n') == 1
source = source.replace('const secrets = secretsInput\n', "const secrets = (secretsInput || '')\n")
path.write_text(source)

path = Path('/testbed/action.yml')
source = path.read_text()
begin = source.index('  secrets:\n')
end = source.index('  namespace:\n', begin)
section = source[begin:end]
assert section.count('required: true') == 1
path.write_text(source[:begin] + section.replace('required: true', 'required: false') + source[end:])
