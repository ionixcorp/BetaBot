import numpy as np


class VolumeRequiredForOBVError(Exception):
    MESSAGE = "Se requiere el volumen para calcular OBV."
    def __init__(self):
        super().__init__(self.MESSAGE)


def momentum_acceleration(source: np.ndarray, length: int = 13, use_obv: bool = False, volume: np.ndarray = None) -> np.ndarray:
    """
    Calcula el oscilador Momentum Acceleration (SpeedyGonzales) para un array de precios o para OBV.
    - source: array de precios (close) o de OBV
    - length: periodo de cálculo
    - use_obv: si True, calcula OBV internamente
    - volume: array de volúmenes (requerido si use_obv=True)
    Devuelve un array con el valor del oscilador para cada punto.
    """
    if use_obv:
        if volume is None:
            raise VolumeRequiredForOBVError()
        # Cálculo de OBV
        obv = np.zeros_like(source)
        obv[0] = 0
        for i in range(1, len(source)):
            if source[i] > source[i-1]:
                obv[i] = obv[i-1] + volume[i]
            elif source[i] < source[i-1]:
                obv[i] = obv[i-1] - volume[i]
            else:
                obv[i] = obv[i-1]
        data = obv
    else:
        data = source
    # f_speedy: velocidad y aceleración
    v = np.convolve(np.diff(data, n=length) / length, np.ones(3)/3, mode='same')
    a = np.diff(v, n=length) / length
    # Ajustar tamaño de a para restar
    a_full = np.concatenate([np.zeros(length), a])
    psgval = v - a_full[:len(v)]
    # Rellenar NaN iniciales
    psgval[:length*2] = np.nan
    return psgval 