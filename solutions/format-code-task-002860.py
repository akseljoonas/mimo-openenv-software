"""Reference repair for validation only; excluded from training images."""
from pathlib import Path

path = Path('sqlglot/dialects/bigquery.py')
text = path.read_text()
text = text.replace('**parser.Parser.FUNCTIONS,', '**parser.Parser.FUNCTIONS,\n            "COUNTIF": exp.CountIf.from_arg_list,', 1)
marker = 'class Generator('
head, tail = text.split(marker, 1)
tail = tail.replace('TRANSFORMS = {', 'TRANSFORMS = {\n            exp.CountIf: rename_func("COUNTIF"),', 1)
path.write_text(head + marker + tail)
