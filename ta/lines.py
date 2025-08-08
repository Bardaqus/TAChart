from __future__ import annotations
import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional

DEF_TOL = 0.01
DEF_ANCH = 3
DEF_SPAN = 20
DEF_ZZ = 0.012

@dataclass
class Line:
    kind: str
    slope: float
    intercept: float
    i0: int
    i1: int
    anchors: List[Tuple[int, float]]

    def score(self) -> float:
        length = float(max(1, int(self.i1) - int(self.i0)))
        return length * float(max(1, len(self.anchors)))

def _as_float(a) -> np.ndarray:
    return np.asarray(a, dtype=np.float64)

def _as_int(a) -> np.ndarray:
    return np.asarray(a, dtype=np.int64)

def zigzag(prices: np.ndarray, dev: float) -> List[int]:
    p = _as_float(prices)
    n = int(p.shape[0])
    if n == 0:
        return []
    piv = [0]
    last = float(p[0])
    direction = 0
    for i in range(1, n):
        val = float(p[i])
        denom = last if last != 0 else 1e-12
        ch = (val - last) / denom
        if direction >= 0 and ch >= dev:
            direction = 1
            piv.append(i)
            last = val
        elif direction <= 0 and ch <= -dev:
            direction = -1
            piv.append(i)
            last = val
        else:
            if direction >= 0:
                last = max(last, val)
            if direction <= 0:
                last = min(last, val)
    if piv[-1] != n - 1:
        piv.append(n - 1)
    return sorted(set(int(x) for x in piv))

def swing_extrema(highs: np.ndarray, lows: np.ndarray, w: int = 3):
    h = _as_float(highs); l = _as_float(lows)
    n = int(h.shape[0])
    hi_idx, lo_idx = [], []
    for i in range(w, n - w):
        if np.all(h[i] >= h[i-w:i]) and np.all(h[i] >= h[i+1:i+1+w]):
            hi_idx.append(i)
        if np.all(l[i] <= l[i-w:i]) and np.all(l[i] <= l[i+1:i+1+w]):
            lo_idx.append(i)
    return _as_int(hi_idx), _as_int(lo_idx)

def fit_line(i0: int, y0: float, i1: int, y1: float):
    i0 = int(i0); i1 = int(i1)
    y0 = float(y0); y1 = float(y1)
    dx = i1 - i0
    if dx == 0:
        return 0.0, y0
    m = (y1 - y0) / float(dx)
    b = y0 - m * float(i0)
    return float(m), float(b)

def anchors_for_line(m: float, b: float, xs: np.ndarray, prices_masked: np.ndarray, tol: float):
    m = float(m); b = float(b); tol = float(tol)
    xs = _as_float(xs)
    y_line = m * xs + b
    denom = np.maximum(np.abs(y_line), 1e-12)
    diff = np.abs(prices_masked - y_line)
    rel = diff / denom
    mask = np.isfinite(rel) & (rel <= tol)
    return _as_int(np.where(mask)[0])

def masked_series(n: int, idx: np.ndarray, vals: np.ndarray):
    n = int(n)
    out = np.full(n, np.nan, dtype=np.float64)
    idx = _as_int(idx); vals = _as_float(vals)
    out[idx] = vals
    return out

def trend_lines_from_extrema(idx: np.ndarray, vals: np.ndarray, kind: str,
                             n: int, tol: float, min_anchors: int, min_span: int) -> List[Line]:
    n = int(n); tol = float(tol); min_anchors = int(min_anchors); min_span = int(min_span)
    xs = _as_float(np.arange(n))
    masked = masked_series(n, idx, vals)
    idx = _as_int(idx); vals = _as_float(vals)

    results: List[Line] = []
    if idx.shape[0] < 3:
        return results
    for a in range(0, idx.shape[0] - 2):
        for bpos in range(a + 2, idx.shape[0]):
            i0 = int(idx[a]); i1 = int(idx[bpos])
            if i1 - i0 < min_span:
                continue
            y0 = float(vals[a]); y1 = float(vals[bpos])
            m, c = fit_line(i0, y0, i1, y1)
            touch_idx = anchors_for_line(m, c, xs, masked, tol)
            hits = [int(k) for k in idx if k in set(touch_idx.tolist())]
            if len(hits) < min_anchors:
                continue
            anchors = [(k, float(vals[np.where(idx == k)[0][0]])) for k in hits]
            results.append(Line(
                kind='resistance' if kind == 'high' else 'support',
                slope=float(m), intercept=float(c), i0=int(i0), i1=int(i1), anchors=anchors
            ))
    results.sort(key=lambda L: (L.score(), (int(L.i1) - int(L.i0))), reverse=True)
    return results

