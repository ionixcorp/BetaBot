"""
Data Quality Validation Module
Bet-AG Trading System - Motor de validación de calidad de datos
"""

import json  # noqa: F401
import statistics
import time
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta  # noqa: F401
from decimal import Decimal  # noqa: F401
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple  # noqa: F401

from .base import NormalizationConfig, UnifiedTick  # noqa: F401


class ValidationSeverity(Enum):
    """Severidad de las validaciones."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ValidationResult(Enum):
    """Resultado de validación."""
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    SKIP = "skip"


@dataclass
class ValidationIssue:
    """Representa un problema de validación."""
    rule_name: str
    severity: ValidationSeverity
    message: str
    field: Optional[str] = None
    expected_value: Optional[Any] = None
    actual_value: Optional[Any] = None
    context: Dict[str, Any] = None
    
    def __post_init__(self):
        """Inicializa context si es None."""
        if self.context is None:
            self.context = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario."""
        return {
            "rule": self.rule_name,
            "severity": self.severity.value,
            "message": self.message,
            "field": self.field,
            "expected": self.expected_value,
            "actual": self.actual_value,
            "context": self.context
        }


@dataclass
class ValidationReport:
    """Reporte completo de validación."""
    tick_id: str
    timestamp: datetime
    result: ValidationResult
    quality_score: float
    issues: List[ValidationIssue] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    processing_time_ms: float = 0.0
    
    def is_valid(self) -> bool:
        """Verifica si el tick pasó la validación."""
        return self.result == ValidationResult.PASS
    
    def has_errors(self) -> bool:
        """Verifica si hay errores críticos."""
        return any(issue.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL] 
                  for issue in self.issues)
    
    def get_issues_by_severity(self, severity: ValidationSeverity) -> List[ValidationIssue]:
        """Obtiene issues por severidad."""
        return [issue for issue in self.issues if issue.severity == severity]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario."""
        return {
            "tick_id": self.tick_id,
            "timestamp": self.timestamp.isoformat(),
            "result": self.result.value,
            "quality_score": self.quality_score,
            "processing_time_ms": self.processing_time_ms,
            "issues": [issue.to_dict() for issue in self.issues],
            "metrics": self.metrics
        }


class ValidationRule(ABC):
    """Clase base para reglas de validación."""
    
    def __init__(self, name: str, severity: ValidationSeverity = ValidationSeverity.ERROR,
                 enabled: bool = True, config: Optional[Dict[str, Any]] = None):
        self.name = name
        self.severity = severity
        self.enabled = enabled
        self.config = config or {}
        self.execution_count = 0
        self.failure_count = 0
        self.total_execution_time = 0.0
    
    @abstractmethod
    def validate(self, tick: UnifiedTick, context: Dict[str, Any]) -> Optional[ValidationIssue]:
        """
        Valida un tick.
        
        Args:
            tick: Tick a validar
            context: Contexto adicional para validación
            
        Returns:
            ValidationIssue si hay problema, None si está OK
        """
        pass
    
    def execute(self, tick: UnifiedTick, context: Dict[str, Any]) -> Optional[ValidationIssue]:
        """Ejecuta la validación con métricas."""
        if not self.enabled:
            return None
        
        start_time = time.perf_counter()
        try:
            result = self.validate(tick, context)
            if result:
                self.failure_count += 1
            return result
        finally:
            self.execution_count += 1
            self.total_execution_time += (time.perf_counter() - start_time) * 1000
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas de la regla."""
        return {
            "name": self.name,
            "enabled": self.enabled,
            "executions": self.execution_count,
            "failures": self.failure_count,
            "failure_rate": self.failure_count / max(1, self.execution_count),
            "avg_execution_time_ms": self.total_execution_time / max(1, self.execution_count)
        }


# Reglas de validación específicas
class PricePositiveRule(ValidationRule):
    """Valida que el precio sea positivo."""
    
    def __init__(self):
        super().__init__("price_positive", ValidationSeverity.CRITICAL)
    
    def validate(self, tick: UnifiedTick, context: Dict[str, Any]) -> Optional[ValidationIssue]:
        # Usar contexto para configuraciones dinámicas
        min_price = context.get('min_price', 0)
        price_tolerance = context.get('price_tolerance', 0.0)
        
        if tick.price <= min_price + price_tolerance:
            return ValidationIssue(
                rule_name=self.name,
                severity=self.severity,
                message=f"Price must be positive, got {tick.price}",
                field="price",
                expected_value=f"> {min_price + price_tolerance}",
                actual_value=float(tick.price),
                context={
                    "min_price": min_price,
                    "tolerance": price_tolerance,
                    "broker": tick.broker,
                    "symbol": tick.symbol
                }
            )
        return None


