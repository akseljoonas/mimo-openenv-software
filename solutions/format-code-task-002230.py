"""Reference repair for validation only; excluded from training images."""
from pathlib import Path

path = Path('pandas/io/parsers/python_parser.py')
text = path.read_text()
marker = '        self._no_thousands_columns = no_thousands_columns'
assert text.count(marker) == 1
text = text.replace(marker, '''        from pandas.core.dtypes.common import is_string_dtype
        if self.dtype is not None:
            if no_thousands_columns is None:
                no_thousands_columns = set()
            for position, column in zip(self._col_indices, self.columns):
                dtype = self.dtype
                if is_dict_like(dtype):
                    dtype = dtype.get(column, dtype.get(position))
                if dtype is not None and is_string_dtype(dtype):
                    no_thousands_columns.add(position)
        self._no_thousands_columns = no_thousands_columns''')
path.write_text(text)
