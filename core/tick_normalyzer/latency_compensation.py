"""
Bet-AG\core\tick_normalizer\latency_compensation.py
LC-MOD: ΦΨ∆-CTX - Latency Compensation Engine
"""

import statistics
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal  # noqa: F401
from enum import Enum
from typing import Deque, Dict, Optional, Tuple

from .base import UTC, BrokerType, NormConfig
from .exceptions import LatencyCompensationError


class CompensationMethod(Enum):
    """Métodos de compensación de latencia"""
    FIXED = "fixed"          # Latencia fija configurada
    ADAPTIVE = "adaptive"    # Adaptativa basada en historial
    NETWORK = "network"      # Basada en medición de red
    HYBRID = "hybrid"        # Combinación de métodos


@dataclass
class LatencyProfile:
    """Perfil de latencia por broker"""
    broker: str
    method: CompensationMethod = CompensationMethod.ADAPTIVE
    fixed_latency_ms: float = 50.0
    min_latency_ms: float = 5.0
    max_latency_ms: float = 1000.0
    window_size: int = 100
    confidence_threshold: float = 0.8
    
    # Estadísticas adaptativas
    samples: Deque[float] = field(default_factory=lambda: deque(maxlen=100))
    last_update: Optional[datetime] = None
    avg_latency: float = 50.0
    std_latency: float = 10.0
    confidence: float = 0.0


@dataclass 
class CompensationResult:
    """Resultado de compensación de latencia"""
    original_ts: datetime
    compensated_ts: datetime
    latency_ms: float
    method_used: CompensationMethod
    confidence: float
    broker: str


class LatencyMeasurement:
    """Medidor de latencia en tiempo real"""
    
    def __init__(self):
        self.ping_history: Dict[str, Deque[float]] = defaultdict(lambda: deque(maxlen=50))
        self.request_times: Dict[str, float] = {}
        self._lock = threading.Lock()
    
    def start_measurement(self, broker: str, request_id: str) -> None:
        """Inicia medición de latencia para una request"""
        with self._lock:
            self.request_times[f"{broker}_{request_id}"] = time.time()
    
    def end_measurement(self, broker: str, request_id: str) -> Optional[float]:
        """Finaliza medición y retorna latencia en ms"""
        with self._lock:
            key = f"{broker}_{request_id}"
            if key in self.request_times:
                latency_ms = (time.time() - self.request_times[key]) * 1000
                self.ping_history[broker].append(latency_ms)
                del self.request_times[key]
                return latency_ms
        return None
    
    def get_avg_latency(self, broker: str) -> float:
        """Obtiene latencia promedio para un broker"""
        with self._lock:
            history = self.ping_history[broker]
            return statistics.mean(history) if history else 50.0
    
    def get_latency_stats(self, broker: str) -> Tuple[float, float, int]:
        """Retorna (promedio, std, muestras)"""
        with self._lock:
            history = list(self.ping_history[broker])
            if len(history) < 2:
                return 50.0, 10.0, len(history)
            return statistics.mean(history), statistics.stdev(history), len(history)