class VolumeNonNegativeRule(ValidationRule):
    """Valida que el volumen no sea negativo."""
    
    def __init__(self):
        super().__init__("volume_non_negative", ValidationSeverity.ERROR)
    
    def validate(self, tick: UnifiedTick, context: Dict[str, Any]) -> Optional[ValidationIssue]:
        # Usar contexto para validaciones específicas de mercado
        market_hours = context.get('market_hours', {})
        current_time = datetime.utcnow()
        
        if tick.volume is not None and tick.volume < 0:
            return ValidationIssue(
                rule_name=self.name,
                severity=self.severity,
                message=f"Volume cannot be negative, got {tick.volume}",
                field="volume",
                expected_value=">= 0",
                actual_value=float(tick.volume),
                context={
                    "market_hours": market_hours,
                    "current_time": current_time.isoformat(),
                    "broker": tick.broker,
                    "symbol": tick.symbol
                }
            )
        return None


class SpreadValidRule(ValidationRule):
    """Valida spread bid/ask."""
    
    def __init__(self, max_spread_percent: float = 5.0):
        super().__init__("spread_valid", ValidationSeverity.WARNING)
        self.max_spread_percent = max_spread_percent
    
    def validate(self, tick: UnifiedTick, context: Dict[str, Any]) -> Optional[ValidationIssue]:
        # Usar contexto para configuraciones dinámicas de spread
        dynamic_max_spread = context.get('max_spread_percent', self.max_spread_percent)
        volatility_factor = context.get('volatility_factor', 1.0)
        adjusted_max_spread = dynamic_max_spread * volatility_factor
        
        if tick.bid and tick.ask:
            if tick.ask <= tick.bid:
                return ValidationIssue(
                    rule_name=self.name,
                    severity=ValidationSeverity.ERROR,
                    message=f"Ask ({tick.ask}) must be greater than bid ({tick.bid})",
                    field="spread",
                    actual_value={"bid": float(tick.bid), "ask": float(tick.ask)},
                    context={
                        "broker": tick.broker,
                        "symbol": tick.symbol,
                        "volatility_factor": volatility_factor
                    }
                )
            
            spread_percent = ((tick.ask - tick.bid) / tick.price) * 100
            if spread_percent > adjusted_max_spread:
                return ValidationIssue(
                    rule_name=self.name,
                    severity=self.severity,
                    message=f"Spread too wide: {spread_percent:.2f}% > {adjusted_max_spread:.2f}%",
                    field="spread",
                    expected_value=f"<= {adjusted_max_spread:.2f}%",
                    actual_value=f"{spread_percent:.2f}%",
                    context={
                        "original_max_spread": self.max_spread_percent,
                        "adjusted_max_spread": adjusted_max_spread,
                        "volatility_factor": volatility_factor,
                        "broker": tick.broker,
                        "symbol": tick.symbol
                    }
                )
        return None


