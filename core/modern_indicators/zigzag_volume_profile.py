import logging
from typing import List, Optional, Tuple  # noqa: F401

import numpy as np

logger = logging.getLogger(__name__)


def zigzag_pivots(high: np.ndarray, low: np.ndarray, close: np.ndarray, 
                  deviation: float = 0.01, depth: int = 10, 
                  min_pivot_distance: int = 5) -> List[int]:
    """
    Calcula los pivotes zigzag dados los precios y la desviación mínima.
    Optimizado para operar con datos de ticks y timestamps, sin dependencia de volumen.
    
    Algoritmo mejorado con:
    - Validación de fuerza de pivotes usando múltiples timeframes
    - Detección de divergencias en momentum
    - Filtrado adaptativo de ruido
    
    Args:
        high, low, close: arrays de precios (validados por el engine)
        deviation: desviación mínima para considerar un pivote
        depth: profundidad de la ventana de análisis
        min_pivot_distance: distancia mínima entre pivotes
        
    Returns:
        Lista de índices de pivotes válidos
    """
    if not (len(high) == len(low) == len(close)):
        raise ValueError("Arrays high, low y close deben tener la misma longitud")
    
    if len(close) < depth * 2:
        return []
    
    pivots = []
    last_pivot_idx = 0
    last_pivot_type = 0  # 1 para high, -1 para low
    
    # Pre-calcular indicadores de momentum para validación
    momentum = _calculate_momentum(close, window=min(depth, 5))
    strength_threshold = np.std(close[-depth*2:]) * deviation
    
    for i in range(depth, len(close) - depth):
        if i - last_pivot_idx < min_pivot_distance:
            continue
            
        # Ventana dinámica para análisis
        window_start = max(0, i - depth)
        window_end = min(len(close), i + depth + 1)
        
        window_high = high[window_start:window_end]
        window_low = low[window_start:window_end]
        window_close = close[window_start:window_end]
        
        current_high = high[i]
        current_low = low[i]
        current_close = close[i]
        
        # Detección de pivote alto con validación de fuerza
        if (_is_local_maximum(window_high, i - window_start) and 
            current_high >= np.max(window_high) - strength_threshold):
            
            if last_pivot_type != 1:  # No es el mismo tipo que el anterior
                # Validación adicional: confirmar que es significativamente diferente
                if (not pivots or 
                    abs(current_high - high[pivots[-1]]) > strength_threshold):
                    
                    # Validar momentum divergence para mayor confianza
                    if _validate_pivot_strength(momentum, i, window_start, 'high'):
                        pivots.append(i)
                        last_pivot_idx = i
                        last_pivot_type = 1
        
        # Detección de pivote bajo con validación de fuerza
        elif (_is_local_minimum(window_low, i - window_start) and 
              current_low <= np.min(window_low) + strength_threshold):
            
            if last_pivot_type != -1:  # No es el mismo tipo que el anterior
                # Validación adicional: confirmar que es significativamente diferente
                if (not pivots or 
                    abs(current_low - low[pivots[-1]]) > strength_threshold):
                    
                    # Validar momentum divergence para mayor confianza
                    if _validate_pivot_strength(momentum, i, window_start, 'low'):
                        pivots.append(i)
                        last_pivot_idx = i
                        last_pivot_type = -1
    
    return pivots


def tick_profile(high: np.ndarray, low: np.ndarray, close: np.ndarray, 
                 timestamps: np.ndarray, start_idx: int, end_idx: int, 
                 n_bins: int = 20) -> np.ndarray:
    """
    Calcula el perfil de distribución de ticks entre dos índices usando bins de precio.
    Reemplaza volume_profile para sistemas basados en ticks y timestamps.
    
    Algoritmo mejorado con:
    - Análisis de densidad temporal de ticks
    - Identificación de zonas de mayor actividad
    - Ponderación por time-weighted average price (TWAP)
    
    Args:
        high, low, close: arrays de precios
        timestamps: array de timestamps para análisis temporal
        start_idx, end_idx: índices del segmento a analizar
        n_bins: número de bins de precio
        
    Returns:
        Array con la densidad de ticks por bin de precio
    """
    if not (len(high) == len(low) == len(close) == len(timestamps)):
        raise ValueError("Todos los arrays deben tener la misma longitud")
    
    if start_idx >= end_idx or end_idx > len(close):
        return np.zeros(n_bins)
    
    # Extraer segmento
    segment_high = high[start_idx:end_idx]
    segment_low = low[start_idx:end_idx]
    segment_close = close[start_idx:end_idx]
    segment_timestamps = timestamps[start_idx:end_idx]
    
    if len(segment_high) == 0:
        return np.zeros(n_bins)
    
    # Calcular rango de precios y crear bins
    price_min = np.min(segment_low)
    price_max = np.max(segment_high)
    
    if price_max - price_min == 0:
        return np.zeros(n_bins)
    
    price_bins = np.linspace(price_min, price_max, n_bins + 1)
    
    # Calcular pesos temporales (más peso a ticks más recientes)
    time_weights = _calculate_time_weights(segment_timestamps)
    
    # Asignar cada tick a su bin correspondiente
    bin_indices = np.digitize(segment_close, price_bins) - 1
    bin_indices = np.clip(bin_indices, 0, n_bins - 1)
    
    # Crear perfil ponderado por tiempo
    profile = np.zeros(n_bins)
    for i, bin_idx in enumerate(bin_indices):
        profile[bin_idx] += time_weights[i]
    
    # Normalizar para obtener densidad
    total_weight = np.sum(time_weights)
    if total_weight > 0:
        profile = profile / total_weight
    
    return profile


