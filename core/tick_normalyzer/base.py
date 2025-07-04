"""
Tick Normalizer Base Classes
Bet-AG Trading System - Clases base y modelos de datos unificados
"""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class TickType(Enum):
    """Tipos de tick soportados."""
    BID_ASK = "bid_ask"
    TRADE = "trade"
    QUOTE = "quote"
    BOOK = "book"


class BrokerType(Enum):
    """Brokers soportados."""
    BINANCE = "binance"
    DERIV = "deriv"
    IQOPTION = "iqoption"
    MT5 = "mt5"


@dataclass
class UnifiedTick:
    """
    Estructura unificada de tick para todos los brokers.
    
    Esta clase representa la forma normalizada de un tick,
    independientemente del broker de origen.
    """
    
    # Campos obligatorios
    timestamp: datetime
    symbol: str
    broker: str
    price: Decimal
    
    # Campos opcionales de mercado
    volume: Optional[Decimal] = None
    bid: Optional[Decimal] = None
    ask: Optional[Decimal] = None
    spread: Optional[Decimal] = None
    
    # Metadatos de calidad
    quality_score: float = 1.0
    latency_ms: float = 0.0
    
    # Datos originales y metadatos
    raw_data: Dict[str, Any] = field(default_factory=dict)
    tick_type: TickType = TickType.TRADE
    sequence_id: Optional[int] = None
    
    # Timestamps adicionales para análisis
    broker_timestamp: Optional[datetime] = None
    received_timestamp: Optional[datetime] = None
    processed_timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        """Validaciones y ajustes post-inicialización."""
        # Asegurar que received_timestamp esté establecido
        if self.received_timestamp is None:
            self.received_timestamp = datetime.utcnow()
        
        # Calcular spread si bid/ask están disponibles
        if self.bid and self.ask and self.spread is None:
            self.spread = self.ask - self.bid
        
        # Validaciones básicas
        if self.price <= 0:
            raise ValueError(f"Price must be positive, got {self.price}")
        
        if self.volume is not None and self.volume < 0:
            raise ValueError(f"Volume cannot be negative, got {self.volume}")
        
        if self.spread is not None and self.spread < 0:
            raise ValueError(f"Spread cannot be negative, got {self.spread}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte el tick a diccionario para serialización."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "symbol": self.symbol,
            "broker": self.broker,
            "price": float(self.price),
            "volume": float(self.volume) if self.volume else None,
            "bid": float(self.bid) if self.bid else None,
            "ask": float(self.ask) if self.ask else None,
            "spread": float(self.spread) if self.spread else None,
            "quality_score": self.quality_score,
            "latency_ms": self.latency_ms,
            "tick_type": self.tick_type.value,
            "sequence_id": self.sequence_id,
            "broker_timestamp": self.broker_timestamp.isoformat() if self.broker_timestamp else None,
            "received_timestamp": self.received_timestamp.isoformat() if self.received_timestamp else None,
            "processed_timestamp": self.processed_timestamp.isoformat() if self.processed_timestamp else None,
            "raw_data": self.raw_data
        }
    
    def to_json(self) -> str:
        """Convierte el tick a JSON."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UnifiedTick':
        """Crea un UnifiedTick desde un diccionario."""
        # Convertir timestamps
        timestamp = datetime.fromisoformat(data["timestamp"])
        broker_timestamp = datetime.fromisoformat(data["broker_timestamp"]) if data.get("broker_timestamp") else None
        received_timestamp = datetime.fromisoformat(data["received_timestamp"]) if data.get("received_timestamp") else None
        processed_timestamp = datetime.fromisoformat(data["processed_timestamp"]) if data.get("processed_timestamp") else None
        
        # Convertir Decimals
        price = Decimal(str(data["price"]))
        volume = Decimal(str(data["volume"])) if data.get("volume") else None
        bid = Decimal(str(data["bid"])) if data.get("bid") else None
        ask = Decimal(str(data["ask"])) if data.get("ask") else None
        spread = Decimal(str(data["spread"])) if data.get("spread") else None
        
        # Convertir tick_type
        tick_type = TickType(data.get("tick_type", "trade"))
        
        return cls(
            timestamp=timestamp,
            symbol=data["symbol"],
            broker=data["broker"],
            price=price,
            volume=volume,
            bid=bid,
            ask=ask,
            spread=spread,
            quality_score=data.get("quality_score", 1.0),
            latency_ms=data.get("latency_ms", 0.0),
            raw_data=data.get("raw_data", {}),
            tick_type=tick_type,
            sequence_id=data.get("sequence_id"),
            broker_timestamp=broker_timestamp,
            received_timestamp=received_timestamp,
            processed_timestamp=processed_timestamp
        )
    
    def is_valid_spread(self, max_spread_percent: float = 5.0) -> bool:
        """Verifica si el spread está dentro de límites razonables."""
        if not (self.bid and self.ask):
            return True  # No se puede validar sin bid/ask
        
        if self.spread is None:
            return False
        
        spread_percent = (self.spread / self.price) * 100
        return spread_percent <= max_spread_percent
    
    def is_stale(self, max_age_seconds: int = 60) -> bool:
        """Verifica si el tick es demasiado antiguo."""
        if not self.received_timestamp:
            return True
        
        age = (datetime.utcnow() - self.received_timestamp).total_seconds()
        return age > max_age_seconds
    
    def calculate_mid_price(self) -> Optional[Decimal]:
        """Calcula el precio medio bid/ask."""
        if self.bid and self.ask:
            return (self.bid + self.ask) / Decimal('2')
        return None


@dataclass
class NormalizationConfig:
    """Configuración para normalización de ticks."""
    
    # Validación de calidad
    min_quality_score: float = 0.7
    max_spread_percent: float = 5.0
    max_tick_age_seconds: int = 60
    
    # Compensación de latencia
    enable_latency_compensation: bool = True
    max_latency_ms: float = 1000.0
    
    # Detección de duplicados
    enable_duplicate_detection: bool = True
    duplicate_window_seconds: int = 1
    
    # Logging
    enable_detailed_logging: bool = False
    log_raw_data: bool = False
    
    # Performance
    max_buffer_size: int = 10000
    batch_size: int = 100
    
    @classmethod
    def from_tick_normalizer_config(cls, config) -> 'NormalizationConfig':
        """
        Crea una NormalizationConfig desde TickNormalizerConfig.
        
        Args:
            config: TickNormalizerConfig del config_manager
            
        Returns:
            NormalizationConfig: Configuración para el normalizador
        """
        return cls(
            min_quality_score=config.min_quality_score,
            max_spread_percent=config.max_spread_percentage,
            max_tick_age_seconds=config.max_age_seconds,
            enable_latency_compensation=config.latency_compensation_enabled,
            max_latency_ms=config.max_latency_ms,
            enable_duplicate_detection=config.duplicate_detection,
            duplicate_window_seconds=int(config.duplicate_window_seconds),
            enable_detailed_logging=config.log_validation_details,
            log_raw_data=config.log_raw_data,
            max_buffer_size=config.buffer_size,
            batch_size=config.batch_size
        )


class BaseTickNormalizer(ABC):
    """
    Clase base abstracta para todos los normalizadores de tick.
    
    Define la interfaz común que deben implementar todos los
    normalizadores específicos de broker.
    """
    
    def __init__(self, config: Optional[NormalizationConfig] = None, config_manager_config=None):
        """
        Inicializa el normalizador base.
        
        Args:
            config: Configuración de normalización (opcional)
            config_manager_config: Configuración del config_manager (opcional)
        """
        if config_manager_config:
            # Usar configuración del config_manager
            self.config = NormalizationConfig.from_tick_normalizer_config(config_manager_config)
        else:
            # Usar configuración por defecto o proporcionada
            self.config = config or NormalizationConfig()
            
        self.broker_name = self._get_broker_name()
        self._processed_count = 0
        self._error_count = 0
        self._last_sequence_id = 0
        self._seen_ticks: Dict[str, datetime] = {}  # Para detección de duplicados
        
        # Métricas de performance
        self.metrics = {
            "processed_ticks": 0,
            "failed_ticks": 0,
            "quality_failures": 0,
            "duplicate_ticks": 0,
            "average_latency_ms": 0.0,
            "last_tick_timestamp": None
        }
    
    @abstractmethod
    def _get_broker_name(self) -> str:
        """Retorna el nombre del broker."""
        pass
    
    @abstractmethod
    def normalize(self, raw_tick: Dict[str, Any]) -> UnifiedTick:
        """
        Normaliza un tick raw del broker al formato UnifiedTick.
        
        Args:
            raw_tick: Datos raw del tick del broker
            
        Returns:
            UnifiedTick normalizado
            
        Raises:
            InvalidTickDataError: Si los datos son inválidos
            TickProcessingError: Si hay error en el procesamiento
        """
        pass
    
    @abstractmethod
    def _extract_timestamp(self, raw_tick: Dict[str, Any]) -> datetime:
        """Extrae timestamp del tick raw."""
        pass
    
    @abstractmethod
    def _extract_symbol(self, raw_tick: Dict[str, Any]) -> str:
        """Extrae símbolo del tick raw."""
        pass
    
    @abstractmethod
    def _extract_price(self, raw_tick: Dict[str, Any]) -> Decimal:
        """Extrae precio del tick raw."""
        pass
    
    def validate_tick(self, tick: UnifiedTick) -> bool:
        """
        Valida un tick normalizado.
        
        Args:
            tick: Tick normalizado a validar
            
        Returns:
            True si el tick es válido, False caso contrario
        """
        try:
            # Validación básica de campos
            if not tick.timestamp or not tick.symbol or not tick.broker:
                return False
            
            if tick.price <= 0:
                return False
            
            # Validación de spread
            if not tick.is_valid_spread(self.config.max_spread_percent):
                return False
            
            # Validación de antiguedad
            if tick.is_stale(self.config.max_tick_age_seconds):
                return False
            
            # Validación de calidad mínima
            if tick.quality_score < self.config.min_quality_score:
                return False
            
            return True
            
        except Exception:
            return False
    
    def calculate_quality_score(self, raw_tick: Dict[str, Any], normalized_tick: UnifiedTick) -> float:
        """
        Calcula score de calidad para el tick.
        
        Args:
            raw_tick: Datos originales del tick
            normalized_tick: Tick normalizado
            
        Returns:
            Score de calidad entre 0.0 y 1.0
        """
        score = 1.0
        
        # Penalizar por campos faltantes en datos normalizados
        if not normalized_tick.volume:
            score -= 0.1
        
        if not (normalized_tick.bid and normalized_tick.ask):
            score -= 0.15
        
        # Penalizar por latencia alta
        if normalized_tick.latency_ms > self.config.max_latency_ms:
            latency_penalty = min(0.3, normalized_tick.latency_ms / self.config.max_latency_ms * 0.3)
            score -= latency_penalty
        
        # Penalizar por spread ancho
        if normalized_tick.spread and normalized_tick.price:
            spread_percent = (normalized_tick.spread / normalized_tick.price) * 100
            if spread_percent > 1.0:  # Spread > 1%
                spread_penalty = min(0.2, spread_percent / 100 * 0.2)
                score -= spread_penalty
        
        # Bonus por completitud de datos normalizados
        completeness_score = len([f for f in [normalized_tick.volume, normalized_tick.bid, normalized_tick.ask] if f is not None]) / 3
        score += completeness_score * 0.1
        
        # Validaciones adicionales basadas en raw_tick
        if raw_tick:
            # Penalizar si raw_tick está vacío o es muy pequeño
            if len(raw_tick) < 3:
                score -= 0.1
            
            # Verificar consistencia entre raw_tick y normalized_tick
            raw_price = raw_tick.get('price') or raw_tick.get('close') or raw_tick.get('last')
            if raw_price is not None:
                try:
                    raw_price_decimal = Decimal(str(raw_price))
                    price_diff = abs(raw_price_decimal - normalized_tick.price)
                    price_diff_percent = (price_diff / normalized_tick.price) * 100
                    
                    # Penalizar si hay diferencia significativa en precio
                    if price_diff_percent > 0.1:  # Diferencia > 0.1%
                        score -= min(0.2, price_diff_percent / 100 * 0.2)
                except (ValueError, TypeError, ZeroDivisionError):
                    score -= 0.1
            
            # Verificar si raw_tick tiene campos de calidad
            quality_indicators = ['quality', 'confidence', 'reliability', 'source_quality']
            has_quality_info = any(indicator in raw_tick for indicator in quality_indicators)
            if has_quality_info:
                # Bonus por tener información de calidad en raw_tick
                score += 0.05
            
            # Verificar si raw_tick tiene timestamps adicionales
            timestamp_fields = ['server_timestamp', 'exchange_timestamp', 'local_timestamp']
            has_additional_timestamps = any(field in raw_tick for field in timestamp_fields)
            if has_additional_timestamps:
                # Bonus por tener timestamps adicionales
                score += 0.03
            
            # Penalizar si raw_tick tiene errores o campos de error
            error_indicators = ['error', 'status', 'valid', 'success']
            has_errors = any(
                raw_tick.get(indicator) in [False, 'error', 'failed', 'invalid'] 
                for indicator in error_indicators 
                if indicator in raw_tick
            )
            if has_errors:
                score -= 0.3
        
        return max(0.0, min(1.0, score))
    
    def is_duplicate(self, tick: UnifiedTick) -> bool:
        """Detecta si un tick es duplicado."""
        if not self.config.enable_duplicate_detection:
            return False
        
        tick_key = f"{tick.symbol}_{tick.timestamp.isoformat()}_{tick.price}"
        
        if tick_key in self._seen_ticks:
            # Verificar si está dentro de la ventana de duplicados
            time_diff = abs((tick.timestamp - self._seen_ticks[tick_key]).total_seconds())
            if time_diff <= self.config.duplicate_window_seconds:
                return True
        
        # Limpiar ticks antiguos del cache
        cutoff_time = tick.timestamp.timestamp() - self.config.duplicate_window_seconds
        self._seen_ticks = {
            k: v for k, v in self._seen_ticks.items() 
            if v.timestamp() > cutoff_time
        }
        
        # Agregar tick actual
        self._seen_ticks[tick_key] = tick.timestamp
        return False
    
    def update_metrics(self, tick: UnifiedTick, success: bool = True):
        """Actualiza métricas del normalizador."""
        if success:
            self.metrics["processed_ticks"] += 1
            self._processed_count += 1
            
            # Actualizar latencia promedio
            current_avg = self.metrics["average_latency_ms"]
            total_processed = self.metrics["processed_ticks"]
            self.metrics["average_latency_ms"] = (
                (current_avg * (total_processed - 1) + tick.latency_ms) / total_processed
            )
            
            self.metrics["last_tick_timestamp"] = tick.timestamp.isoformat()
        else:
            self.metrics["failed_ticks"] += 1
            self._error_count += 1
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retorna estadísticas del normalizador."""
        total_ticks = self.metrics["processed_ticks"] + self.metrics["failed_ticks"]
        success_rate = (self.metrics["processed_ticks"] / total_ticks * 100) if total_ticks > 0 else 0
        
        return {
            "broker": self.broker_name,
            "total_processed": self.metrics["processed_ticks"],
            "total_failed": self.metrics["failed_ticks"],
            "success_rate_percent": round(success_rate, 2),
            "average_latency_ms": round(self.metrics["average_latency_ms"], 2),
            "quality_failures": self.metrics["quality_failures"],
            "duplicate_ticks": self.metrics["duplicate_ticks"],
            "last_tick_timestamp": self.metrics["last_tick_timestamp"],
            "configuration": {
                "min_quality_score": self.config.min_quality_score,
                "max_spread_percent": self.config.max_spread_percent,
                "latency_compensation": self.config.enable_latency_compensation
            }
        }
    
    def reset_statistics(self):
        """Resetea todas las estadísticas."""
        self.metrics = {
            "processed_ticks": 0,
            "failed_ticks": 0,
            "quality_failures": 0,
            "duplicate_ticks": 0,
            "average_latency_ms": 0.0,
            "last_tick_timestamp": None
        }
        self._processed_count = 0
        self._error_count = 0
        self._seen_ticks.clear()