class TimestampValidRule(ValidationRule):
    """Valida timestamp del tick."""
    
    def __init__(self, max_age_seconds: int = 300, max_future_seconds: int = 10):
        super().__init__("timestamp_valid", ValidationSeverity.ERROR)
        self.max_age_seconds = max_age_seconds
        self.max_future_seconds = max_future_seconds
    
    def validate(self, tick: UnifiedTick, context: Dict[str, Any]) -> Optional[ValidationIssue]:
        # Usar contexto para configuraciones de tiempo dinámicas
        dynamic_max_age = context.get('max_age_seconds', self.max_age_seconds)
        dynamic_max_future = context.get('max_future_seconds', self.max_future_seconds)
        timezone_offset = context.get('timezone_offset', 0)
        
        now = datetime.utcnow()
        age_seconds = (now - tick.timestamp).total_seconds()
        
        if age_seconds > dynamic_max_age:
            return ValidationIssue(
                rule_name=self.name,
                severity=self.severity,
                message=f"Tick too old: {age_seconds:.1f}s > {dynamic_max_age}s",
                field="timestamp",
                expected_value=f"within {dynamic_max_age}s",
                actual_value=f"{age_seconds:.1f}s ago",
                context={
                    "original_max_age": self.max_age_seconds,
                    "dynamic_max_age": dynamic_max_age,
                    "timezone_offset": timezone_offset,
                    "broker": tick.broker,
                    "symbol": tick.symbol
                }
            )
        
        if age_seconds < -dynamic_max_future:
            return ValidationIssue(
                rule_name=self.name,
                severity=self.severity,
                message=f"Tick from future: {-age_seconds:.1f}s ahead",
                field="timestamp",
                expected_value=f"within {dynamic_max_future}s future",
                actual_value=f"{-age_seconds:.1f}s ahead",
                context={
                    "original_max_future": self.max_future_seconds,
                    "dynamic_max_future": dynamic_max_future,
                    "timezone_offset": timezone_offset,
                    "broker": tick.broker,
                    "symbol": tick.symbol
                }
            )
        
        return None


class SequenceValidRule(ValidationRule):
    """Valida secuencia de ticks."""
    
    def __init__(self):
        super().__init__("sequence_valid", ValidationSeverity.WARNING)
        self.last_timestamps: Dict[str, datetime] = {}
    
    def validate(self, tick: UnifiedTick, context: Dict[str, Any]) -> Optional[ValidationIssue]:
        # Usar contexto para configuraciones de secuencia
        allow_out_of_sequence = context.get('allow_out_of_sequence', False)
        max_sequence_gap = context.get('max_sequence_gap_seconds', 60)
        
        key = f"{tick.broker}_{tick.symbol}"
        
        if key in self.last_timestamps:
            last_ts = self.last_timestamps[key]
            time_diff = (tick.timestamp - last_ts).total_seconds()
            
            if tick.timestamp < last_ts and not allow_out_of_sequence:
                return ValidationIssue(
                    rule_name=self.name,
                    severity=self.severity,
                    message=f"Out of sequence tick: {tick.timestamp} < {last_ts}",
                    field="timestamp",
                    context={
                        "broker": tick.broker,
                        "symbol": tick.symbol,
                        "time_diff_seconds": time_diff,
                        "allow_out_of_sequence": allow_out_of_sequence,
                        "max_sequence_gap": max_sequence_gap
                    }
                )
            
            # Verificar gaps muy grandes en secuencia
            if time_diff > max_sequence_gap:
                return ValidationIssue(
                    rule_name=self.name,
                    severity=ValidationSeverity.WARNING,
                    message=f"Large sequence gap: {time_diff:.1f}s > {max_sequence_gap}s",
                    field="timestamp",
                    context={
                        "broker": tick.broker,
                        "symbol": tick.symbol,
                        "time_diff_seconds": time_diff,
                        "max_sequence_gap": max_sequence_gap
                    }
                )
        
        self.last_timestamps[key] = tick.timestamp
        return None


@dataclass
class AnomalyDetectorConfig:
    """Configuración para detector de anomalías."""
    price_sigma_threshold: float = 3.0
    volume_sigma_threshold: float = 3.0
    window_size: int = 100
    min_samples: int = 10
    enable_price_detection: bool = True
    enable_volume_detection: bool = True


