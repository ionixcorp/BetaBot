"""
Tick Normalizer Exception System
Bet-AG Trading System - Módulo de excepciones para normalización de ticks
"""

from typing import Any, Dict, Optional


class TickNormalizationError(Exception):
    """
    Excepción base para todos los errores del sistema de normalización de ticks.
    
    Attributes:
        message: Mensaje descriptivo del error
        error_code: Código único del error para logging/debugging
        context: Información adicional del contexto donde ocurrió el error
    """
    
    def __init__(
        self, 
        message: str, 
        error_code: str = "TN_GENERIC", 
        context: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.context = context or {}
        super().__init__(self.message)
    
    def __str__(self) -> str:
        context_str = f" | Context: {self.context}" if self.context else ""
        return f"[{self.error_code}] {self.message}{context_str}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte la excepción a diccionario para logging estructurado."""
        return {
            "error_type": self.__class__.__name__,
            "error_code": self.error_code,
            "message": self.message,
            "context": self.context
        }


class InvalidTickDataError(TickNormalizationError):
    """
    Excepción para datos de tick inválidos o corruptos.
    
    Se lanza cuando:
    - Precio fuera de rango realista
    - Timestamp inválido o corrupto
    - Campos requeridos faltantes
    - Formato de datos incorrecto
    """
    
    def __init__(
        self, 
        message: str, 
        field: Optional[str] = None,
        value: Optional[Any] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        error_code = "TN_INVALID_DATA"
        ctx = context or {}
        
        if field:
            ctx["invalid_field"] = field
        if value is not None:
            ctx["invalid_value"] = str(value)
            
        super().__init__(message, error_code, ctx)


class BrokerConnectionError(TickNormalizationError):
    """
    Excepción para errores de conexión con brokers.
    
    Se lanza cuando:
    - Pérdida de conexión con broker
    - Timeout en respuesta del broker
    - Error de autenticación
    - Rate limit excedido
    """
    
    def __init__(
        self, 
        message: str, 
        broker: str,
        connection_type: Optional[str] = None,
        retry_count: int = 0,
        context: Optional[Dict[str, Any]] = None
    ):
        error_code = "TN_BROKER_CONNECTION"
        ctx = context or {}
        ctx.update({
            "broker": broker,
            "retry_count": retry_count
        })
        
        if connection_type:
            ctx["connection_type"] = connection_type
            
        super().__init__(message, error_code, ctx)


class DataQualityError(TickNormalizationError):
    """
    Excepción para problemas de calidad de datos.
    
    Se lanza cuando:
    - Spread bid/ask anormal
    - Gap temporal excesivo
    - Datos duplicados detectados
    - Secuencia temporal incorrecta
    - Quality score por debajo del umbral
    """
    
    def __init__(
        self, 
        message: str, 
        quality_issue: str,
        quality_score: Optional[float] = None,
        threshold: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        error_code = "TN_DATA_QUALITY"
        ctx = context or {}
        ctx.update({
            "quality_issue": quality_issue
        })
        
        if quality_score is not None:
            ctx["quality_score"] = quality_score
        if threshold is not None:
            ctx["quality_threshold"] = threshold
            
        super().__init__(message, error_code, ctx)


class LatencyCompensationError(TickNormalizationError):
    """
    Excepción para errores en compensación de latencia.
    
    Se lanza cuando:
    - No se puede calcular latencia del broker
    - Compensación temporal fallida
    - Desfase excesivo entre brokers
    - Buffer de compensación overflow
    """
    
    def __init__(
        self, 
        message: str, 
        broker: str,
        latency_ms: Optional[float] = None,
        compensation_attempted: bool = False,
        context: Optional[Dict[str, Any]] = None
    ):
        error_code = "TN_LATENCY_COMPENSATION"
        ctx = context or {}
        ctx.update({
            "broker": broker,
            "compensation_attempted": compensation_attempted
        })
        
        if latency_ms is not None:
            ctx["latency_ms"] = latency_ms
            
        super().__init__(message, error_code, ctx)


class UnknownBrokerError(TickNormalizationError):
    """
    Excepción para broker no reconocido o no soportado.
    
    Se lanza cuando:
    - Broker no registrado en el dispatcher
    - Normalizer no disponible para el broker
    - Configuración de broker faltante
    """
    
    def __init__(
        self, 
        message: str, 
        broker: str,
        available_brokers: Optional[list] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        error_code = "TN_UNKNOWN_BROKER"
        ctx = context or {}
        ctx.update({
            "unknown_broker": broker
        })
        
        if available_brokers:
            ctx["available_brokers"] = available_brokers
            
        super().__init__(message, error_code, ctx)


class TickProcessingError(TickNormalizationError):
    """
    Excepción para errores generales en el procesamiento de ticks.
    
    Se lanza cuando:
    - Error en pipeline de procesamiento
    - Excepción no capturada en normalizer
    - Fallo en validación post-procesamiento
    """
    
    def __init__(
        self, 
        message: str, 
        processing_stage: str,
        original_exception: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        error_code = "TN_PROCESSING"
        ctx = context or {}
        ctx.update({
            "processing_stage": processing_stage
        })
        
        if original_exception:
            ctx["original_exception"] = {
                "type": type(original_exception).__name__,
                "message": str(original_exception)
            }
            
        super().__init__(message, error_code, ctx)


class ConfigurationError(TickNormalizationError):
    """
    Excepción para errores de configuración del sistema.
    
    Se lanza cuando:
    - Configuración faltante o inválida
    - Parámetros fuera de rango
    - Dependencias no disponibles
    """
    
    def __init__(
        self, 
        message: str, 
        config_section: Optional[str] = None,
        config_key: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        error_code = "TN_CONFIGURATION"
        ctx = context or {}
        
        if config_section:
            ctx["config_section"] = config_section
        if config_key:
            ctx["config_key"] = config_key
            
        super().__init__(message, error_code, ctx)


# Excepciones de conveniencia para casos específicos
class DuplicateTickError(DataQualityError):
    """Excepción específica para ticks duplicados."""
    
    def __init__(self, timestamp: str, symbol: str, broker: str):
        message = f"Duplicate tick detected for {symbol} at {timestamp}"
        super().__init__(
            message,
            quality_issue="duplicate_tick",
            context={
                "timestamp": timestamp,
                "symbol": symbol,
                "broker": broker
            }
        )


class OutOfSequenceError(DataQualityError):
    """Excepción específica para ticks fuera de secuencia temporal."""
    
    def __init__(self, expected_ts: str, received_ts: str, symbol: str):
        message = f"Out of sequence tick for {symbol}: expected >= {expected_ts}, got {received_ts}"
        super().__init__(
            message,
            quality_issue="out_of_sequence",
            context={
                "expected_timestamp": expected_ts,
                "received_timestamp": received_ts,
                "symbol": symbol
            }
        )


class RateLimitExceededError(BrokerConnectionError):
    """Excepción específica para rate limits excedidos."""
    
    def __init__(self, broker: str, limit: int, current_rate: int):
        message = f"Rate limit exceeded for {broker}: {current_rate}/{limit} requests"
        super().__init__(
            message,
            broker=broker,
            connection_type="rate_limit",
            context={
                "rate_limit": limit,
                "current_rate": current_rate
            }
        )


# Funciones utilitarias para manejo de excepciones
def handle_tick_error(
    error: Exception, 
    broker: str, 
    tick_data: Optional[Dict[str, Any]] = None
) -> TickNormalizationError:
    """
    Convierte excepciones genéricas a excepciones específicas del tick normalizer.
    
    Args:
        error: Excepción original
        broker: Nombre del broker donde ocurrió el error
        tick_data: Datos del tick que causó el error (opcional)
    
    Returns:
        TickNormalizationError apropiada para el tipo de error
    """
    context = {"broker": broker}
    if tick_data:
        context["tick_data"] = tick_data
    
    if isinstance(error, TickNormalizationError):
        return error
    
    # Mapeo de excepciones comunes
    error_type = type(error).__name__
    error_message = str(error)
    context["original_error_type"] = error_type
    
    # Mapeo por tipo específico (más preciso que keywords)
    connection_errors = {"ConnectionError", "TimeoutError", "URLError", "HTTPError", "RequestException"}
    data_errors = {"ValueError", "TypeError", "JSONDecodeError", "KeyError", "IndexError"}
    
    if error_type in connection_errors or any(keyword in error_message.lower() for keyword in ["connection", "timeout", "network"]):
        return BrokerConnectionError(
            f"Connection error with {broker}: {error_message}",
            broker=broker,
            context=context
        )
    
    if error_type in data_errors or any(keyword in error_message.lower() for keyword in ["invalid", "format", "parse"]):
        return InvalidTickDataError(
            f"Data format error from {broker}: {error_message}",
            context=context
        )
    
    # Error genérico de procesamiento
    return TickProcessingError(
        f"Processing error for {broker}: {error_message}",
        processing_stage="unknown",
        original_exception=error,
        context=context
    )


def is_retryable_error(error: TickNormalizationError) -> bool:
    """
    Determina si un error es recuperable y se puede reintentar.
    
    Args:
        error: Excepción del tick normalizer
    
    Returns:
        True si el error es recuperable, False caso contrario
    """
    # Errores de conexión generalmente son recuperables
    if isinstance(error, BrokerConnectionError):
        return True
    
    # Errores de latencia pueden ser temporales
    if isinstance(error, LatencyCompensationError):
        return True
    
    # Errores de configuración no son recuperables
    if isinstance(error, (ConfigurationError, UnknownBrokerError)):
        return False
    
    # Errores de datos generalmente no son recuperables
    if isinstance(error, (InvalidTickDataError, DataQualityError)):
        return False
    
    # Por defecto, errores de procesamiento pueden reintentarse
    return isinstance(error, TickProcessingError)