# Funciones utilitarias
def create_test_tick(
    symbol: str = "BTCUSDT",
    broker: str = "test",
    price: Union[float, Decimal] = Decimal("50000.00"),
    timestamp: Optional[datetime] = None
) -> UnifiedTick:
    """Crea un tick de prueba con valores por defecto."""
    return UnifiedTick(
        timestamp=timestamp or datetime.utcnow(),
        symbol=symbol,
        broker=broker,
        price=Decimal(str(price)) if not isinstance(price, Decimal) else price,
        volume=Decimal("1.0"),
        bid=Decimal(str(price)) * Decimal("0.999"),
        ask=Decimal(str(price)) * Decimal("1.001"),
        quality_score=1.0,
        latency_ms=10.0
    )


def validate_tick_data(data: Dict[str, Any]) -> List[str]:
    """
    Valida datos de tick y retorna lista de errores.
    
    Args:
        data: Diccionario con datos de tick
        
    Returns:
        Lista de errores encontrados (vacía si no hay errores)
    """
    errors = []
    
    # Campos requeridos
    required_fields = ["timestamp", "symbol", "broker", "price"]
    for required_field in required_fields:  # Cambio: field → required_field
        if required_field not in data or data[required_field] is None:
            errors.append(f"Missing required field: {required_field}")
    
    # Validación de tipos y valores
    if "price" in data:
        try:
            price = float(data["price"])
            if price <= 0:
                errors.append("Price must be positive")
        except (ValueError, TypeError):
            errors.append("Price must be a valid number")
    
    if "volume" in data and data["volume"] is not None:
        try:
            volume = float(data["volume"])
            if volume < 0:
                errors.append("Volume cannot be negative")
        except (ValueError, TypeError):
            errors.append("Volume must be a valid number")
    
    # Validación de spread bid/ask
    if all(field_name in data and data[field_name] is not None for field_name in ["bid", "ask"]):  # Cambio: field → field_name
        try:
            bid = float(data["bid"])
            ask = float(data["ask"])
            if ask <= bid:
                errors.append("Ask price must be greater than bid price")
        except (ValueError, TypeError):
            errors.append("Bid and ask prices must be valid numbers")
    
    return errors