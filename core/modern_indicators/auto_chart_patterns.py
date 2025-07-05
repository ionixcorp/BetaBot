def find_pivots(high, low, depth=8):
    """
    Encuentra pivotes zigzag en los datos de precios.
    Un pivote es un máximo o mínimo local dentro de una ventana de tamaño 'depth'.
    Args:
        high: array-like de precios altos
        low: array-like de precios bajos
        depth: tamaño de la ventana para buscar el pivote (entero positivo)
    Devuelve:
        Lista de índices de pivotes.
    """
    pivots = []
    for i in range(depth, len(high)-depth):
        if high[i] == max(high[i-depth:i+depth+1]):
            pivots.append(i)
        elif low[i] == min(low[i-depth:i+depth+1]):
            pivots.append(i)
    return sorted(set(pivots))

def detect_channels(pivots, high, low):
    """
    Detecta canales ascendentes, descendentes y laterales a partir de pivotes.
    Devuelve lista de canales como tuplas (start_idx, end_idx, tipo).
    """
    channels = []
    for i in range(len(pivots)-2):
        x1, x2, x3 = pivots[i], pivots[i+1], pivots[i+2]
        if high[x1] < high[x2] < high[x3] and low[x1] < low[x2] < low[x3]:
            channels.append((x1, x3, 'up'))
        elif high[x1] > high[x2] > high[x3] and low[x1] > low[x2] > low[x3]:
            channels.append((x1, x3, 'down'))
        elif abs(high[x1]-high[x3]) < 0.01 and abs(low[x1]-low[x3]) < 0.01:
            channels.append((x1, x3, 'side'))
    return channels 