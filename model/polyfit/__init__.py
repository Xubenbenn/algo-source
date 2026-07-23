"""多项式拟合模块 — 拟合、插值与求根"""

from .fitting import (
    polyfit_ls,
    polyval,
    poly_residual,
    r2_score,
    weighted_polyfit,
)
from .interpolation import (
    lagrange_interp,
    newton_interp,
    cubic_spline,
    linear_interp_grid,
)
from .roots import (
    poly_roots,
    poly_derivative,
    poly_integral,
    find_extrema,
)
