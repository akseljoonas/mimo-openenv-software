"""Deterministic reference repair; verification fixture only."""
from pathlib import Path

path = Path('/testbed/fastavro/json_write.py')
source = path.read_text()
old = 'def json_writer(fo, schema, records, *, write_union_type=True):'
assert source.count(old) == 1
source = source.replace(old, 'def json_writer(fo, schema, records, *, write_union_type=True, validator=None):')
old = 'AvroJSONEncoder(fo, write_union_type=write_union_type), schema, records\n'
assert source.count(old) == 1
source = source.replace(old, 'AvroJSONEncoder(fo, write_union_type=write_union_type), schema, records, validator=validator\n')
path.write_text(source)
