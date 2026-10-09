"""Reference repair for validation only; excluded from training images."""
from pathlib import Path

path = Path('statsmodels/regression/rolling.py')
text = path.read_text()
replacements = [
    ("missing='drop'):", "missing='drop', expanding=False):"),
    ('        self._has_nan = self._find_nans()\n', '        self._expanding = bool(expanding)\n'),
    ("                             'regressors in the model and less than window')", "                             'regressors in the model and less than window')\n        self._has_nan = self._find_nans()"),
    ('has_nan[:w - 1] = False', 'has_nan[:(self._min_nobs if self._expanding else w) - 1] = False'),
    ('[idx - window:idx]', '[max(0, idx - window):idx]'),
    ('        xpx, xpy, nobs = self._reset(window)', '        first = self._min_nobs if self._expanding else window\n        xpx, xpy, nobs = self._reset(first)'),
    ('self._has_nan[window - 1]', 'self._has_nan[first - 1]'),
    ('self._fit_single(w, xpx', 'self._fit_single(first, xpx'),
    ('range(w + 1, self._x.shape[0] + 1)', 'range(first + 1, self._x.shape[0] + 1)'),
    ('if not self._is_nan[i - w - 1]:', 'if i > w and not self._is_nan[i - w - 1]:'),
    ('super().__init__(endog, exog, window, None, min_nobs, missing)', 'super().__init__(endog, exog, window, None, min_nobs, missing, expanding)'),
]
for old, new in replacements:
    assert old in text, old
    text = text.replace(old, new)
path.write_text(text)