class AnomalyDetector:
    """Detector de anomalías estadísticas."""
    
    def __init__(self, config: AnomalyDetectorConfig):
        self.config = config
        self.price_windows: Dict[str, deque] = defaultdict(lambda: deque(maxlen=config.window_size))
        self.volume_windows: Dict[str, deque] = defaultdict(lambda: deque(maxlen=config.window_size))
    
    def add_tick(self, tick: UnifiedTick):
        """Agrega tick a las ventanas estadísticas."""
        key = f"{tick.broker}_{tick.symbol}"
        
        if self.config.enable_price_detection:
            self.price_windows[key].append(float(tick.price))
        
        if self.config.enable_volume_detection and tick.volume:
            self.volume_windows[key].append(float(tick.volume))
    
    def detect_price_anomaly(self, tick: UnifiedTick) -> Optional[ValidationIssue]:
        """Detecta anomalías en precio."""
        if not self.config.enable_price_detection:
            return None
        
        key = f"{tick.broker}_{tick.symbol}"
        window = self.price_windows[key]
        
        if len(window) < self.config.min_samples:
            return None
        
        prices = list(window)
        mean_price = statistics.mean(prices)
        std_price = statistics.stdev(prices) if len(prices) > 1 else 0
        
        if std_price == 0:
            return None
        
        z_score = abs(float(tick.price) - mean_price) / std_price
        
        if z_score > self.config.price_sigma_threshold:
            return ValidationIssue(
                rule_name="price_anomaly",
                severity=ValidationSeverity.WARNING,
                message=f"Price anomaly detected: z-score {z_score:.2f}",
                field="price",
                actual_value=float(tick.price),
                context={
                    "z_score": z_score,
                    "mean": mean_price,
                    "std": std_price,
                    "threshold": self.config.price_sigma_threshold
                }
            )
        
        return None
    
    def detect_volume_anomaly(self, tick: UnifiedTick) -> Optional[ValidationIssue]:
        """Detecta anomalías en volumen."""
        if not self.config.enable_volume_detection or not tick.volume:
            return None
        
        key = f"{tick.broker}_{tick.symbol}"
        window = self.volume_windows[key]
        
        if len(window) < self.config.min_samples:
            return None
        
        volumes = list(window)
        mean_volume = statistics.mean(volumes)
        std_volume = statistics.stdev(volumes) if len(volumes) > 1 else 0
        
        if std_volume == 0:
            return None
        
        z_score = abs(float(tick.volume) - mean_volume) / std_volume
        
        if z_score > self.config.volume_sigma_threshold:
            return ValidationIssue(
                rule_name="volume_anomaly",
                severity=ValidationSeverity.WARNING,
                message=f"Volume anomaly detected: z-score {z_score:.2f}",
                field="volume",
                actual_value=float(tick.volume),
                context={
                    "z_score": z_score,
                    "mean": mean_volume,
                    "std": std_volume,
                    "threshold": self.config.volume_sigma_threshold
                }
            )
        
        return None


@dataclass
class DQVConfig:
    """Configuración del motor de validación."""
    
    # Reglas básicas
    validate_price: bool = True
    validate_volume: bool = True
    validate_spread: bool = True
    validate_timestamp: bool = True
    validate_sequence: bool = True
    
    # Parámetros de validación
    max_spread_percent: float = 5.0
    max_tick_age_seconds: int = 300
    max_future_seconds: int = 10
    
    # Detección de anomalías
    enable_anomaly_detection: bool = True
    anomaly_config: Optional[AnomalyDetectorConfig] = None
    
    # Calidad mínima
    min_quality_score: float = 0.6
    
    # Performance
    max_validation_time_ms: float = 5.0
    enable_rule_stats: bool = True
    
    def __post_init__(self):
        if self.anomaly_config is None:
            self.anomaly_config = AnomalyDetectorConfig()
    
    @classmethod
    def from_tick_normalizer_config(cls, config) -> 'DQVConfig':
        """
        Crea una DQVConfig desde TickNormalizerConfig.
        
        Args:
            config: TickNormalizerConfig del config_manager
            
        Returns:
            DQVConfig: Configuración para el validador
        """
        # Crear configuración de anomalías
        anomaly_config = AnomalyDetectorConfig(
            price_sigma_threshold=config.price_sigma_threshold,
            volume_sigma_threshold=config.volume_sigma_threshold,
            window_size=config.anomaly_window_size,
            min_samples=config.anomaly_min_samples,
            enable_price_detection=config.anomaly_detection,
            enable_volume_detection=config.anomaly_detection
        )
        
        return cls(
            validate_price=config.price_positive,
            validate_volume=config.volume_non_negative,
            validate_spread=config.spread_validation,
            validate_timestamp=config.timestamp_validation,
            validate_sequence=config.sequence_validation,
            max_spread_percent=config.max_spread_percentage,
            max_tick_age_seconds=config.max_age_seconds,
            enable_anomaly_detection=config.anomaly_detection,
            anomaly_config=anomaly_config,
            min_quality_score=config.min_quality_score
        )


