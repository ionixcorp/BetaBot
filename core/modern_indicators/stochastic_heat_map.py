import numpy as np
import pandas as pd


def stochastic_heat_map(close: np.ndarray, high: np.ndarray, low: np.ndarray, plot_number: int = 28, inc: int = 10, ma_type: str = 'EMA', smooth: int = 2, smooth_slow: int = 21) -> pd.DataFrame:
    """
    Calcula un heatmap de estocásticos suavizados para diferentes periodos.
    Devuelve un DataFrame con cada columna como un estocástico de diferente longitud.
    Aplica un suavizado adicional (smooth_slow) a cada columna del heatmap.
    """
    def stoch(src, high_prices, low_prices, length):
        lowest = pd.Series(low_prices).rolling(length).min()
        highest = pd.Series(high_prices).rolling(length).max()
        return 100 * (pd.Series(src) - lowest) / (highest - lowest)
    
    def ma(arr, n, typ):
        s = pd.Series(arr)
        if typ == 'SMA':
            return s.rolling(n).mean()
        elif typ == 'EMA':
            return s.ewm(span=n, adjust=False).mean()
        elif typ == 'WMA':
            weights = np.arange(1, n+1)
            return s.rolling(n).apply(lambda x: np.dot(x, weights)/weights.sum(), raw=True)
        else:
            return s
            
    result = {}
    for i in range(plot_number):
        period = (i+1) * inc
        stoch_values = stoch(close, high, low, period)
        stoch_smooth = ma(stoch_values, smooth, ma_type)
        stoch_slow = ma(stoch_smooth, smooth_slow, ma_type)
        result[f'stoch_{i+1}'] = stoch_slow
    return pd.DataFrame(result)