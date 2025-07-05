import numpy as np
import talib


def ma_sabres(close, high, low, ma_type='TEMA', length=50, count=20, price_mode='close'):
    """
    Calcula la media móvil seleccionada y detecta cambios de tendencia según la lógica de MA Sabres.
    Permite elegir el precio base: 'close', 'high', 'low', 'hl2' (promedio high/low), 'hlc3' (promedio high/low/close).
    Devuelve un dict con 'ma', 'trend_up', 'trend_down', cada uno limitado a los últimos 'count' valores.

    Args:
        close: array de precios de cierre
        high: array de precios máximos
        low: array de precios mínimos
        ma_type: tipo de media móvil ('SMA', 'EMA', 'SMMA (RMA)', 'HullMA', 'TEMA')
        length: periodo de la media móvil
        count: cantidad de valores recientes a devolver
        price_mode: base para el cálculo ('close', 'high', 'low', 'hl2', 'hlc3')
    """
    if price_mode == 'close':
        price = close
    elif price_mode == 'high':
        price = high
    elif price_mode == 'low':
        price = low
    elif price_mode == 'hl2':
        price = (high + low) / 2
    elif price_mode == 'hlc3':
        price = (high + low + close) / 3
    else:
        price = close

    if ma_type == 'SMA':
        ma = talib.SMA(price, timeperiod=length)
    elif ma_type == 'EMA':
        ma = talib.EMA(price, timeperiod=length)
    elif ma_type == 'SMMA (RMA)':
        ma = talib.RMA(price, timeperiod=length)
    elif ma_type == 'HullMA':
        # Hull MA aproximado
        wma1 = talib.WMA(price, timeperiod=int(length/2))
        wma2 = talib.WMA(price, timeperiod=length)
        ma = talib.WMA(2*wma1 - wma2, timeperiod=int(np.sqrt(length)))
    elif ma_type == 'WMA':
        ma = talib.WMA(price, timeperiod=length)
    elif ma_type == 'VWMA':
        ma = np.convolve(price, np.ones(length)/length, mode='valid')
    elif ma_type == 'DEMA':
        ema1 = talib.EMA(price, timeperiod=length)
        ema1 = talib.EMA(close, timeperiod=length)
        ema2 = talib.EMA(ema1, timeperiod=length)
        ma = 2*ema1 - ema2
    elif ma_type == 'TEMA':
        ema1 = talib.EMA(close, timeperiod=length)
        ema2 = talib.EMA(ema1, timeperiod=length)
        ema3 = talib.EMA(ema2, timeperiod=length)
        ma = 3*ema1 - 3*ema2 + ema3
    else:
        ma = close
    # Detección de tendencia
    falling = np.array([ma[i] < ma[i-1] for i in range(1, len(ma))] + [False])
    rising = np.array([ma[i] > ma[i-1] for i in range(1, len(ma))] + [False])
    trend_up = np.roll(falling, 1) & (ma > np.roll(ma, 1))
    trend_down = np.roll(rising, 1) & (ma < np.roll(ma, 1))

    # Limitar la longitud de los resultados a los últimos 'count' valores
    if count is not None and count > 0:
        ma = ma[-count:]
        trend_up = trend_up[-count:]
        trend_down = trend_down[-count:]

    return {'ma': ma, 'trend_up': trend_up, 'trend_down': trend_down}