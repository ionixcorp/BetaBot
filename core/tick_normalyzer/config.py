"""
Configuración del Tick Normalizer
Bet-AG Trading System - Integración con sistema de configuración
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from ..config_manager import ConfigManager


@dataclass
class TickNormalizerConfig:
    """Configuración unificada del tick normalizer desde archivos YAML."""
    
    # Configuración de calidad de datos
    min_quality_score: float = 0.7
    max_spread_percentage: float = 5.0
    max_age_seconds: int = 60
    duplicate_detection: bool = True
    duplicate_window_seconds: float = 2.0
    
    # Configuración de compensación de latencia
    latency_compensation_enabled: bool = True
    latency_method: str = "adaptive"
    fixed_latency_ms: float = 150.0
    min_latency_ms: float = 50.0
    max_latency_ms: float = 800.0
    confidence_threshold: float = 0.7
    measurement_window_size: int = 50
    
    # Configuración de validación
    price_positive: bool = True
    volume_non_negative: bool = True
    spread_validation: bool = True
    timestamp_validation: bool = True
    sequence_validation: bool = True
    anomaly_detection: bool = True
    
    # Configuración de detección de anomalías
    price_sigma_threshold: float = 2.5
    volume_sigma_threshold: float = 2.0
    anomaly_window_size: int = 30
    anomaly_min_samples: int = 5
    
    # Configuración de performance
    buffer_size: int = 5000
    batch_size: int = 50
    performance_max_latency_ms: float = 500
    processing_threads: int = 1
    queue_max_size: int = 2000
    
    # Configuración de logging
    log_level: str = "DEBUG"
    log_raw_data: bool = True
    log_normalized_ticks: bool = True
    log_validation_details: bool = True
    log_latency_measurements: bool = True


class TickNormalizerConfigManager:
    """Gestor de configuración específico para el tick normalizer."""
    
    def __init__(self, config_manager: ConfigManager):
        """
        Inicializa el gestor de configuración del tick normalizer.
        
        Args:
            config_manager: Instancia del gestor de configuración principal
        """
        self.config_manager = config_manager
    
    def get_broker_config(self, broker_name: str) -> Optional[TickNormalizerConfig]:
        """
        Obtiene la configuración del tick normalizer para un broker específico.
        
        Args:
            broker_name: Nombre del broker
            
        Returns:
            TickNormalizerConfig: Configuración del tick normalizer o None si no existe
        """
        try:
            # Obtener configuración del broker
            broker_config = self.config_manager.get_broker_config(broker_name)
            if not broker_config:
                return None
            
            # Obtener configuración específica del tick_normalizer
            tick_normalizer_config = broker_config.get('tick_normalizer', {})
            if not tick_normalizer_config:
                return None
            
            return self._parse_tick_normalizer_config(tick_normalizer_config)
            
        except Exception:
            return None
    
    def _parse_tick_normalizer_config(self, config: Dict[str, Any]) -> TickNormalizerConfig:
        """
        Parsea la configuración del tick normalizer desde el diccionario.
        
        Args:
            config: Configuración del tick normalizer
            
        Returns:
            TickNormalizerConfig: Configuración parseada
        """
        # Extraer configuración de data_quality
        data_quality = config.get('data_quality', {})
        min_quality_score = data_quality.get('min_quality_score', 0.7)
        max_spread_percentage = data_quality.get('max_spread_percentage', 5.0)
        max_age_seconds = data_quality.get('max_age_seconds', 60)
        duplicate_detection = data_quality.get('duplicate_detection', True)
        duplicate_window_seconds = data_quality.get('duplicate_window_seconds', 2.0)
        
        # Extraer configuración de latency_compensation
        latency_compensation = config.get('latency_compensation', {})
        latency_compensation_enabled = latency_compensation.get('enabled', True)
        latency_method = latency_compensation.get('method', 'adaptive')
        fixed_latency_ms = latency_compensation.get('fixed_latency_ms', 150.0)
        min_latency_ms = latency_compensation.get('min_latency_ms', 50.0)
        max_latency_ms = latency_compensation.get('max_latency_ms', 800.0)
        confidence_threshold = latency_compensation.get('confidence_threshold', 0.7)
        measurement_window_size = latency_compensation.get('measurement_window_size', 50)
        
        # Extraer configuración de validation
        validation = config.get('validation', {})
        price_positive = validation.get('price_positive', True)
        volume_non_negative = validation.get('volume_non_negative', True)
        spread_validation = validation.get('spread_validation', True)
        timestamp_validation = validation.get('timestamp_validation', True)
        sequence_validation = validation.get('sequence_validation', True)
        anomaly_detection = validation.get('anomaly_detection', True)
        
        # Extraer configuración de anomaly_detection
        anomaly_config = config.get('anomaly_detection', {})
        price_sigma_threshold = anomaly_config.get('price_sigma_threshold', 2.5)
        volume_sigma_threshold = anomaly_config.get('volume_sigma_threshold', 2.0)
        anomaly_window_size = anomaly_config.get('window_size', 30)
        anomaly_min_samples = anomaly_config.get('min_samples', 5)
        
        # Extraer configuración de performance
        performance = config.get('performance', {})
        buffer_size = performance.get('buffer_size', 5000)
        batch_size = performance.get('batch_size', 50)
        performance_max_latency_ms = performance.get('max_latency_ms', 500)
        processing_threads = performance.get('processing_threads', 1)
        queue_max_size = performance.get('queue_max_size', 2000)
        
        # Extraer configuración de logging
        logging_config = config.get('logging', {})
        log_level = logging_config.get('level', 'DEBUG')
        log_raw_data = logging_config.get('log_raw_data', True)
        log_normalized_ticks = logging_config.get('log_normalized_ticks', True)
        log_validation_details = logging_config.get('log_validation_details', True)
        log_latency_measurements = logging_config.get('log_latency_measurements', True)
        
        return TickNormalizerConfig(
            min_quality_score=min_quality_score,
            max_spread_percentage=max_spread_percentage,
            max_age_seconds=max_age_seconds,
            duplicate_detection=duplicate_detection,
            duplicate_window_seconds=duplicate_window_seconds,
            latency_compensation_enabled=latency_compensation_enabled,
            latency_method=latency_method,
            fixed_latency_ms=fixed_latency_ms,
            min_latency_ms=min_latency_ms,
            max_latency_ms=max_latency_ms,
            confidence_threshold=confidence_threshold,
            measurement_window_size=measurement_window_size,
            price_positive=price_positive,
            volume_non_negative=volume_non_negative,
            spread_validation=spread_validation,
            timestamp_validation=timestamp_validation,
            sequence_validation=sequence_validation,
            anomaly_detection=anomaly_detection,
            price_sigma_threshold=price_sigma_threshold,
            volume_sigma_threshold=volume_sigma_threshold,
            anomaly_window_size=anomaly_window_size,
            anomaly_min_samples=anomaly_min_samples,
            buffer_size=buffer_size,
            batch_size=batch_size,
            performance_max_latency_ms=performance_max_latency_ms,
            processing_threads=processing_threads,
            queue_max_size=queue_max_size,
            log_level=log_level,
            log_raw_data=log_raw_data,
            log_normalized_ticks=log_normalized_ticks,
            log_validation_details=log_validation_details,
            log_latency_measurements=log_latency_measurements
        )
    
    def get_default_config(self) -> TickNormalizerConfig:
        """
        Obtiene la configuración por defecto.
        
        Returns:
            TickNormalizerConfig: Configuración por defecto
        """
        return TickNormalizerConfig() 