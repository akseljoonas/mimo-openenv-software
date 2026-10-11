"""Reference repair for validation only; excluded from training images."""
from pathlib import Path

path = Path('src/mrinufft/density/geometry_based.py')
with path.open('a') as output:
    output.write('''

@register_density
@flat_traj
def cell_count(traj, shape, osf=1.0):
    if len(shape) != traj.shape[-1]:
        raise ValueError("Shape and trajectory dimensions must agree")
    bins = np.asarray([int(size * osf) for size in shape])
    if np.any(bins <= 0):
        raise ValueError("Grid dimensions must be positive")
    cells = np.floor((traj + 0.5) * bins).astype(int)
    cells = np.clip(cells, 0, bins - 1)
    _, inverse, counts = np.unique(cells, axis=0, return_inverse=True, return_counts=True)
    return _normalize_weights(counts[inverse])
''')
path = Path('src/mrinufft/density/__init__.py')
text = path.read_text().replace('from .geometry_based import voronoi', 'from .geometry_based import voronoi, cell_count')
text = text.replace('__all__ = [', '__all__ = [\n    "cell_count",')
path.write_text(text)
