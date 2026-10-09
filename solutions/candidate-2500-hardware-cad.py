"""Deterministic technical reference repair; never ship in training images."""
import json
from pathlib import Path
import sys

root = Path('/app/vendor/openscad_parser/src/openscad_parser/ast')
path = root / 'builder.py'
source = path.read_text()
old = '''        end = children[1]
        # Step is optional - if present, use it; otherwise default to 1.0
        step = children[2] if len(children) > 2 else NumberLiteral(val=1.0, position=self._get_node_position(node))'''
new = '''        end = children[2] if len(children) > 2 else children[1]
        step = children[1] if len(children) > 2 else NumberLiteral(val=1.0, position=self._get_node_position(node))'''
assert source.count(old) == 1
path.write_text(source.replace(old, new))
path = root / 'nodes.py'
source = path.read_text()
old = 'return f"[{self.start} : {self.end} : {self.step}]"'
assert source.count(old) == 1
path.write_text(source.replace(old, 'return f"[{self.start} : {self.step} : {self.end}]"'))
sys.path.insert(0, str(root.parent.parent))
from openscad_parser.ast import NumberLiteral, UnaryMinusOp, getASTfromString


def number(expression):
    if isinstance(expression, NumberLiteral):
        return expression.val
    if isinstance(expression, UnaryMinusOp):
        return -number(expression.expr)
    raise ValueError(type(expression).__name__)


result = {'output_schema_version': 'openscad-range-repair.v1', 'source': 'cad_models.scad', 'ranges': {}}
for assignment in getASTfromString(Path('/app/cad_models.scad').read_text(), origin='cad_models.scad'):
    node = assignment.expr
    rendered = str(node)
    roundtrip = getASTfromString('probe = ' + rendered + ';')[0].expr
    values = {key: number(getattr(node, key)) for key in ['start', 'step', 'end']}
    stable = all(values[key] == number(getattr(roundtrip, key)) for key in values)
    result['ranges'][assignment.name.name] = {**values, 'rendered': rendered, 'roundtrip_stable': stable}
Path('/app/output.json').write_text(json.dumps(result))
