"""Reference repair for validation only; excluded from training images."""
from pathlib import Path

path = Path('pdfplumber/utils/text.py')
with path.open('a') as output:
    output.write('''

def dedupe_chars(chars, tolerance=1, extra_attrs=("fontname", "size")):
    groups = {}
    for index, char in enumerate(chars):
        key = tuple(char[attr] for attr in ("upright", "text", *extra_attrs))
        groups.setdefault(key, []).append(index)
    retained = []
    for indices in groups.values():
        for y_group in cluster_objects(indices, lambda i: chars[i]["doctop"], tolerance):
            for xy_group in cluster_objects(y_group, lambda i: chars[i]["x0"], tolerance):
                retained.append(min(xy_group, key=lambda i: (chars[i]["doctop"], chars[i]["x0"])))
    return [chars[index] for index in sorted(retained)]
''')
path = Path('pdfplumber/utils/__init__.py')
with path.open('a') as output:
    output.write('\nfrom .text import dedupe_chars\n')