def best_parallel_for_opposite(idx: np.ndarray, vals: np.ndarray, slope: float,
                               n: int, tol: float) -> Optional[float]:
    idx = _as_int(idx); vals = _as_float(vals)
    n = int(n); tol = float(tol); slope = float(slope)
    if idx.shape[0] == 0:
        return None
    xs = _as_float(np.arange(n))
    masked = masked_series(n, idx, vals)
    best_b, best_hits = None, -1
    for i, xk in enumerate(idx):
        yk = float(vals[i])
        b = yk - slope * float(xk)
        touches = anchors_for_line(slope, b, xs, masked, tol)
        hits = int(np.isin(idx, touches).sum())
        if hits > best_hits:
            best_hits, best_b = hits, float(b)
    return best_b

def triangles(uppers: List[Line], lowers: List[Line]) -> List[Line]:
    out: List[Line] = []
    for U in uppers:
        for L in lowers:
            left = int(max(int(U.i0), int(L.i0)))
            right = int(min(int(U.i1), int(L.i1)))
            if right - left < 10:
                continue
            if (U.slope >= 0 and L.slope <= 0) or (U.slope <= 0 and L.slope >= 0) or (abs(float(U.slope) - float(L.slope)) > 1e-9):
                out.append(Line('triangle_upper', float(U.slope), float(U.intercept), left, right, U.anchors))
                out.append(Line('triangle_lower', float(L.slope), float(L.intercept), left, right, L.anchors))
    return out

def find_best_lines(
    highs: np.ndarray,
    lows: np.ndarray,
    max_lines: int = 5,
    tolerance: float = DEF_TOL,
    min_anchors: int = DEF_ANCH,
    min_span: int = DEF_SPAN,
    zz_dev: float = DEF_ZZ,
) -> List[Dict]:
    highs = _as_float(highs); lows = _as_float(lows)
    n = int(highs.shape[0])
    if n < 10:
        return []

    hi_idx_fr, lo_idx_fr = swing_extrema(highs, lows, w=3)
    piv_hi = np.intersect1d(hi_idx_fr, _as_int(zigzag(highs, zz_dev)))
    piv_lo = np.intersect1d(lo_idx_fr, _as_int(zigzag(lows, zz_dev)))

    hi_vals = highs[piv_hi]
    lo_vals = lows[piv_lo]

    uppers = trend_lines_from_extrema(piv_hi, hi_vals, 'high', n, tolerance, min_anchors, min_span)
    lowers = trend_lines_from_extrema(piv_lo, lo_vals, 'low',  n, tolerance, min_anchors, min_span)

    uppers = uppers[: max(0, (int(max_lines) + 1)//2)]
    lowers = lowers[: max(0, int(max_lines)//2)]

    channels: List[Line] = []
    if uppers and piv_lo.shape[0] > 0:
        b = best_parallel_for_opposite(piv_lo, lo_vals, uppers[0].slope, n, tolerance)
        if b is not None:
            channels.append(Line('channel_upper', uppers[0].slope, uppers[0].intercept, uppers[0].i0, uppers[0].i1, []))
            channels.append(Line('channel_lower', uppers[0].slope, b, uppers[0].i0, uppers[0].i1, []))
    if lowers and piv_hi.shape[0] > 0:
        b = best_parallel_for_opposite(piv_hi, hi_vals, lowers[0].slope, n, tolerance)
        if b is not None:
            channels.append(Line('channel_lower', lowers[0].slope, lowers[0].intercept, lowers[0].i0, lowers[0].i1, []))
            channels.append(Line('channel_upper', lowers[0].slope, b, lowers[0].i0, lowers[0].i1, []))

    tris = triangles(uppers, lowers)

    targets: List[Line] = []
    if uppers and piv_lo.shape[0] > 0:
        last_lo = int(piv_lo[-1]); y = float(lo_vals[-1])
        b = y - float(uppers[0].slope) * float(last_lo)
        targets.append(Line('target', float(uppers[0].slope), float(b), uppers[0].i0, uppers[0].i1, []))
    elif lowers and piv_hi.shape[0] > 0:
        last_hi = int(piv_hi[-1]); y = float(hi_vals[-1])
        b = y - float(lowers[0].slope) * float(last_hi)
        targets.append(Line('target', float(lowers[0].slope), float(b), lowers[0].i0, lowers[0].i1, []))

    all_lines: List[Line] = uppers + lowers + channels + tris + targets

    out: List[Dict] = []
    for L in all_lines:
        out.append({
            "type": L.kind,
            "slope": float(L.slope),
            "intercept": float(L.intercept),
            "i0": int(L.i0),
            "i1": int(L.i1),
            "anchors": [(int(k), float(v)) for k, v in (L.anchors or [])],
        })
    return out
