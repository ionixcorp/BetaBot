"""
Sistema de Excepciones para Métricas de Velas
=============================================

Este módulo define todas las excepciones específicas del sistema de métricas,
proporcionando manejo granular de errores y debugging mejorado.

Autor: Sistema Bet-AG
Fecha: 2025
"""

from typing import Any, Dict, Optional


class BaseMetricException(Exception):
    """
    Excepción base para todas las excepciones del sistema de métricas.
    
    Proporciona funcionalidad común como contexto de error y metadata.
    """
    
    def __init__(
        self,
        message: str,
        metric_name: Optional[str] = None,
        symbol: Optional[str] = None,
        broker: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.metric_name = metric_name
        self.symbol = symbol
        self.broker = broker
        self.context = context or {}
        
        # Construir mensaje completo
        full_message = self._build_full_message()
        super().__init__(full_message)
    
    def _build_full_message(self) -> str:
        """Construye el mensaje completo de error con contexto."""
        parts = [self.message]
        
        if self.metric_name:
            parts.append(f"Métrica: {self.metric_name}")
        
        if self.symbol:
            parts.append(f"Símbolo: {self.symbol}")
        
        if self.broker:
            parts.append(f"Broker: {self.broker}")
        
        if self.context:
            context_str = ", ".join([f"{k}={v}" for k, v in self.context.items()])
            parts.append(f"Contexto: {context_str}")
        
        return " | ".join(parts)


class MetricConfigurationError(BaseMetricException):
    """
    Excepción lanzada cuando hay problemas con la configuración de una métrica.
    
    Ejemplos:
    - Parámetros faltantes o inválidos
    - Configuración malformada
    - Valores fuera de rango
    """
    pass


class MetricInitializationError(BaseMetricException):
    """
    Excepción lanzada durante la inicialización de una métrica.
    
    Ejemplos:
    - Error al cargar configuración
    - Fallo en la inicialización de buffers
    - Recursos no disponibles
    """
    pass


class MetricCalculationError(BaseMetricException):
    """
    Excepción lanzada durante el cálculo de una métrica.
    
    Ejemplos:
    - División por cero
    - Datos insuficientes
    - Operaciones matemáticas inválidas
    """
    pass


class InsufficientDataError(MetricCalculationError):
    """
    Excepción específica para cuando no hay suficientes datos para calcular una métrica.
    
    Esta excepción incluye información sobre cuántos datos se necesitan
    vs cuántos están disponibles.
    """
    
    def __init__(
        self,
        message: str,
        required_ticks: int,
        available_ticks: int,
        metric_name: Optional[str] = None,
        symbol: Optional[str] = None,
        broker: Optional[str] = None
    ):
        self.required_ticks = required_ticks
        self.available_ticks = available_ticks
        
        context = {
            "required_ticks": required_ticks,
            "available_ticks": available_ticks,
            "deficit": required_ticks - available_ticks
        }
        
        super().__init__(
            message=message,
            metric_name=metric_name,
            symbol=symbol,
            broker=broker,
            context=context
        )


class TickValidationError(BaseMetricException):
    """
    Excepción lanzada cuando un tick no pasa las validaciones requeridas.
    
    Ejemplos:
    - Tick con datos corruptos
    - Timestamp inválido
    - Precios negativos o cero
    """
    pass


class MetricStateError(BaseMetricException):
    """
    Excepción lanzada cuando el estado interno de una métrica es inconsistente.
    
    Ejemplos:
    - Buffer corrupto
    - Estado no inicializado
    - Concurrencia no controlada
    """
    pass


class VolumeNotSupportedError(BaseMetricException):
    """
    Excepción lanzada cuando se intenta usar métricas de volumen
    pero el broker no soporta datos de volumen.
    """
    pass


class TimeframeError(BaseMetricException):
    """
    Excepción lanzada cuando hay problemas con el manejo de timeframes.
    
    Ejemplos:
    - Timeframe no soportado
    - Conversión de timeframe inválida
    - Configuración de timeframe conflictiva
    """
    pass


class MetricTimeoutError(BaseMetricException):
    """
    Excepción lanzada cuando una operación de métrica excede el tiempo límite.
    
    Útil para operaciones asíncronas que pueden colgarse.
    """
    
    def __init__(
        self,
        message: str,
        timeout_seconds: float,
        metric_name: Optional[str] = None,
        symbol: Optional[str] = None,
        broker: Optional[str] = None
    ):
        self.timeout_seconds = timeout_seconds
        
        context = {"timeout_seconds": timeout_seconds}
        
        super().__init__(
            message=message,
            metric_name=metric_name,
            symbol=symbol,
            broker=broker,
            context=context
        )


class ConcurrencyError(BaseMetricException):
    """
    Excepción lanzada cuando hay problemas de concurrencia en el procesamiento.
    
    Ejemplos:
    - Race conditions
    - Deadlocks
    - Acceso simultáneo a recursos compartidos
    """
    pass


class MetricMemoryError(BaseMetricException):
    """
    Excepción lanzada cuando hay problemas de memoria en las métricas.
    
    Ejemplos:
    - Buffer demasiado grande
    - Leak de memoria
    - Límites de memoria excedidos
    """
    
    def __init__(
        self,
        message: str,
        memory_usage_mb: Optional[float] = None,
        memory_limit_mb: Optional[float] = None,
        metric_name: Optional[str] = None,
        symbol: Optional[str] = None,
        broker: Optional[str] = None
    ):
        self.memory_usage_mb = memory_usage_mb
        self.memory_limit_mb = memory_limit_mb
        
        context = {}
        if memory_usage_mb is not None:
            context["memory_usage_mb"] = memory_usage_mb
        if memory_limit_mb is not None:
            context["memory_limit_mb"] = memory_limit_mb
        
        super().__init__(
            message=message,
            metric_name=metric_name,
            symbol=symbol,
            broker=broker,
            context=context
        )


class MetricDeprecationWarning(UserWarning):
    """
    Warning lanzado cuando se usa una funcionalidad obsoleta de métricas.
    """
    pass


# Funciones de utilidad para manejo de excepciones

def handle_metric_exception(
    exception: Exception,
    metric_name: str,
    symbol: str,
    broker: str,
    logger = None
) -> None:
    """
    Función utilitaria para manejar excepciones de métricas de forma consistente.
    
    Args:
        exception: La excepción capturada
        metric_name: Nombre de la métrica donde ocurrió el error
        symbol: Símbolo siendo procesado
        broker: Broker del que provienen los datos
        logger: Logger opcional para registrar el error
    """
    if isinstance(exception, BaseMetricException):
        # Ya es una excepción de métricas, solo loguear
        error_msg = str(exception)
    else:
        # Convertir a excepción de métricas
        error_msg = f"Error no manejado en métrica: {exception!s}"
        exception = MetricCalculationError(
            message=error_msg,
            metric_name=metric_name,
            symbol=symbol,
            broker=broker
        )
    
    if logger:
        logger.error(error_msg, exc_info=True)
    
    # Re-lanzar la excepción para que el llamador pueda manejarla
    raise exception


def validate_tick_data(tick, required_fields: list | None = None) -> None:
    """
    Valida que un tick tenga los campos requeridos y datos válidos.
    
    Args:
        tick: El tick a validar
        required_fields: Lista de campos requeridos
        
    Raises:
        TickValidationError: Si el tick no es válido
    """
    if tick is None:
        raise TickValidationError("Tick es None")
    
    # Validaciones básicas
    required_fields = required_fields or ['timestamp', 'symbol', 'broker', 'price']
    
    for field in required_fields:
        if not hasattr(tick, field) or getattr(tick, field) is None:
            raise TickValidationError(
                f"Campo requerido '{field}' faltante o None",
                symbol=getattr(tick, 'symbol', None),
                broker=getattr(tick, 'broker', None)
            )
    
    # Validar precio positivo
    if hasattr(tick, 'price') and tick.price <= 0:
        raise TickValidationError(
            f"Precio inválido: {tick.price}",
            symbol=tick.symbol,
            broker=tick.broker
        )
    
    # Validar quality_score en rango válido
    if hasattr(tick, 'quality_score') and not (0.0 <= tick.quality_score <= 1.0):
        raise TickValidationError(
            f"Quality score fuera de rango [0,1]: {tick.quality_score}",
            symbol=tick.symbol,
            broker=tick.broker
        )


def require_minimum_ticks(
    current_count: int,
    required_count: int,
    metric_name: str,
    symbol: str,
    broker: str
) -> None:
    """
    Valida que haya suficientes ticks para realizar un cálculo.
    
    Args:
        current_count: Cantidad actual de ticks
        required_count: Cantidad mínima requerida
        metric_name: Nombre de la métrica
        symbol: Símbolo
        broker: Broker
        
    Raises:
        InsufficientDataError: Si no hay suficientes ticks
    """
    if current_count < required_count:
        raise InsufficientDataError(
            f"Insuficientes ticks para calcular {metric_name}",
            required_ticks=required_count,
            available_ticks=current_count,
            metric_name=metric_name,
            symbol=symbol,
            broker=broker
        )


def validate_volume_support(
    tick,
    metric_name: str,
    operation: str = "cálculo"
) -> None:
    """
    Valida que el tick tenga soporte de volumen cuando es requerido.
    
    Args:
        tick: El tick a validar
        metric_name: Nombre de la métrica
        operation: Tipo de operación que requiere volumen
        
    Raises:
        VolumeNotSupportedError: Si no hay datos de volumen
    """
    if not hasattr(tick, 'volume') or tick.volume is None:
        raise VolumeNotSupportedError(
            f"Métrica {metric_name} requiere datos de volumen para {operation}",
            metric_name=metric_name,
            symbol=getattr(tick, 'symbol', None),
            broker=getattr(tick, 'broker', None)
        )