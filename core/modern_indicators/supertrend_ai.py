import numpy as np
import pandas as pd
from sklearn.cluster import KMeans


def supertrend_ai(close: np.ndarray, high: np.ndarray, low: np.ndarray, length: int = 10, min_mult: float = 1.0, max_mult: float = 5.0, step: float = 0.5, perf_alpha: float = 10.0) -> dict:
    """
    Calcula el SuperTrend AI (con clustering) y devuelve trailing stop, tendencia y factor óptimo.
    - close, high, low: arrays de precios
    - length: periodo ATR
    - min_mult, max_mult, step: rango de factores a probar
    - perf_alpha: memoria de performance
    Devuelve un dict con 'trailing_stop', 'trend', 'factor', 'perf_idx'.
    """
    def atr(high, low, close, period):
        tr = np.maximum(high[1:], close[:-1]) - np.minimum(low[1:], close[:-1])
        tr = np.insert(tr, 0, high[0] - low[0])
        return pd.Series(tr).rolling(period).mean().to_numpy()
    atr_arr = atr(high, low, close, length)
    factors = np.arange(min_mult, max_mult + step, step)
    trailing_stops = []
    trends = []
    perfs = []
    for factor in factors:
        up = (high + low) / 2 + atr_arr * factor
        dn = (high + low) / 2 - atr_arr * factor
        trend = np.zeros_like(close)
        upper = np.copy(up)
        lower = np.copy(dn)
        for i in range(1, len(close)):
            if close[i] > upper[i-1]:
                trend[i] = 1
            elif close[i] < lower[i-1]:
                trend[i] = 0
            else:
                trend[i] = trend[i-1]
            upper[i] = min(up[i], upper[i-1]) if close[i-1] < upper[i-1] else up[i]
            lower[i] = max(dn[i], lower[i-1]) if close[i-1] > lower[i-1] else dn[i]
        output = np.where(trend == 1, lower, upper)
        perf = np.zeros_like(close)
        for i in range(1, len(close)):
            diff = np.sign(close[i-1] - output[i-1])
            perf[i] = perf[i-1] + 2/(perf_alpha+1) * ((close[i] - close[i-1]) * diff - perf[i-1])
        trailing_stops.append(output)
        trends.append(trend)
        perfs.append(perf)
    # Clustering de performance
    last_perfs = np.array([perf[-1] for perf in perfs]).reshape(-1, 1)
    kmeans = KMeans(n_clusters=3, n_init=10, random_state=0).fit(last_perfs)
    labels = kmeans.labels_
    # Selección del mejor cluster (el de mayor media de performance)
    cluster_means = [last_perfs[labels == i].mean() for i in range(3)]
    best_cluster = np.argmax(cluster_means)
    idxs = np.where(labels == best_cluster)[0]
    # Factor óptimo: el de mayor performance dentro del mejor cluster
    best_idx = idxs[np.argmax([last_perfs[i][0] for i in idxs])]
    return {
        'trailing_stop': trailing_stops[best_idx],
        'trend': trends[best_idx],
        'factor': factors[best_idx],
        'perf_idx': perfs[best_idx]
    } 