class DataQualityValidator:
    """Motor principal de validación de calidad de datos."""
    
    def __init__(self, config: Optional[DQVConfig] = None, config_manager_config=None):
        """
        Inicializa el validador de calidad de datos.
        
        Args:
            config: Configuración del validador (opcional)
            config_manager_config: Configuración del config_manager (opcional)
        """
        if config_manager_config:
            # Usar configuración del config_manager
            self.config = DQVConfig.from_tick_normalizer_config(config_manager_config)
        else:
            # Usar configuración por defecto o proporcionada
            self.config = config or DQVConfig()
            
        self.rules: List[ValidationRule] = []
        self.anomaly_detector = AnomalyDetector(self.config.anomaly_config)
        
        # Métricas
        self.total_validations = 0
        self.total_failures = 0
        self.total_processing_time = 0.0
        
        self._setup_default_rules()
    
    def _setup_default_rules(self):
        """Configura reglas por defecto."""
        if self.config.validate_price:
            self.rules.append(PricePositiveRule())
        
        if self.config.validate_volume:
            self.rules.append(VolumeNonNegativeRule())
        
        if self.config.validate_spread:
            self.rules.append(SpreadValidRule(self.config.max_spread_percent))
        
        if self.config.validate_timestamp:
            self.rules.append(TimestampValidRule(
                self.config.max_tick_age_seconds,
                self.config.max_future_seconds
            ))
        
        if self.config.validate_sequence:
            self.rules.append(SequenceValidRule())
    
    def add_rule(self, rule: ValidationRule):
        """Agrega regla personalizada."""
        self.rules.append(rule)
    
    def remove_rule(self, rule_name: str) -> bool:
        """Remueve regla por nombre."""
        for i, rule in enumerate(self.rules):
            if rule.name == rule_name:
                del self.rules[i]
                return True
        return False
    
    def validate_tick(self, tick: UnifiedTick, context: Optional[Dict[str, Any]] = None) -> ValidationReport:
        """
        Valida un tick completo.
        
        Args:
            tick: Tick a validar
            context: Contexto adicional para validación. Puede incluir:
                - Configuraciones específicas del broker
                - Condiciones de mercado (volatilidad, horarios)
                - Configuraciones de tiempo
                - Parámetros personalizados de validación
                
        Returns:
            Reporte completo de validación
            
        Example:
            # Validación básica
            report = validator.validate_tick(tick)
            
            # Validación con contexto específico del broker
            broker_context = create_broker_context(
                broker_name="binance",
                symbol="BTCUSDT",
                volatility_factor=1.2
            )
            report = validator.validate_tick(tick, broker_context)
            
            # Validación con condiciones de mercado
            market_context = create_market_context(
                market_volatility=1.5,
                trading_session="asian"
            )
            report = validator.validate_tick(tick, market_context)
        """
        start_time = time.perf_counter()
        context = context or {}
        issues = []
        
        # ID único para el tick
        tick_id = f"{tick.broker}_{tick.symbol}_{tick.timestamp.isoformat()}_{id(tick)}"
        
        try:
            # Ejecutar reglas básicas
            for rule in self.rules:
                issue = rule.execute(tick, context)
                if issue:
                    issues.append(issue)
            
            # Detección de anomalías
            if self.config.enable_anomaly_detection:
                anomalies = self._detect_anomalies(tick)
                issues.extend(anomalies)
            
            # Calcular resultado final
            result = self._calculate_result(issues)
            quality_score = self._calculate_quality_score(tick, issues)
            
            # Agregar tick al detector para futuras comparaciones
            if self.config.enable_anomaly_detection:
                self.anomaly_detector.add_tick(tick)
            
            processing_time = (time.perf_counter() - start_time) * 1000
            
            # Crear reporte
            report = ValidationReport(
                tick_id=tick_id,
                timestamp=datetime.utcnow(),
                result=result,
                quality_score=quality_score,
                issues=issues,
                processing_time_ms=processing_time,
                metrics={
                    "rules_executed": len([r for r in self.rules if r.enabled]),
                    "anomaly_checks": 2 if self.config.enable_anomaly_detection else 0
                }
            )
            
            # Actualizar métricas
            self._update_metrics(report)
            
            return report
            
        except Exception as e:
            # Error en validación
            processing_time = (time.perf_counter() - start_time) * 1000
            
            critical_issue = ValidationIssue(
                rule_name="validation_error",
                severity=ValidationSeverity.CRITICAL,
                message=f"Validation engine error: {e!s}",
                context={"exception_type": type(e).__name__}
            )
            
            return ValidationReport(
                tick_id=tick_id,
                timestamp=datetime.utcnow(),
                result=ValidationResult.FAIL,
                quality_score=0.0,
                issues=[critical_issue],
                processing_time_ms=processing_time
            )
    
    def _detect_anomalies(self, tick: UnifiedTick) -> List[ValidationIssue]:
        """Detecta anomalías estadísticas."""
        anomalies = []
        
        # Anomalías de precio
        price_anomaly = self.anomaly_detector.detect_price_anomaly(tick)
        if price_anomaly:
            anomalies.append(price_anomaly)
        
        # Anomalías de volumen
        volume_anomaly = self.anomaly_detector.detect_volume_anomaly(tick)
        if volume_anomaly:
            anomalies.append(volume_anomaly)
        
        return anomalies
    
    def _calculate_result(self, issues: List[ValidationIssue]) -> ValidationResult:
        """Calcula resultado final basado en issues."""
        if not issues:
            return ValidationResult.PASS
        
        has_critical = any(issue.severity == ValidationSeverity.CRITICAL for issue in issues)
        has_error = any(issue.severity == ValidationSeverity.ERROR for issue in issues)
        
        if has_critical or has_error:
            return ValidationResult.FAIL
        
        return ValidationResult.WARN
    
    def _calculate_quality_score(self, tick: UnifiedTick, issues: List[ValidationIssue]) -> float:
        """Calcula score de calidad basado en issues."""
        base_score = 1.0
        
        for issue in issues:
            if issue.severity == ValidationSeverity.CRITICAL:
                base_score -= 0.4
            elif issue.severity == ValidationSeverity.ERROR:
                base_score -= 0.2
            elif issue.severity == ValidationSeverity.WARNING:
                base_score -= 0.1
            else:  # INFO
                base_score -= 0.05
        
        # Bonus por completitud de datos
        completeness = sum([
            1 if tick.volume else 0,
            1 if tick.bid else 0,
            1 if tick.ask else 0
        ]) / 3
        
        base_score += completeness * 0.1
        
        return max(0.0, min(1.0, base_score))
    
    def _update_metrics(self, report: ValidationReport):
        """Actualiza métricas del validador."""
        self.total_validations += 1
        self.total_processing_time += report.processing_time_ms
        
        if not report.is_valid():
            self.total_failures += 1
    
    def get_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas del validador."""
        avg_processing_time = (
            self.total_processing_time / max(1, self.total_validations)
        )
        
        failure_rate = (
            self.total_failures / max(1, self.total_validations) * 100
        )
        
        return {
            "total_validations": self.total_validations,
            "total_failures": self.total_failures,
            "failure_rate_percent": round(failure_rate, 2),
            "average_processing_time_ms": round(avg_processing_time, 3),
            "rule_statistics": [rule.get_stats() for rule in self.rules],
            "configuration": {
                "rules_enabled": len([r for r in self.rules if r.enabled]),
                "anomaly_detection": self.config.enable_anomaly_detection,
                "min_quality_score": self.config.min_quality_score
            }
        }
    
    def reset_statistics(self):
        """Resetea todas las estadísticas."""
        self.total_validations = 0
        self.total_failures = 0
        self.total_processing_time = 0.0
        
        for rule in self.rules:
            rule.execution_count = 0
            rule.failure_count = 0
            rule.total_execution_time = 0.0


# Funciones utilitarias
def create_validation_context(
    broker_config: Optional[Dict[str, Any]] = None,
    market_conditions: Optional[Dict[str, Any]] = None,
    time_settings: Optional[Dict[str, Any]] = None,
    custom_settings: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Crea un contexto de validación con configuraciones útiles.
    
    Args:
        broker_config: Configuración específica del broker
        market_conditions: Condiciones de mercado (volatilidad, etc.)
        time_settings: Configuraciones de tiempo
        custom_settings: Configuraciones personalizadas
        
    Returns:
        Contexto de validación
    """
    context = {}
    
    # Configuración del broker
    if broker_config:
        context.update(broker_config)
    
    # Condiciones de mercado
    if market_conditions:
        context.update(market_conditions)
    
    # Configuraciones de tiempo
    if time_settings:
        context.update(time_settings)
    
    # Configuraciones personalizadas
    if custom_settings:
        context.update(custom_settings)
    
    return context


