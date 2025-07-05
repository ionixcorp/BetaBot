import pandas as pd
import talib


def detect_candlestick_patterns(df):
    """
    Detecta patrones de velas japonesas usando TA-Lib.
    Devuelve un DataFrame con columnas para cada patrón (True/False).
    """
    patterns = {
        'hammer': talib.CDLHAMMER,
        'engulfing': talib.CDLENGULFING,
        'doji': talib.CDLDOJI,
        'shooting_star': talib.CDLSHOOTINGSTAR,
        'morning_star': talib.CDLMORNINGSTAR,
        'evening_star': talib.CDLEVENINGSTAR,
        'hanging_man': talib.CDLHANGINGMAN,
        'harami': talib.CDLHARAMI,
        'dark_cloud_cover': talib.CDLDARKCLOUDCOVER,
        'piercing': talib.CDLPIERCING,
        'three_white_soldiers': talib.CDL3WHITESOLDIERS,
        'three_black_crows': talib.CDL3BLACKCROWS,
        # Agrega más patrones según sea necesario
    }
    out = {}
    for name, func in patterns.items():
        out[name] = func(df['open'], df['high'], df['low'], df['close']) != 0
    return pd.DataFrame(out) 