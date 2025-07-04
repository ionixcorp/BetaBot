"""
Clase Base para Métricas de Velas - Sistema Asíncrono Multi-Asset
================================================================

Esta clase base proporciona la infraestructura común para todas las métricas
del sistema, incluyendo gestión asíncrona, configuración centralizada,
y procesamiento multi-asset sin mezcla de información.

Las métricas reciben ticks normalizados (UnifiedTick) del módulo tick_normalizer,
que valida la integridad de los datos, incluyendo el campo de volumen, basado en
la configuración del broker (volume_available: bool). Las métricas NO deben validar
el campo de volumen y deben usar la configuración volume_available para decidir
entre cálculos basados en volumen (with_volume) o proxies robustos basados en
precio y timestamp (price_only).

Configuración requerida en metrics.yaml:
```yaml
metrics:
  [categoria_carpeta]:
    [nombre_metrica]:
      enabled: true
      window_size: 50
      buffer_limit: 1000
      volume_preferred: false
      custom_params:
        # Parámetros específicos de la métrica
```
Configuración del broker (en brokers.yaml, manejado por config_manager):
```yaml
brokers:
  [broker_name]:
    volume_available: bool
```

Autor: Sistema Bet-AG
Fecha: 2025
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Callable, Deque, Dict, List, Optional, Set, Union  # noqa: F401
from weakref import WeakSet  # noqa: F401

from ...config_manager import ConfigManager
from .exceptions import (  # noqa: F401
    BaseMetricException,
    ConcurrencyError,
    InsufficientDataError,
    MetricCalculationError,
    MetricConfigurationError,
    MetricInitializationError,
    MetricMemoryError,
    MetricStateError,
    MetricTimeoutError,
    TickValidationError,
    handle_metric_exception,
    require_minimum_ticks,
    validate_tick_data,
)

from core.tick_normalyzer.base import UnifiedTick  # Importar UnifiedTick


@dataclass
class MetricResult:
    """
    Resultado de cálculo de una métrica.
    
    Contiene el valor calculado junto con metadata relevante.
    """
    value: Union[float, Decimal, Dict[str, Any]]
    timestamp: datetime
    symbol: str
    broker: str
    metric_name: str
    quality_score: float = 1.0
    calculation_time_ms: float = 0.0
    ticks_used: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetricConfiguration:
    """
    Configuración de una métrica específica.
    """
    enabled: bool = True
    window_size: int = 50
    buffer_limit: int = 1000
    volume_preferred: bool = False  # Cambiado de volume_required a volume_preferred
    timeout_seconds: float = 5.0
    memory_limit_mb: float = 100.0
    custom_params: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_config_dict(cls, config_dict: Dict[str, Any]) -> 'MetricConfiguration':
        """Crea configuración desde diccionario de configuración."""
        return cls(
            enabled=config_dict.get('enabled', True),
            window_size=config_dict.get('window_size', 50),
            buffer_limit=config_dict.get('buffer_limit', 1000),
            volume_preferred=config_dict.get('volume_preferred', False),
            timeout_seconds=config_dict.get('timeout_seconds', 5.0),
            memory_limit_mb=config_dict.get('memory_limit_mb', 100.0),
            custom_params=config_dict.get('custom_params', {})
        )


class BaseMetric(ABC):
    """
    Clase base abstracta para todas las métricas del sistema.
    
    Proporciona:
    - Gestión asíncrona completa
    - Separación por símbolo/broker
    - Configuración centralizada
    - Validación de datos (excepto volumen, manejada por tick_normalizer)
    - Manejo de errores
    - Monitoreo de rendimiento
    """
    
    def __init__(
        self,
        config_manager: ConfigManager,
        category: str,
        metric_name: str,
        logger: Optional[logging.Logger] = None
    ):
        """
        Inicializa la métrica base.
        
        Args:
            config_manager: Gestor de configuración centralizado
            category: Categoría de la métrica (ej: 'momentum_intrabar')
            metric_name: Nombre específico de la métrica
            logger: Logger opcional
        """
        self.config_manager = config_manager
        self.category = category
        self.metric_name = metric_name
        self.logger = logger or logging.getLogger(f"metrics.{category}.{metric_name}")
        
        # Configuración de la métrica
        self.config: MetricConfiguration = self._load_configuration()
        
        # Verificar disponibilidad de volumen por broker
        self._volume_available: Dict[str, bool] = {}  # broker -> bool
        self._initialize_volume_availability()
        
        # Almacenamiento por símbolo/broker - thread-safe
        self._tick_buffers: Dict[str, Dict[str, Deque[UnifiedTick]]] = defaultdict(lambda: defaultdict(deque))
        self._last_calculations: Dict[str, Dict[str, MetricResult]] = defaultdict(dict)
        self._locks: Dict[str, Dict[str, asyncio.Lock]] = defaultdict(lambda: defaultdict(asyncio.Lock))
        
        # Estadísticas y monitoreo
        self._active_symbols: Set[str] = set()
        self._active_brokers: Set[str] = set()
        self._calculation_count: int = 0
        self._error_count: int = 0
        self._total_processing_time: float = 0.0
        
        # Control de memoria y rendimiento
        self._memory_usage_mb: float = 0.0
        self._last_cleanup: datetime = datetime.now()
        
        # Validación inicial
        self._validate_configuration()
        
        self.logger.info(
            f"Métrica {self.metric_name} inicializada",
            extra={
                "category": self.category,
                "enabled": self.config.enabled,
                "window_size": self.config.window_size,
                "volume_preferred": self.config.volume_preferred
            }
        )
    
    def _initialize_volume_availability(self) -> None:
        """Inicializa la disponibilidad de volumen por broker desde la configuración."""
        try:
            brokers_config = self.config_manager.get_configuration("brokers") or {}
            for broker in brokers_config:
                self._volume_available[broker] = brokers_config.get(broker, {}).get('volume_available', False)
        except Exception as e:
            self.logger.warning(f"Error cargando configuración de volumen por broker: {e!s}")
            self._volume_available = defaultdict(lambda: False)  # Default a False si hay error
    
    def _validate_metrics_config(self, metrics_config: Optional[Dict]) -> None:
        """Valida la configuración de métricas."""
        if not metrics_config:
            raise MetricConfigurationError(
                "No se encontró configuración de métricas",
                metric_name=self.metric_name
            )
    
    def _validate_category_config(self, category_config: Optional[Dict]) -> None:
        """Valida la configuración de categoría."""
        if not category_config:
            raise MetricConfigurationError(
                f"No se encontró configuración para categoría {self.category}",
                metric_name=self.metric_name
            )
    
    def _validate_metric_config(self, metric_config: Optional[Dict]) -> None:
        """Valida la configuración específica de la métrica."""
        if not metric_config:
            raise MetricConfigurationError(
                f"No se encontró configuración para métrica {self.metric_name}",
                metric_name=self.metric_name
            )
    
    def _load_configuration(self) -> MetricConfiguration:
        """Carga la configuración de la métrica desde config_manager."""
        try:
            # Obtener configuración de métricas
            metrics_config = self.config_manager.get_configuration("metrics")
            self._validate_metrics_config(metrics_config)
            
            # Navegar a la configuración específica
            category_config = metrics_config.get(self.category)
            self._validate_category_config(category_config)
            
            metric_config = category_config.get(self.metric_name)
            self._validate_metric_config(metric_config)
            
            return MetricConfiguration.from_config_dict(metric_config)
            
        except Exception as e:
            raise MetricInitializationError(
                f"Error cargando configuración: {e!s}",
                metric_name=self.metric_name
            ) from e
    
    def _validate_configuration(self) -> None:
        """Valida la configuración cargada."""
        if self.config.window_size <= 0:
            raise MetricConfigurationError(
                f"window_size debe ser positivo: {self.config.window_size}",
                metric_name=self.metric_name
            )
        
        if self.config.buffer_limit <= self.config.window_size:
            raise MetricConfigurationError(
                f"buffer_limit ({self.config.buffer_limit}) debe ser mayor que window_size ({self.config.window_size})",
                metric_name=self.metric_name
            )
        
        if self.config.timeout_seconds <= 0:
            raise MetricConfigurationError(
                f"timeout_seconds debe ser positivo: {self.config.timeout_seconds}",
                metric_name=self.metric_name
            )
    
    def _get_asset_key(self, symbol: str, broker: str) -> str:
        """Genera clave única para combinación símbolo/broker."""
        return f"{broker}:{symbol}"
    
    async def process_tick(self, tick: UnifiedTick) -> Optional[MetricResult]:
        """
        Procesa un tick normalizado y calcula la métrica si es posible.
        
        Args:
            tick: Tick normalizado (UnifiedTick) procesado por tick_normalizer
            
        Returns:
            MetricResult si se pudo calcular, None en caso contrario
            
        Raises:
            TickValidationError: Si el tick no es válido
            MetricCalculationError: Si hay error en el cálculo
        """
        if not self.config.enabled:
            return None
        
        start_time = datetime.now()
        
        try:
            # Validar tick (sin validación de volumen, manejada por tick_normalizer)
            self._validate_tick(tick)
            
            # Obtener clave del asset
            asset_key = self._get_asset_key(tick.symbol, tick.broker)
            
            # Procesar de forma thread-safe
            async with self._locks[tick.broker][tick.symbol]:
                # Agregar tick al buffer
                await self._add_tick_to_buffer(tick)
                
                # Intentar calcular métrica
                result = await self._calculate_metric_safe(tick)
                
                if result:
                    # Actualizar estadísticas
                    self._update_statistics(start_time)
                    
                    # Guardar último resultado
                    self._last_calculations[tick.broker][tick.symbol] = result
                    
                    self.logger.debug(
                        f"Métrica calculada para {asset_key}",
                        extra={
                            "value": result.value,
                            "ticks_used": result.ticks_used,
                            "calculation_time_ms": result.calculation_time_ms
                        }
                    )
                
                return result
                
        except Exception as e:
            self._error_count += 1
            handle_metric_exception(
                e, self.metric_name, tick.symbol, tick.broker, self.logger
            )
            return None
    
    def _validate_tick(self, tick: UnifiedTick) -> None:
        """Valida un tick normalizado antes de procesarlo."""
        # Validación básica (campos requeridos)
        validate_tick_data(tick, ['timestamp', 'symbol', 'broker', 'price'])
        
        # Validaciones adicionales específicas de la métrica
        self._validate_tick_specific(tick)
    
    def _validate_tick_specific(self, tick: UnifiedTick) -> None:  # noqa: B027
        """
        Validaciones específicas de cada métrica.
        
        Debe ser implementado por las métricas que requieran validaciones adicionales
        más allá de los campos básicos. NO debe validar el campo de volumen,
        ya que esto lo maneja tick_normalizer.
        """
        pass
    
    async def _add_tick_to_buffer(self, tick: UnifiedTick) -> None:
        """Agrega un tick normalizado al buffer correspondiente."""
        buffer = self._tick_buffers[tick.broker][tick.symbol]
        buffer.append(tick)
        
        # Mantener límite del buffer
        while len(buffer) > self.config.buffer_limit:
            buffer.popleft()
        
        # Actualizar conjuntos de activos activos
        self._active_symbols.add(tick.symbol)
        self._active_brokers.add(tick.broker)
        
        # Limpieza periódica de memoria
        await self._periodic_cleanup()
    
    async def _calculate_metric_safe(self, tick: UnifiedTick) -> Optional[MetricResult]:
        """Calcula la métrica de forma segura con timeout."""
        try:
            # Aplicar timeout
            result = await asyncio.wait_for(
                self._calculate_metric(tick),
                timeout=self.config.timeout_seconds
            )
            return result
            
        except asyncio.TimeoutError as e:
            raise MetricTimeoutError(
                f"Cálculo de métrica excedió timeout de {self.config.timeout_seconds}s",
                timeout_seconds=self.config.timeout_seconds,
                metric_name=self.metric_name,
                symbol=tick.symbol,
                broker=tick.broker
            ) from e
        except Exception as e:
            raise MetricCalculationError(
                f"Error en cálculo de métrica: {e!s}",
                metric_name=self.metric_name,
                symbol=tick.symbol,
                broker=tick.broker
            ) from e
    
    @abstractmethod
    async def _calculate_metric(self, tick: UnifiedTick) -> Optional[MetricResult]:
        """
        Calcula la métrica específica.
        
        Debe ser implementado por cada métrica concreta.
        Usa self._volume_available[tick.broker] para decidir entre lógica
        with_volume o price_only. No valida tick.volume.
        
        Args:
            tick: Tick normalizado (UnifiedTick) actual que disparó el cálculo
            
        Returns:
            MetricResult con el valor calculado o None si no se puede calcular
        """
        pass
    
    def _get_tick_buffer(self, symbol: str, broker: str) -> Deque[UnifiedTick]:
        """Obtiene el buffer de ticks para un asset específico."""
        return self._tick_buffers[broker][symbol]
    
    def _get_sufficient_ticks(
        self, 
        symbol: str, 
        broker: str, 
        required_count: Optional[int] = None
    ) -> List[UnifiedTick]:
        """
        Obtiene ticks suficientes para el cálculo.
        
        Args:
            symbol: Símbolo del asset
            broker: Broker del asset
            required_count: Cantidad mínima requerida (usa window_size por defecto)
            
        Returns:
            Lista de ticks normalizados suficientes
            
        Raises:
            InsufficientDataError: Si no hay suficientes ticks
        """
        required_count = required_count or self.config.window_size
        buffer = self._get_tick_buffer(symbol, broker)
        
        require_minimum_ticks(
            len(buffer), required_count, self.metric_name, symbol, broker
        )
        
        # Devolver los últimos N ticks
        return list(buffer)[-required_count:]
    
    def _update_statistics(self, start_time: datetime) -> None:
        """Actualiza estadísticas de rendimiento."""
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        self._total_processing_time += processing_time
        self._calculation_count += 1
    
    async def _periodic_cleanup(self) -> None:
        """Limpieza periódica de memoria y recursos."""
        now = datetime.now()
        if (now - self._last_cleanup).total_seconds() > 300:  # 5 minutos
            await self._cleanup_old_data()
            self._last_cleanup = now
    
    async def _cleanup_old_data(self) -> None:
        """Limpia datos antiguos para liberar memoria."""
        # Limpiar buffers que excedan el límite de memoria
        for broker in list(self._tick_buffers.keys()):
            for symbol in list(self._tick_buffers[broker].keys()):
                buffer = self._tick_buffers[broker][symbol]
                if len(buffer) > self.config.buffer_limit:
                    # Mantener solo los ticks más recientes
                    new_buffer = deque(list(buffer)[-self.config.buffer_limit:])
                    self._tick_buffers[broker][symbol] = new_buffer
    
    # Métodos de consulta y estado
    
    def get_last_result(self, symbol: str, broker: str) -> Optional[MetricResult]:
        """Obtiene el último resultado calculado para un asset."""
        return self._last_calculations.get(broker, {}).get(symbol)
    
    def get_buffer_size(self, symbol: str, broker: str) -> int:
        """Obtiene el tamaño actual del buffer para un asset."""
        return len(self._tick_buffers[broker][symbol])
    
    def is_ready(self, symbol: str, broker: str) -> bool:
        """Verifica si la métrica está lista para calcular en un asset."""
        return self.get_buffer_size(symbol, broker) >= self.config.window_size
    
    def get_active_assets(self) -> List[str]:
        """Obtiene lista de assets activos (broker:symbol)."""
        assets = []
        for broker in self._active_brokers:
            for symbol in self._active_symbols:
                if self.get_buffer_size(symbol, broker) > 0:
                    assets.append(f"{broker}:{symbol}")
        return assets
    
    def get_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas de rendimiento de la métrica."""
        avg_processing_time = (
            self._total_processing_time / self._calculation_count
            if self._calculation_count > 0 else 0
        )
        
        return {
            "metric_name": self.metric_name,
            "category": self.category,
            "enabled": self.config.enabled,
            "calculation_count": self._calculation_count,
            "error_count": self._error_count,
            "avg_processing_time_ms": avg_processing_time,
            "active_assets": len(self.get_active_assets()),
            "active_symbols": len(self._active_symbols),
            "active_brokers": len(self._active_brokers),
            "memory_usage_mb": self._memory_usage_mb,
            "buffer_total_size": sum(
                sum(len(buffer) for buffer in broker_buffers.values())
                for broker_buffers in self._tick_buffers.values()
            )
        }
    
    async def reset_asset(self, symbol: str, broker: str) -> None:
        """Resetea los datos de un asset específico."""
        async with self._locks[broker][symbol]:
            if broker in self._tick_buffers and symbol in self._tick_buffers[broker]:
                self._tick_buffers[broker][symbol].clear()
            
            if broker in self._last_calculations and symbol in self._last_calculations[broker]:
                del self._last_calculations[broker][symbol]
        
        self.logger.info(f"Asset {broker}:{symbol} reseteado")
    
    async def reset_all(self) -> None:
        """Resetea todos los datos de la métrica."""
        self._tick_buffers.clear()
        self._last_calculations.clear()
        self._locks.clear()
        
        # Resetear estadísticas
        self._active_symbols.clear()
        self._active_brokers.clear()
        self._calculation_count = 0
        self._error_count = 0
        self._total_processing_time = 0.0
        self._memory_usage_mb = 0.0
        self._last_cleanup = datetime.now()
        
        self.logger.info(f"Métrica {self.metric_name} completamente reseteada")
    
    def __str__(self) -> str:
        """Representación en string de la métrica."""
        return f"{self.__class__.__name__}({self.category}.{self.metric_name})"
    
    def __repr__(self) -> str:
        """Representación detallada de la métrica."""
        return (
            f"{self.__class__.__name__}("
            f"category='{self.category}', "
            f"metric_name='{self.metric_name}', "
            f"enabled={self.config.enabled}, "
            f"window_size={self.config.window_size}"
            f")"
        )
    
    async def __aenter__(self):
        """Entrada del context manager asíncrono."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Salida del context manager asíncrono con limpieza."""
        await self.reset_all()
        if exc_type:
            self.logger.error(
                f"Error en métrica {self.metric_name}: {exc_val}",
                extra={"exception_type": exc_type.__name__}
            )
        return False
    
    # Métodos de utilidad para métricas derivadas
    
    def _calculate_price_change(self, current_price: float, previous_price: float) -> float:
        """Calcula el cambio porcentual entre dos precios."""
        if previous_price == 0:
            return 0.0
        return ((current_price - previous_price) / previous_price) * 100
    
    def _calculate_volatility_simple(self, prices: List[float]) -> float:
        """Calcula volatilidad simple como desviación estándar de precios."""
        if len(prices) < 2:
            return 0.0
        
        mean_price = sum(prices) / len(prices)
        variance = sum((price - mean_price) ** 2 for price in prices) / len(prices)
        return variance ** 0.5
    
    def _get_ohlc_from_ticks(self, ticks: List[UnifiedTick]) -> Dict[str, float]:
        """
        Extrae OHLC de una lista de ticks normalizados.
        
        Args:
            ticks: Lista de ticks normalizados ordenados por timestamp
            
        Returns:
            Dict con open, high, low, close
        """
        if not ticks:
            return {"open": 0.0, "high": 0.0, "low": 0.0, "close": 0.0}
        
        prices = [tick.price for tick in ticks]
        return {
            "open": prices[0],
            "high": max(prices),
            "low": min(prices),
            "close": prices[-1]
        }
    
    def _calculate_typical_price(self, high: float, low: float, close: float) -> float:
        """Calcula precio típico (HLC/3)."""
        return (high + low + close) / 3
    
    def _calculate_weighted_price(self, high: float, low: float, close: float, volume: float = 1.0) -> float:
        """Calcula precio ponderado por volumen."""
        return ((high + low + close) / 3) * volume
    
    def _get_time_window_ticks(
        self, 
        symbol: str, 
        broker: str, 
        minutes: int
    ) -> List[UnifiedTick]:
        """
        Obtiene ticks normalizados dentro de una ventana de tiempo específica.
        
        Args:
            symbol: Símbolo del asset
            broker: Broker del asset
            minutes: Minutos hacia atrás desde el último tick
            
        Returns:
            Lista de ticks normalizados dentro de la ventana
        """
        buffer = self._get_tick_buffer(symbol, broker)
        if not buffer:
            return []
        
        latest_tick = buffer[-1]
        cutoff_time = latest_tick.timestamp - timedelta(minutes=minutes)
        
        return [
            tick for tick in buffer 
            if tick.timestamp >= cutoff_time
        ]
    
    def _validate_price_sequence(self, prices: List[float], max_gap_percent: float = 10.0) -> bool:
        """
        Valida que una secuencia de precios no tenga gaps anómalos.
        
        Args:
            prices: Lista de precios a validar
            max_gap_percent: Máximo porcentaje de gap permitido
            
        Returns:
            True si la secuencia es válida
        """
        if len(prices) < 2:
            return True
        
        for i in range(1, len(prices)):
            if prices[i-1] == 0:
                continue
            
            gap_percent = abs((prices[i] - prices[i-1]) / prices[i-1]) * 100
            if gap_percent > max_gap_percent:
                return False
        
        return True
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Verifica el estado de salud de la métrica.
        
        Returns:
            Dict con información de salud de la métrica
        """
        try:
            stats = self.get_statistics()
            active_assets = self.get_active_assets()
            
            # Calcular métricas de salud
            error_rate = (
                (self._error_count / self._calculation_count * 100) 
                if self._calculation_count > 0 else 0
            )
            
            memory_usage_percent = (
                (self._memory_usage_mb / self.config.memory_limit_mb * 100)
                if self.config.memory_limit_mb > 0 else 0
            )
            
            # Determinar estado de salud
            health_status = "healthy"
            issues = []
            
            if error_rate > 5.0:  # Más del 5% de errores
                health_status = "warning"
                issues.append(f"Alta tasa de errores: {error_rate:.1f}%")
            
            if memory_usage_percent > 80.0:  # Más del 80% de memoria
                health_status = "warning"
                issues.append(f"Alto uso de memoria: {memory_usage_percent:.1f}%")
            
            if not self.config.enabled:
                health_status = "disabled"
                issues.append("Métrica deshabilitada")
            
            if len(active_assets) == 0 and self.config.enabled:
                health_status = "warning"
                issues.append("No hay assets activos")
            
            return {
                "metric_name": self.metric_name,
                "category": self.category,
                "status": health_status,
                "enabled": self.config.enabled,
                "issues": issues,
                "statistics": stats,
                "active_assets_count": len(active_assets),
                "error_rate_percent": error_rate,
                "memory_usage_percent": memory_usage_percent,
                "last_check": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "metric_name": self.metric_name,
                "category": self.category,
                "status": "error",
                "error": str(e),
                "last_check": datetime.now().isoformat()
            }