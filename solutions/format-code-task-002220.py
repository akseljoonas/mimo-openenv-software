"""Reference repair for validation only; excluded from training images."""
from pathlib import Path

path = Path('pandas/io/excel/_openpyxl.py')
text = path.read_text()
marker = '        self.book.save(self.handles.handle)'
assert text.count(marker) == 1
text = text.replace(marker, '''        if "r+" in self.mode:
            self.handles.handle.seek(0)
        self.book.save(self.handles.handle)
        if "r+" in self.mode:
            self.handles.handle.truncate()''')
path.write_text(text)
