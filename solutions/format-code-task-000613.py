"""Reference repair for validation only; excluded from training images."""
import ast
from pathlib import Path

table_methods = '''

    def to_csv(self, path, **kwargs):
        options = dict(encoding="utf-8", index=False, header=False, quoting=1)
        options.update(kwargs)
        self.df.to_csv(path, **options)

    def to_json(self, path, **kwargs):
        mode = kwargs.pop("mode", "w")
        options = dict(orient="records")
        options.update(kwargs)
        with open(path, mode, encoding="utf-8") as output:
            output.write(self.df.to_json(**options))

    def to_excel(self, path, **kwargs):
        options = dict(sheet_name=f"page-{self.page}-table-{self.order}", index=False, header=False)
        options.update(kwargs)
        self.df.to_excel(path, **options)

    def to_html(self, path, **kwargs):
        mode = kwargs.pop("mode", "w")
        with open(path, mode, encoding="utf-8") as output:
            output.write(self.df.to_html(**kwargs))

    def to_markdown(self, path, **kwargs):
        mode = kwargs.pop("mode", "w")
        with open(path, mode, encoding="utf-8") as output:
            output.write(self.df.to_markdown(**kwargs))

    def to_sqlite(self, path, **kwargs):
        import sqlite3
        options = dict(name=f"page-{self.page}-table-{self.order}", if_exists="replace", index=False)
        options.update(kwargs)
        with sqlite3.connect(path) as connection:
            self.df.to_sql(con=connection, **options)
'''

list_methods = '''

    def export(self, path, f="csv", compress=False):
        import tempfile
        import zipfile
        from pathlib import Path
        import pandas as pd

        if f not in ("csv", "json", "html", "markdown", "excel", "sqlite"):
            raise ValueError("Unsupported export format")
        destination = Path(path)

        def write_files(target):
            if f == "excel":
                with pd.ExcelWriter(target) as writer:
                    for table in self:
                        table.to_excel(writer)
                return [target]
            if f == "sqlite":
                for table in self:
                    table.to_sqlite(target)
                return [target]
            files = []
            for table in self:
                filename = target.with_name(f"{target.stem}-page-{table.page}-table-{table.order}{target.suffix}")
                getattr(table, "to_" + f)(filename)
                files.append(filename)
            return files

        if compress:
            with tempfile.TemporaryDirectory() as directory:
                files = write_files(Path(directory) / destination.name)
                with zipfile.ZipFile(destination.with_suffix(".zip"), "w", zipfile.ZIP_DEFLATED) as archive:
                    for filename in files:
                        archive.write(filename, filename.name)
        else:
            write_files(destination)
'''

path = Path('camelot/core.py')
text = path.read_text()
tree = ast.parse(text)
lines = text.splitlines(keepends=True)
insertions = []
for node in tree.body:
    if isinstance(node, ast.ClassDef) and node.name in ('Table', 'TableList'):
        insertions.append((node.end_lineno, table_methods if node.name == 'Table' else list_methods))
assert len(insertions) == 2
for index, methods in sorted(insertions, reverse=True):
    lines.insert(index, methods + '\n')
path.write_text(''.join(lines))
