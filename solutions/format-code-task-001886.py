"""Reference repair for validation only; excluded from training images."""
from pathlib import Path

Path('libfmp/c3/c3s2_dtw.py').write_text('''import numpy as np
from scipy.spatial.distance import cdist


def compute_cost_matrix(X, Y, metric="euclidean"):
    return cdist(X.T, Y.T, metric=metric)


def _accumulate(C, steps):
    D = np.full(C.shape, np.inf)
    D[0, 0] = C[0, 0]
    for i in range(C.shape[0]):
        for j in range(C.shape[1]):
            if i == j == 0:
                continue
            previous = [D[i-di, j-dj] for di, dj in steps if i >= di and j >= dj]
            if previous:
                D[i, j] = C[i, j] + min(previous)
    return D


def _path(D, steps):
    i, j = D.shape[0]-1, D.shape[1]-1
    points = [(i, j)]
    while i or j:
        candidates = [(i-di, j-dj) for di, dj in steps if i >= di and j >= dj]
        if not candidates:
            raise ValueError("No feasible warping path")
        i, j = min(candidates, key=lambda p: D[p])
        points.append((i, j))
    return np.array(points[::-1])


def compute_accumulated_cost_matrix(C):
    return _accumulate(C, [(1, 1), (1, 0), (0, 1)])


def compute_optimal_warping_path(D):
    return _path(D, [(1, 1), (1, 0), (0, 1)])


def compute_accumulated_cost_matrix_21(C):
    return _accumulate(C, [(1, 1), (2, 1), (1, 2)])


def compute_optimal_warping_path_21(D):
    return _path(D, [(1, 1), (2, 1), (1, 2)])
''')
with Path('libfmp/c3/__init__.py').open('a') as output:
    output.write('\nfrom .c3s2_dtw import compute_cost_matrix, compute_accumulated_cost_matrix, compute_optimal_warping_path, compute_accumulated_cost_matrix_21, compute_optimal_warping_path_21\n')