def create_broker_context(
    broker_name: str,
    symbol: str,
    volatility_factor: float = 1.0,
    spread_tolerance: float = 1.0,
    timezone_offset: int = 0
) -> Dict[str, Any]:
    """
    Crea contexto específico para un broker.
    
    Args:
        broker_name: Nombre del broker
        symbol: Símbolo del activo
        volatility_factor: Factor de volatilidad para ajustar spreads
        spread_tolerance: Tolerancia adicional para spreads
        timezone_offset: Offset de zona horaria en segundos
        
    Returns:
        Contexto del broker
    """
    return {
        "broker_name": broker_name,
        "symbol": symbol,
        "volatility_factor": volatility_factor,
        "spread_tolerance": spread_tolerance,
        "timezone_offset": timezone_offset,
        "max_spread_percent": 5.0 * volatility_factor,
        "allow_out_of_sequence": broker_name.lower() in ["iqoption", "deriv"],  # Algunos brokers permiten esto
        "max_sequence_gap_seconds": 120 if broker_name.lower() == "binance" else 60
    }


def create_market_context(
    market_volatility: float = 1.0,
    market_hours: Optional[Dict[str, Any]] = None,
    trading_session: Optional[str] = None
) -> Dict[str, Any]:
    """
    Crea contexto de condiciones de mercado.
    
    Args:
        market_volatility: Nivel de volatilidad del mercado
        market_hours: Horarios de mercado
        trading_session: Sesión de trading actual
        
    Returns:
        Contexto de mercado
    """
    context = {
        "volatility_factor": market_volatility,
        "trading_session": trading_session
    }
    
    if market_hours:
        context["market_hours"] = market_hours
    
    return context


