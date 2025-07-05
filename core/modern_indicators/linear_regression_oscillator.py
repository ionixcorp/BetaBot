import numpy as np
import pandas as pd


def linear_regression_oscillator(close: np.ndarray, length: int = 20, upper: float = 1.5, lower: float = -1.5) -> dict:
    """
    Calcula el Linear Regression Oscillator y devuelve el oscilador normalizado y señales de cruce de umbrales.
    - close: array de precios de cierre
    - length: periodo de regresión
    - upper, lower: umbrales
    Devuelve un dict con 'osc', 'cross_up', 'cross_down', 'mean_reversion_up', 'mean_reversion_down'.
    """
    n = length
    lr = np.zeros_like(close)
    for i in range(n-1, len(close)):
        x = np.arange(n)
        y = close[i-n+1:i+1]
        A = np.vstack([x, np.ones(n)]).T
        m, c = np.linalg.lstsq(A, y, rcond=None)[0]
        lr[i] = (m * (i) + c) * -1
    # Normalización
    lr_norm = (lr - pd.Series(lr).rolling(100).mean()) / pd.Series(lr).rolling(100).std()
    # Señales
    cross_up = (np.diff(lr_norm) > 0) & (lr_norm[1:] > 0) & (lr_norm[:-1] <= 0)
    cross_down = (np.diff(lr_norm) < 0) & (lr_norm[1:] < 0) & (lr_norm[:-1] >= 0)
    mean_reversion_up = (lr_norm[2:] < lower) & (lr_norm[1:-1] > lr_norm[2:])
    mean_reversion_down = (lr_norm[2:] > upper) & (lr_norm[1:-1] < lr_norm[2:])
    return {
        'osc': lr_norm,
        'cross_up': np.concatenate([[False], cross_up]),
        'cross_down': np.concatenate([[False], cross_down]),
        'mean_reversion_up': np.concatenate([[False, False], mean_reversion_up]),
        'mean_reversion_down': np.concatenate([[False, False], mean_reversion_down]),
    } 