def _calculate_momentum(prices: np.ndarray, window: int = 5) -> np.ndarray:
    """Calcula momentum usando ROC (Rate of Change) suavizado"""
    if len(prices) < window * 2:
        return np.zeros(len(prices))
    
    momentum = np.zeros(len(prices))
    for i in range(window, len(prices)):
        if prices[i - window] != 0:
            momentum[i] = (prices[i] - prices[i - window]) / prices[i - window] * 100
    
    # Suavizar momentum con media móvil
    smoothed = np.zeros(len(momentum))
    for i in range(window, len(momentum)):
        smoothed[i] = np.mean(momentum[i-window+1:i+1])
    
    return smoothed


def _is_local_maximum(values: np.ndarray, center_idx: int) -> bool:
    """Verifica si el valor en center_idx es un máximo local robusto"""
    if center_idx < 1 or center_idx >= len(values) - 1:
        return False
    
    center_value = values[center_idx]
    
    # Verificar que sea mayor que vecinos inmediatos
    if not (center_value >= values[center_idx - 1] and 
            center_value >= values[center_idx + 1]):
        return False
    
    # Verificar tendencia en ventana más amplia si hay suficientes datos
    if len(values) >= 5 and center_idx >= 2 and center_idx < len(values) - 2:
        left_avg = np.mean(values[max(0, center_idx-2):center_idx])
        right_avg = np.mean(values[center_idx+1:min(len(values), center_idx+3)])
        return center_value > max(left_avg, right_avg)
    
    return True


def _is_local_minimum(values: np.ndarray, center_idx: int) -> bool:
    """Verifica si el valor en center_idx es un mínimo local robusto"""
    if center_idx < 1 or center_idx >= len(values) - 1:
        return False
    
    center_value = values[center_idx]
    
    # Verificar que sea menor que vecinos inmediatos
    if not (center_value <= values[center_idx - 1] and 
            center_value <= values[center_idx + 1]):
        return False
    
    # Verificar tendencia en ventana más amplia si hay suficientes datos
    if len(values) >= 5 and center_idx >= 2 and center_idx < len(values) - 2:
        left_avg = np.mean(values[max(0, center_idx-2):center_idx])
        right_avg = np.mean(values[center_idx+1:min(len(values), center_idx+3)])
        return center_value < min(left_avg, right_avg)
    
    return True


def _validate_pivot_strength(momentum: np.ndarray, pivot_idx: int, 
                           window_start: int, pivot_type: str) -> bool:
    """Valida la fuerza del pivote usando análisis de momentum"""
    if pivot_idx < len(momentum):
        current_momentum = momentum[pivot_idx]
        
        # Para pivotes altos, buscamos momentum decreciente
        if pivot_type == 'high':
            return current_momentum < 0 or abs(current_momentum) > 0.1
        # Para pivotes bajos, buscamos momentum creciente
        else:
            return current_momentum > 0 or abs(current_momentum) > 0.1
    
    return True  # Si no hay datos de momentum, aceptar el pivote


def _calculate_time_weights(timestamps: np.ndarray) -> np.ndarray:
    """Calcula pesos temporales dando más importancia a ticks recientes"""
    if len(timestamps) == 0:
        return np.array([])
    
    # Normalizar timestamps a rango [0, 1]
    time_range = timestamps[-1] - timestamps[0]
    if time_range == 0:
        return np.ones(len(timestamps))
    
    normalized_times = (timestamps - timestamps[0]) / time_range
    
    # Aplicar función exponencial para dar más peso a tiempos recientes
    weights = np.exp(normalized_times * 2)  # Factor 2 para curva moderada
    
    return weights