class LatencyCompensator:
    """Motor principal de compensación de latencia"""
    
    def __init__(self, config: Optional[NormConfig] = None):
        self.config = config or NormConfig()
        self.profiles: Dict[str, LatencyProfile] = {}
        self.measurement = LatencyMeasurement()
        self._lock = threading.Lock()
        
        # Inicializar perfiles por defecto
        self._init_default_profiles()
    
    def _init_default_profiles(self) -> None:
        """Inicializa perfiles de latencia por defecto para cada broker"""
        default_latencies = {
            BrokerType.BINANCE.value: 25.0,
            BrokerType.DERIV.value: 100.0, 
            BrokerType.IQOPTION.value: 150.0,
            BrokerType.MT5.value: 80.0
        }
        
        for broker, latency in default_latencies.items():
            self.profiles[broker] = LatencyProfile(
                broker=broker,
                fixed_latency_ms=latency,
                method=CompensationMethod.ADAPTIVE if self.config.latency_compensation else CompensationMethod.FIXED
            )
    
    def register_broker_profile(self, broker: str, profile: LatencyProfile) -> None:
        """Registra o actualiza perfil de latencia para un broker"""
        with self._lock:
            self.profiles[broker] = profile
    
    def compensate_tick(self, tick: UTC) -> CompensationResult:
        """Compensa la latencia de un tick"""
        if not self.config.latency_compensation:
            return CompensationResult(
                original_ts=tick.timestamp,
                compensated_ts=tick.timestamp,
                latency_ms=0.0,
                method_used=CompensationMethod.FIXED,
                confidence=1.0,
                broker=tick.broker
            )
        
        profile = self.profiles.get(tick.broker)
        if not profile:
            raise LatencyCompensationError(
                broker=tick.broker,
                latency_ms=0,
                compensation_attempts=1,
                context={"error": "No profile found for broker"}
            )
        
        # Actualizar estadísticas del perfil
        self._update_profile_stats(profile)
        
        # Calcular latencia según método
        latency_ms, confidence, method = self._calculate_latency(profile)
        
        # Aplicar compensación
        compensated_ts = tick.timestamp - timedelta(milliseconds=latency_ms)
        
        # Validar compensación
        if not self._validate_compensation(tick.timestamp, compensated_ts, latency_ms):
            raise LatencyCompensationError(
                broker=tick.broker,
                latency_ms=latency_ms,
                compensation_attempts=1,
                context={"error": "Invalid compensation result", "original": tick.timestamp, "compensated": compensated_ts}
            )
        
        return CompensationResult(
            original_ts=tick.timestamp,
            compensated_ts=compensated_ts,
            latency_ms=latency_ms,
            method_used=method,
            confidence=confidence,
            broker=tick.broker
        )
    
    def _update_profile_stats(self, profile: LatencyProfile) -> None:
        """Actualiza estadísticas del perfil con mediciones recientes"""
        avg_latency, std_latency, sample_count = self.measurement.get_latency_stats(profile.broker)
        
        if sample_count >= 5:  # Mínimo de muestras para confiabilidad
            profile.avg_latency = avg_latency
            profile.std_latency = std_latency
            profile.confidence = min(1.0, sample_count / profile.window_size)
            profile.last_update = datetime.utcnow()
    
    def _calculate_latency(self, profile: LatencyProfile) -> Tuple[float, float, CompensationMethod]:
        """Calcula latencia según método configurado"""
        
        if profile.method == CompensationMethod.FIXED:
            return profile.fixed_latency_ms, 1.0, CompensationMethod.FIXED
        
        elif profile.method == CompensationMethod.ADAPTIVE:
            if profile.confidence >= profile.confidence_threshold:
                latency = max(profile.min_latency_ms, 
                            min(profile.max_latency_ms, profile.avg_latency))
                return latency, profile.confidence, CompensationMethod.ADAPTIVE
            else:
                return profile.fixed_latency_ms, 0.5, CompensationMethod.FIXED
        
        elif profile.method == CompensationMethod.NETWORK:
            recent_latency = self.measurement.get_avg_latency(profile.broker)
            latency = max(profile.min_latency_ms, min(profile.max_latency_ms, recent_latency))
            confidence = min(1.0, len(self.measurement.ping_history[profile.broker]) / 20)
            return latency, confidence, CompensationMethod.NETWORK
        
        elif profile.method == CompensationMethod.HYBRID:
            # Combina adaptativo y network con pesos
            adaptive_weight = profile.confidence
            network_weight = 1.0 - adaptive_weight
            
            adaptive_latency = profile.avg_latency
            network_latency = self.measurement.get_avg_latency(profile.broker)
            
            combined_latency = (adaptive_latency * adaptive_weight + 
                              network_latency * network_weight)
            
            latency = max(profile.min_latency_ms, min(profile.max_latency_ms, combined_latency))
            return latency, (adaptive_weight + network_weight) / 2, CompensationMethod.HYBRID
        
        return profile.fixed_latency_ms, 0.5, CompensationMethod.FIXED
    
    def _validate_compensation(self, original_ts: datetime, compensated_ts: datetime, latency_ms: float) -> bool:
        """Valida que la compensación sea razonable"""
        # No debe compensar hacia el futuro
        if compensated_ts > original_ts:
            return False
        
        # Diferencia no debe exceder límites configurados
        diff_ms = (original_ts - compensated_ts).total_seconds() * 1000
        if diff_ms > self.config.max_latency_ms or diff_ms < 0:
            return False
        
        # Latencia debe estar en rango razonable
        if latency_ms < 0 or latency_ms > self.config.max_latency_ms:
            return False
        
        return True
    
    def update_tick_latency(self, tick: UTC) -> UTC:
        """Actualiza timestamp del tick con compensación aplicada"""
        if not self.config.latency_compensation:
            return tick
        
        try:
            result = self.compensate_tick(tick)
            
            # Crear nuevo tick con timestamp compensado
            compensated_tick = UTC(
                timestamp=result.compensated_ts,
                symbol=tick.symbol,
                broker=tick.broker,
                price=tick.price,
                volume=tick.volume,
                bid=tick.bid,
                ask=tick.ask,
                spread=tick.spread,
                quality_score=tick.quality_score,
                latency_ms=result.latency_ms,
                raw_data=tick.raw_data,
                tick_type=tick.tick_type,
                sequence_id=tick.sequence_id
            )
            
            return compensated_tick
            
        except LatencyCompensationError:
            # En caso de error, retornar tick original
            return tick
    
    def get_broker_stats(self, broker: str) -> Dict:
        """Obtiene estadísticas de latencia para un broker"""
        profile = self.profiles.get(broker)
        if not profile:
            return {}
        
        avg_latency, std_latency, sample_count = self.measurement.get_latency_stats(broker)
        
        return {
            "broker": broker,
            "method": profile.method.value,
            "fixed_latency_ms": profile.fixed_latency_ms,
            "adaptive_latency_ms": profile.avg_latency,
            "network_latency_ms": avg_latency,
            "std_latency_ms": std_latency,
            "confidence": profile.confidence,
            "sample_count": sample_count,
            "last_update": profile.last_update.isoformat() if profile.last_update else None
        }
    
    def get_all_stats(self) -> Dict[str, Dict]:
        """Obtiene estadísticas de todos los brokers"""
        return {broker: self.get_broker_stats(broker) for broker in self.profiles.keys()}
    
    def reset_broker_stats(self, broker: str) -> None:
        """Resetea estadísticas de un broker específico"""
        with self._lock:
            if broker in self.profiles:
                profile = self.profiles[broker]
                profile.samples.clear()
                profile.confidence = 0.0
                profile.last_update = None
            
            if broker in self.measurement.ping_history:
                self.measurement.ping_history[broker].clear()


# Utilidades para testing y configuración
def create_test_compensator(enable_compensation: bool = True) -> LatencyCompensator:
    """Crea compensador para testing"""
    config = NormConfig()
    config.latency_compensation = enable_compensation
    config.max_latency_ms = 500
    return LatencyCompensator(config)


def simulate_network_latency(compensator: LatencyCompensator, broker: str, latency_ms: float) -> None:
    """Simula latencia de red para testing"""
    compensator.measurement.ping_history[broker].append(latency_ms)