"""SVD 模块 — 奇异值分解及其应用"""

from .decompose import (
    svd_full,
    svd_economy,
    singular_values,
    svd_rank,
    svd_reconstruct,
)
from .pseudo_inverse import (
    pseudo_inverse,
    solve_via_svd,
    tikhonov_regularized,
)
from .approximation import (
    low_rank_approx,
    reconstruction_error,
    condition_number,
    effective_rank,
)
