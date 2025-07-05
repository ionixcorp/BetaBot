from datetime import time

import pandas as pd


def get_killzone_ranges(df, tz='America/New_York'):
    """
    Devuelve un DataFrame con las zonas horarias de killzones (Asia, London, NY AM, NY Lunch, NY PM).
    df: DataFrame con columna 'datetime' en UTC.
    tz: zona horaria para convertir.
    """
    df = df.copy()
    df['datetime'] = pd.to_datetime(df['datetime']).dt.tz_localize('UTC').dt.tz_convert(tz)
    df['time'] = df['datetime'].dt.time
    killzones = {
        'Asia':   (time(20,0), time(0,0)),
        'London': (time(2,0), time(5,0)),
        'NY AM':  (time(9,30), time(11,0)),
        'NY Lunch': (time(12,0), time(13,0)),
        'NY PM':  (time(13,30), time(16,0)),
    }
    result = {}
    for name, (start, end) in killzones.items():
        if start < end:
            mask = (df['time'] >= start) & (df['time'] < end)
        else:
            mask = (df['time'] >= start) | (df['time'] < end)
        result[name] = df[mask]
    return result

def get_daily_pivots(df):
    """
    Calcula los pivotes diarios (high, low, open) por día.
    """
    df = df.copy()
    df['date'] = pd.to_datetime(df['datetime']).dt.date
    pivots = df.groupby('date').agg({'high':'max','low':'min','open':'first'})
    return pivots 