def create_default_validator(config: Optional[DQVConfig] = None) -> DataQualityValidator:
    """Crea validador con configuración por defecto."""
    return DataQualityValidator(config)


def validate_tick_quick(tick: UnifiedTick) -> bool:
    """Validación rápida de tick (solo reglas críticas)."""
    try:
        # Validaciones básicas críticas
        if tick.price <= 0:
            return False
        
        if tick.volume is not None and tick.volume < 0:
            return False
        
        if tick.bid and tick.ask and tick.ask <= tick.bid:
            return False
        
        # Validación de timestamp básica
        age = (datetime.utcnow() - tick.timestamp).total_seconds()
        if age > 3600:  # 1 hora máximo
            return False
        
        return True
        
    except Exception:
        return False


def analyze_validation_reports(reports: List[ValidationReport]) -> Dict[str, Any]:
    """Analiza múltiples reportes de validación."""
    if not reports:
        return {"error": "No reports provided"}
    
    total_reports = len(reports)
    passed = sum(1 for r in reports if r.result == ValidationResult.PASS)
    warned = sum(1 for r in reports if r.result == ValidationResult.WARN)
    failed = sum(1 for r in reports if r.result == ValidationResult.FAIL)
    
    # Análisis de issues
    all_issues = [issue for report in reports for issue in report.issues]
    issue_counts = defaultdict(int)
    severity_counts = defaultdict(int)
    
    for issue in all_issues:
        issue_counts[issue.rule_name] += 1
        severity_counts[issue.severity.value] += 1
    
    # Métricas de calidad
    quality_scores = [r.quality_score for r in reports]
    avg_quality = statistics.mean(quality_scores)
    
    # Tiempo de procesamiento
    processing_times = [r.processing_time_ms for r in reports]
    avg_processing_time = statistics.mean(processing_times)
    
    return {
        "summary": {
            "total_reports": total_reports,
            "passed": passed,
            "warned": warned,
            "failed": failed,
            "pass_rate_percent": round(passed / total_reports * 100, 2),
            "average_quality_score": round(avg_quality, 3),
            "average_processing_time_ms": round(avg_processing_time, 3)
        },
        "issue_analysis": {
            "total_issues": len(all_issues),
            "by_rule": dict(issue_counts),
            "by_severity": dict(severity_counts)
        },
        "quality_distribution": {
            "min": min(quality_scores),
            "max": max(quality_scores),
            "median": statistics.median(quality_scores),
            "std_dev": statistics.stdev(quality_scores) if len(quality_scores) > 1 else 0
        }
    }