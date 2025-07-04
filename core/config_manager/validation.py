"""
Módulo de Validación de Configuraciones

Este módulo proporciona funciones para validar todas las configuraciones
del sistema de trading automatizado.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional  # noqa: F401


@dataclass
class ValidationResult:
    """Resultado de una validación"""
    is_valid: bool
    errors: List[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


class ConfigValidator:
    """
    Validador de configuraciones que proporciona métodos para validar
    todas las configuraciones del sistema de trading.
    """
    
    def __init__(self):
        """Inicializa el validador de configuraciones"""
        self.logger = logging.getLogger(__name__)
    
    def validate_global_config(self, system_config) -> bool:
        """
        Valida la configuración global del sistema.
        
        Args:
            system_config: Configuración global del sistema
            
        Returns:
            bool: True si la configuración es válida
        """
        try:
            # Validar que la configuración global tenga la estructura correcta
            if not hasattr(system_config, 'metrics'):
                self.logger.error("Configuración global debe tener sección 'metrics'")
                return False
            
            if not hasattr(system_config, 'live_global_candle'):
                self.logger.error("Configuración global debe tener sección 'live_global_candle'")
                return False
            
            if not hasattr(system_config, 'system'):
                self.logger.error("Configuración global debe tener sección 'system'")
                return False
            
            # Validar configuración de métricas
            if system_config.metrics:
                if not self._validate_metrics_config(system_config.metrics):
                    return False
            
            return True
            
        except Exception:
            self.logger.exception("Error al validar configuración global")
            return False
    
    def _validate_metrics_config(self, metrics_config: Dict[str, Any]) -> bool:
        """
        Valida la configuración de métricas.
        
        Args:
            metrics_config: Configuración de métricas
            
        Returns:
            bool: True si la configuración es válida
        """
        try:
            if not isinstance(metrics_config, dict):
                self.logger.error("Configuración de métricas debe ser un diccionario")
                return False
            
            # Validar que tenga la estructura esperada
            expected_modules = [
                'lead_lag', 'liquidity', 'microstructure', 'momentum',
                'price_stats', 'temporal_patterns', 'volume_intrabar',
                'volume_profile', 'volume_stats'
            ]
            
            metrics = metrics_config.get('metrics', {})
            for module in expected_modules:
                if module not in metrics:
                    self.logger.warning(f"Módulo de métricas '{module}' no encontrado")
            
            return True
            
        except Exception:
            self.logger.exception("Error al validar configuración de métricas")
            return False
    
    def validate_broker_config(self, broker_config: Dict[str, Any]) -> ValidationResult:
        """
        Valida la configuración de un broker.
        
        Args:
            broker_config: Configuración del broker
            
        Returns:
            ValidationResult: Resultado de la validación
        """
        result = ValidationResult(is_valid=True)
        
        try:
            # Validar sección broker
            broker_info = broker_config.get('broker', {})
            if not broker_info:
                result.errors.append("Sección 'broker' requerida")
                result.is_valid = False
            
            # Validar campos requeridos del broker
            required_fields = ['name', 'type', 'enabled']
            for field in required_fields:
                if field not in broker_info:
                    result.errors.append(f"Campo '{field}' requerido en sección broker")
                    result.is_valid = False
            
            # Validar sección connection
            connection = broker_config.get('connection', {})
            if not connection:
                result.errors.append("Sección 'connection' requerida")
                result.is_valid = False
            else:
                if not self._validate_connection_config(connection, result):
                    result.is_valid = False
            
            # Validar sección auth
            auth = broker_config.get('auth', {})
            if not auth:
                result.errors.append("Sección 'auth' requerida")
                result.is_valid = False
            else:
                if not self._validate_auth_config(auth, result):
                    result.is_valid = False
            
            # Validar sección tick_normalizer
            tick_normalizer = broker_config.get('tick_normalizer', {})
            if tick_normalizer:
                if not self._validate_tick_normalizer_config(tick_normalizer, result):
                    result.is_valid = False
            
            # Validar sección symbols
            symbols = broker_config.get('symbols', {})
            if not symbols:
                result.warnings.append("No hay símbolos configurados")
            
            return result
            
        except Exception as e:
            result.errors.append(f"Error al validar configuración de broker: {e}")
            result.is_valid = False
            return result
    
    def _validate_connection_config(self, connection: Dict[str, Any], result: ValidationResult) -> bool:
        """Valida la configuración de conexión"""
        try:
            # Validar que tenga al menos una configuración de conexión
            has_rest = 'rest_api' in connection
            has_websocket = 'websocket' in connection
            has_api = 'api' in connection
            
            if not (has_rest or has_websocket or has_api):
                result.errors.append("Configuración de conexión debe tener al menos una de: rest_api, websocket, api")
                return False
            
            # Validar rate_limits si existe
            rate_limits = connection.get('rate_limits', {})
            if rate_limits:
                required_rate_fields = ['requests_per_second']
                for field in required_rate_fields:
                    if field not in rate_limits:
                        result.errors.append(f"Campo '{field}' requerido en rate_limits")
                        return False
            
            return True
            
        except Exception as e:
            result.errors.append(f"Error al validar configuración de conexión: {e}")
            return False
    
    def _validate_auth_config(self, auth: Dict[str, Any], result: ValidationResult) -> bool:
        """Valida la configuración de autenticación"""
        try:
            # Validar que tenga al menos un método de autenticación
            has_api_key = 'api_key' in auth
            has_username = 'username' in auth
            
            if not (has_api_key or has_username):
                result.errors.append("Configuración de autenticación debe tener api_key o username")
                return False
            
            return True
            
        except Exception as e:
            result.errors.append(f"Error al validar configuración de autenticación: {e}")
            return False
    
    def _validate_tick_normalizer_config(self, tick_normalizer: Dict[str, Any], result: ValidationResult) -> bool:
        """Valida la configuración del normalizador de ticks"""
        try:
            # Validar data_quality
            data_quality = tick_normalizer.get('data_quality', {})
            if data_quality:
                required_fields = ['min_quality_score', 'max_spread_percentage']
                for field in required_fields:
                    if field not in data_quality:
                        result.errors.append(f"Campo '{field}' requerido en data_quality")
                        return False
                
                # Validar valores numéricos
                if 'min_quality_score' in data_quality:
                    score = data_quality['min_quality_score']
                    if not isinstance(score, (int, float)) or score < 0 or score > 1:
                        result.errors.append("min_quality_score debe ser un número entre 0 y 1")
                        return False
                
                if 'max_spread_percentage' in data_quality:
                    spread = data_quality['max_spread_percentage']
                    if not isinstance(spread, (int, float)) or spread <= 0:
                        result.errors.append("max_spread_percentage debe ser un número positivo")
                        return False
            
            # Validar latency_compensation
            latency_compensation = tick_normalizer.get('latency_compensation', {})
            if latency_compensation:
                if 'enabled' not in latency_compensation:
                    result.errors.append("Campo 'enabled' requerido en latency_compensation")
                    return False
                
                # Validar campos adicionales de latency_compensation
                if 'method' in latency_compensation:
                    method = latency_compensation['method']
                    if method not in ['adaptive', 'fixed', 'dynamic']:
                        result.warnings.append(f"Método de compensación de latencia '{method}' no estándar")
                
                if 'fixed_latency_ms' in latency_compensation:
                    latency = latency_compensation['fixed_latency_ms']
                    if not isinstance(latency, (int, float)) or latency < 0:
                        result.errors.append("fixed_latency_ms debe ser un número positivo")
                        return False
            
            # Validar validation
            validation = tick_normalizer.get('validation', {})
            if validation:
                if not isinstance(validation, dict):
                    result.errors.append("Sección 'validation' debe ser un diccionario")
                    return False
                
                # Validar campos de validación
                validation_fields = ['price_positive', 'volume_non_negative', 'spread_validation', 
                                   'timestamp_validation', 'sequence_validation', 'anomaly_detection']
                for field in validation_fields:
                    if field in validation and not isinstance(validation[field], bool):
                        result.errors.append(f"Campo '{field}' en validation debe ser un booleano")
                        return False
            
            # Validar anomaly_detection
            anomaly_detection = tick_normalizer.get('anomaly_detection', {})
            if anomaly_detection:
                if 'enabled' not in anomaly_detection:
                    result.errors.append("Campo 'enabled' requerido en anomaly_detection")
                    return False
                
                # Validar parámetros de anomalía
                anomaly_params = ['price_sigma_threshold', 'volume_sigma_threshold', 'window_size', 'min_samples']
                for param in anomaly_params:
                    if param in anomaly_detection:
                        value = anomaly_detection[param]
                        if not isinstance(value, (int, float)) or value <= 0:
                            result.errors.append(f"Parámetro '{param}' en anomaly_detection debe ser un número positivo")
                            return False
            
            return True
            
        except Exception as e:
            result.errors.append(f"Error al validar configuración de tick_normalizer: {e}")
            return False
    
    def validate_asset_config(self, asset_config: Dict[str, Any]) -> ValidationResult:
        """
        Valida la configuración de un asset.
        
        Args:
            asset_config: Configuración del asset
            
        Returns:
            ValidationResult: Resultado de la validación
        """
        result = ValidationResult(is_valid=True)
        
        try:
            # Validar campos requeridos
            required_fields = ['type', 'enabled']
            for field in required_fields:
                if field not in asset_config:
                    result.errors.append(f"Campo '{field}' requerido en configuración de asset")
                    result.is_valid = False
            
            # Validar parámetros si existen
            parameters = asset_config.get('parameters', {})
            if parameters and not isinstance(parameters, dict):
                result.errors.append("Sección 'parameters' debe ser un diccionario")
                result.is_valid = False
            
            return result
            
        except Exception as e:
            result.errors.append(f"Error al validar configuración de asset: {e}")
            result.is_valid = False
            return result
    
    def validate_strategy_config(self, strategy_config: Dict[str, Any]) -> ValidationResult:
        """
        Valida la configuración de una estrategia.
        
        Args:
            strategy_config: Configuración de la estrategia
            
        Returns:
            ValidationResult: Resultado de la validación
        """
        result = ValidationResult(is_valid=True)
        
        try:
            # Validar sección strategy
            strategy_name = strategy_config.get('strategy', '')
            if not strategy_name:
                result.errors.append("Campo 'strategy' requerido")
                result.is_valid = False
            
            # Validar strategy_params
            strategy_params = strategy_config.get('strategy_params', {})
            if not strategy_params:
                result.warnings.append("No hay parámetros de estrategia configurados")
            else:
                if not self._validate_strategy_params(strategy_params, result):
                    result.is_valid = False
            
            return result
            
        except Exception as e:
            result.errors.append(f"Error al validar configuración de estrategia: {e}")
            result.is_valid = False
            return result
    
    def _validate_strategy_params(self, strategy_params: Dict[str, Any], result: ValidationResult) -> bool:
        """Valida los parámetros de estrategia"""
        try:
            # Validar que enabled esté presente si existe
            if 'enabled' in strategy_params:
                if not isinstance(strategy_params['enabled'], bool):
                    result.errors.append("Campo 'enabled' debe ser un booleano")
                    return False
            
            # Validar secciones opcionales
            optional_sections = [
                'analysis', 'metrics_thresholds', 'weights', 'feature_flags',
                'candle_patterns', 'multi_timeframes', 'zigzag_multifractal',
                'volume_strength', 'volume_profile', 'signal_composer',
                'scoring_engine', 'use_advanced_system'
            ]
            
            for section in optional_sections:
                if section in strategy_params:
                    section_config = strategy_params[section]
                    if not isinstance(section_config, dict):
                        result.errors.append(f"Sección '{section}' debe ser un diccionario")
                        return False
            
            return True
            
        except Exception as e:
            result.errors.append(f"Error al validar parámetros de estrategia: {e}")
            return False
    
    def validate_risk_config(self, risk_config: Dict[str, Any]) -> ValidationResult:
        """
        Valida la configuración de gestión de riesgo.
        
        Args:
            risk_config: Configuración de gestión de riesgo
            
        Returns:
            ValidationResult: Resultado de la validación
        """
        result = ValidationResult(is_valid=True)
        
        try:
            # Validar campos requeridos
            required_fields = ['enabled']
            for field in required_fields:
                if field not in risk_config:
                    result.errors.append(f"Campo '{field}' requerido en configuración de riesgo")
                    result.is_valid = False
            
            # Validar secciones opcionales
            optional_sections = ['parameters', 'limits', 'thresholds']
            for section in optional_sections:
                if section in risk_config:
                    section_config = risk_config[section]
                    if not isinstance(section_config, dict):
                        result.errors.append(f"Sección '{section}' debe ser un diccionario")
                        result.is_valid = False
            
            return result
            
        except Exception as e:
            result.errors.append(f"Error al validar configuración de riesgo: {e}")
            result.is_valid = False
            return result
    
    def validate_complete_config(self, config_manager) -> ValidationResult:
        """
        Valida toda la configuración del sistema.
        
        Args:
            config_manager: Instancia del gestor de configuración
            
        Returns:
            ValidationResult: Resultado de la validación completa
        """
        result = ValidationResult(is_valid=True)
        
        try:
            # Validar configuración global
            if not self.validate_global_config(config_manager.system_config):
                result.errors.append("Validación de configuración global falló")
                result.is_valid = False
            
            # Validar brokers
            for broker_name, broker_config in config_manager.get_all_brokers().items():
                broker_result = self.validate_broker_config(broker_config)
                if not broker_result.is_valid:
                    result.errors.extend([f"Broker {broker_name}: {error}" for error in broker_result.errors])
                    result.is_valid = False
                result.warnings.extend([f"Broker {broker_name}: {warning}" for warning in broker_result.warnings])
            
            # Validar assets
            for category, assets in config_manager.get_all_assets().items():
                for asset_name, asset_config in assets.items():
                    asset_result = self.validate_asset_config(asset_config)
                    if not asset_result.is_valid:
                        result.errors.extend([f"Asset {category}/{asset_name}: {error}" for error in asset_result.errors])
                        result.is_valid = False
                    result.warnings.extend([f"Asset {category}/{asset_name}: {warning}" for warning in asset_result.warnings])
            
            # Validar estrategias
            for category, strategies in config_manager.get_all_strategies().items():
                for strategy_name, strategy_config in strategies.items():
                    strategy_result = self.validate_strategy_config(strategy_config)
                    if not strategy_result.is_valid:
                        result.errors.extend([f"Estrategia {category}/{strategy_name}: {error}" for error in strategy_result.errors])
                        result.is_valid = False
                    result.warnings.extend([f"Estrategia {category}/{strategy_name}: {warning}" for warning in strategy_result.warnings])
            
            # Validar gestión de riesgo
            for risk_type, risk_config in config_manager.get_all_risk_configs().items():
                risk_result = self.validate_risk_config(risk_config)
                if not risk_result.is_valid:
                    result.errors.extend([f"Riesgo {risk_type}: {error}" for error in risk_result.errors])
                    result.is_valid = False
                result.warnings.extend([f"Riesgo {risk_type}: {warning}" for warning in risk_result.warnings])
            
            return result
            
        except Exception as e:
            result.errors.append(f"Error al validar configuración completa: {e}")
            result.is_valid = False
            return result
    
    def print_validation_report(self, result: ValidationResult):
        """
        Imprime un reporte de validación.
        
        Args:
            result: Resultado de la validación
        """
        print("=" * 60)
        print("REPORTE DE VALIDACIÓN DE CONFIGURACIÓN")
        print("=" * 60)
        
        if result.is_valid:
            print("✅ CONFIGURACIÓN VÁLIDA")
        else:
            print("❌ CONFIGURACIÓN INVÁLIDA")
        
        if result.errors:
            print("\n🚨 ERRORES:")
            for error in result.errors:
                print(f"  • {error}")
        
        if result.warnings:
            print("\n⚠️  ADVERTENCIAS:")
            for warning in result.warnings:
                print(f"  • {warning}")
        
        print("=" * 60)
