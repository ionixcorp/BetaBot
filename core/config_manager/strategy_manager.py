"""
Gestor de Configuración de Estrategias

Este módulo maneja la carga y gestión de configuraciones para todas
las estrategias de trading disponibles en el sistema.
"""

import logging
import os  # noqa: F401
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


@dataclass
class StrategyConfig:
    """Configuración de una estrategia específica"""
    name: str
    type: str
    category: str
    enabled: bool
    strategy_params: Dict[str, Any]
    analysis: Dict[str, Any]
    metrics_thresholds: Dict[str, Any]
    weights: Dict[str, Any]
    feature_flags: Dict[str, Any]
    candle_patterns: Dict[str, Any]
    multi_timeframes: Dict[str, Any]
    zigzag_multifractal: Dict[str, Any]
    volume_strength: Dict[str, Any]
    volume_profile: Dict[str, Any]
    signal_composer: Dict[str, Any]
    scoring_engine: Dict[str, Any]
    use_advanced_system: Dict[str, Any]
    raw_config: Dict[str, Any] = field(default_factory=dict)


class StrategyManager:
    """
    Gestor de configuración de estrategias que carga y valida las configuraciones
    de todas las estrategias de trading disponibles en el sistema.
    """
    
    def __init__(self, strategies_path: Path):
        """
        Inicializa el gestor de estrategias.
        
        Args:
            strategies_path: Ruta al directorio de configuración de estrategias
        """
        self.logger = logging.getLogger(__name__)
        self.strategies_path = strategies_path
        self.strategies: Dict[str, Dict[str, StrategyConfig]] = {}  # {category: {strategy_name: config}}
        self._loaded = False
        
        if not self.strategies_path.exists():
            raise FileNotFoundError(f"Directorio de estrategias no encontrado: {strategies_path}")
    
    def load_all_strategies(self) -> bool:
        """
        Carga todas las configuraciones de estrategias disponibles.
        
        Returns:
            bool: True si la carga fue exitosa
        """
        try:
            self.logger.info(f"Cargando estrategias desde: {self.strategies_path}")
            
            # Buscar todos los subdirectorios (categorías de estrategias)
            strategy_categories = [d for d in self.strategies_path.iterdir() if d.is_dir()]
            
            if not strategy_categories:
                self.logger.warning("No se encontraron categorías de estrategias")
                return True
            
            for category_path in strategy_categories:
                category_name = category_path.name
                self.logger.info(f"Cargando categoría de estrategias: {category_name}")
                
                # Buscar archivos YAML en la categoría
                yaml_files = list(category_path.glob("*.yaml"))
                
                if not yaml_files:
                    self.logger.warning(f"No se encontraron archivos de configuración en categoría: {category_name}")
                    continue
                
                self.strategies[category_name] = {}
                
                for yaml_file in yaml_files:
                    strategy_name = yaml_file.stem  # Nombre del archivo sin extensión
                    self.logger.info(f"Cargando estrategia: {category_name}/{strategy_name}")
                    
                    try:
                        with open(yaml_file, 'r', encoding='utf-8') as f:
                            config_data = yaml.safe_load(f)
                        
                        if config_data and 'strategy' in config_data:
                            strategy_config = self._parse_strategy_config(strategy_name, category_name, config_data)
                            self.strategies[category_name][strategy_name] = strategy_config
                            self.logger.info(f"Estrategia {category_name}/{strategy_name} cargada exitosamente")
                        else:
                            self.logger.warning(f"Archivo {yaml_file} no contiene configuración válida de estrategia")
                            
                    except Exception:
                        self.logger.exception(f"Error al cargar estrategia {category_name}/{strategy_name}")
                        continue
            
            self._loaded = True
            total_strategies = sum(len(strategies) for strategies in self.strategies.values())
            self.logger.info(f"Total de estrategias cargadas: {total_strategies} en {len(self.strategies)} categorías")
            return True
            
        except Exception:
            self.logger.exception("Error al cargar estrategias")
            return False
    
    def _parse_strategy_config(self, strategy_name: str, category: str, config_data: Dict[str, Any]) -> StrategyConfig:
        """
        Parsea la configuración de una estrategia desde el diccionario de datos.
        
        Args:
            strategy_name: Nombre de la estrategia
            category: Categoría de la estrategia
            config_data: Datos de configuración del archivo YAML
            
        Returns:
            StrategyConfig: Configuración parseada de la estrategia
        """
        strategy_info = config_data.get('strategy', '')
        strategy_params = config_data.get('strategy_params', {})
        
        return StrategyConfig(
            name=strategy_name,
            type=strategy_info,
            category=category,
            enabled=strategy_params.get('enabled', True),
            strategy_params=strategy_params,
            analysis=strategy_params.get('analysis', {}),
            metrics_thresholds=strategy_params.get('metrics_thresholds', {}),
            weights=strategy_params.get('weights', {}),
            feature_flags=strategy_params.get('feature_flags', {}),
            candle_patterns=strategy_params.get('candle_patterns', {}),
            multi_timeframes=strategy_params.get('multi_timeframes', {}),
            zigzag_multifractal=strategy_params.get('zigzag_multifractal', {}),
            volume_strength=strategy_params.get('volume_strength', {}),
            volume_profile=strategy_params.get('volume_profile', {}),
            signal_composer=strategy_params.get('signal_composer', {}),
            scoring_engine=strategy_params.get('scoring_engine', {}),
            use_advanced_system=strategy_params.get('use_advanced_system', {}),
            raw_config=config_data
        )
    
    def get_strategy_config(self, strategy_type: str, strategy_name: str) -> Optional[StrategyConfig]:
        """
        Obtiene la configuración de una estrategia específica.
        
        Args:
            strategy_type: Tipo/categoría de la estrategia
            strategy_name: Nombre de la estrategia
            
        Returns:
            StrategyConfig: Configuración de la estrategia o None si no existe
        """
        return self.strategies.get(strategy_type, {}).get(strategy_name)
    
    def get_all_strategies(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """
        Obtiene todas las configuraciones de estrategias como diccionarios.
        
        Returns:
            Dict: Diccionario con todas las configuraciones de estrategias
        """
        result = {}
        for category, strategies in self.strategies.items():
            result[category] = {}
            for strategy_name, strategy_config in strategies.items():
                result[category][strategy_name] = {
                    'name': strategy_config.name,
                    'type': strategy_config.type,
                    'category': strategy_config.category,
                    'enabled': strategy_config.enabled,
                    'strategy_params': strategy_config.strategy_params,
                    'analysis': strategy_config.analysis,
                    'metrics_thresholds': strategy_config.metrics_thresholds,
                    'weights': strategy_config.weights,
                    'feature_flags': strategy_config.feature_flags,
                    'candle_patterns': strategy_config.candle_patterns,
                    'multi_timeframes': strategy_config.multi_timeframes,
                    'zigzag_multifractal': strategy_config.zigzag_multifractal,
                    'volume_strength': strategy_config.volume_strength,
                    'volume_profile': strategy_config.volume_profile,
                    'signal_composer': strategy_config.signal_composer,
                    'scoring_engine': strategy_config.scoring_engine,
                    'use_advanced_system': strategy_config.use_advanced_system
                }
        return result
    
    def get_strategies_by_category(self, category: str) -> Dict[str, StrategyConfig]:
        """
        Obtiene todas las estrategias de una categoría específica.
        
        Args:
            category: Categoría de estrategias a obtener
            
        Returns:
            Dict: Diccionario con las estrategias de la categoría
        """
        return self.strategies.get(category, {})
    
    def get_enabled_strategies(self, category: Optional[str] = None) -> Dict[str, Dict[str, StrategyConfig]]:
        """
        Obtiene solo las estrategias habilitadas.
        
        Args:
            category: Categoría específica (opcional)
            
        Returns:
            Dict: Diccionario con las estrategias habilitadas
        """
        if category:
            return {
                category: {
                    name: config 
                    for name, config in self.strategies.get(category, {}).items() 
                    if config.enabled
                }
            }
        else:
            return {
                cat: {
                    name: config 
                    for name, config in strategies.items() 
                    if config.enabled
                }
                for cat, strategies in self.strategies.items()
            }
    
    def get_strategies_by_type(self, strategy_type: str) -> Dict[str, StrategyConfig]:
        """
        Obtiene estrategias filtradas por tipo.
        
        Args:
            strategy_type: Tipo de estrategia a filtrar
            
        Returns:
            Dict: Diccionario con las estrategias del tipo especificado
        """
        result = {}
        for category, strategies in self.strategies.items():
            for strategy_name, strategy_config in strategies.items():
                if strategy_config.type.lower() == strategy_type.lower():
                    result[f"{category}/{strategy_name}"] = strategy_config
        return result
    
    def get_strategy_parameters(self, strategy_type: str, strategy_name: str) -> Dict[str, Any]:
        """
        Obtiene los parámetros de configuración de una estrategia específica.
        
        Args:
            strategy_type: Tipo/categoría de la estrategia
            strategy_name: Nombre de la estrategia
            
        Returns:
            Dict: Parámetros de configuración de la estrategia
        """
        strategy_config = self.get_strategy_config(strategy_type, strategy_name)
        if strategy_config:
            return strategy_config.strategy_params
        return {}
    
    def get_strategy_analysis_config(self, strategy_type: str, strategy_name: str) -> Dict[str, Any]:
        """
        Obtiene la configuración de análisis de una estrategia específica.
        
        Args:
            strategy_type: Tipo/categoría de la estrategia
            strategy_name: Nombre de la estrategia
            
        Returns:
            Dict: Configuración de análisis de la estrategia
        """
        strategy_config = self.get_strategy_config(strategy_type, strategy_name)
        if strategy_config:
            return strategy_config.analysis
        return {}
    
    def get_strategy_weights(self, strategy_type: str, strategy_name: str) -> Dict[str, Any]:
        """
        Obtiene los pesos de configuración de una estrategia específica.
        
        Args:
            strategy_type: Tipo/categoría de la estrategia
            strategy_name: Nombre de la estrategia
            
        Returns:
            Dict: Pesos de configuración de la estrategia
        """
        strategy_config = self.get_strategy_config(strategy_type, strategy_name)
        if strategy_config:
            return strategy_config.weights
        return {}
    
    def get_strategy_feature_flags(self, strategy_type: str, strategy_name: str) -> Dict[str, Any]:
        """
        Obtiene los flags de características de una estrategia específica.
        
        Args:
            strategy_type: Tipo/categoría de la estrategia
            strategy_name: Nombre de la estrategia
            
        Returns:
            Dict: Flags de características de la estrategia
        """
        strategy_config = self.get_strategy_config(strategy_type, strategy_name)
        if strategy_config:
            return strategy_config.feature_flags
        return {}
    
    def validate_all(self) -> bool:
        """
        Valida todas las configuraciones de estrategias cargadas.
        
        Returns:
            bool: True si todas las validaciones pasan
        """
        try:
            for category, strategies in self.strategies.items():
                for strategy_name, strategy_config in strategies.items():
                    if not self._validate_strategy_config(strategy_config):
                        self.logger.error(f"Validación falló para estrategia: {category}/{strategy_name}")
                        return False
            
            self.logger.info("Todas las configuraciones de estrategias validadas exitosamente")
            return True
            
        except Exception:
            self.logger.exception("Error en validación de estrategias")
            return False
    
    def _validate_strategy_config(self, strategy_config: StrategyConfig) -> bool:
        """
        Valida la configuración de una estrategia específica.
        
        Args:
            strategy_config: Configuración de la estrategia a validar
            
        Returns:
            bool: True si la configuración es válida
        """
        try:
            # Validar campos requeridos
            if not strategy_config.name:
                self.logger.error("Nombre de estrategia requerido")
                return False
            
            if not strategy_config.type:
                self.logger.error(f"Tipo de estrategia requerido para {strategy_config.name}")
                return False
            
            if not strategy_config.category:
                self.logger.error(f"Categoría de estrategia requerida para {strategy_config.name}")
                return False
            
            # Validar que tenga parámetros de estrategia
            if not strategy_config.strategy_params:
                self.logger.warning(f"No hay parámetros de estrategia configurados para {strategy_config.name}")
            
            return True
            
        except Exception:
            self.logger.exception("Error al validar configuración de estrategia")
            return False
    
    def is_loaded(self) -> bool:
        """Verifica si las configuraciones de estrategias han sido cargadas"""
        return self._loaded
    
    def get_strategy_summary(self) -> Dict[str, Any]:
        """Obtiene un resumen de todas las estrategias configuradas"""
        total_strategies = sum(len(strategies) for strategies in self.strategies.values())
        enabled_strategies = sum(
            len([config for config in strategies.values() if config.enabled])
            for strategies in self.strategies.values()
        )
        
        return {
            "total_strategies": total_strategies,
            "enabled_strategies": enabled_strategies,
            "categories": list(self.strategies.keys()),
            "strategy_types": list(set(
                config.type 
                for strategies in self.strategies.values() 
                for config in strategies.values()
            )),
            "loaded": self._loaded
        }
    
    def reload_strategy(self, strategy_type: str, strategy_name: str) -> bool:
        """
        Recarga la configuración de una estrategia específica.
        
        Args:
            strategy_type: Tipo/categoría de la estrategia
            strategy_name: Nombre de la estrategia a recargar
            
        Returns:
            bool: True si la recarga fue exitosa
        """
        try:
            yaml_file = self.strategies_path / strategy_type / f"{strategy_name}.yaml"
            
            if not yaml_file.exists():
                self.logger.error(f"Archivo de configuración no encontrado: {yaml_file}")
                return False
            
            with open(yaml_file, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            if config_data and 'strategy' in config_data:
                strategy_config = self._parse_strategy_config(strategy_name, strategy_type, config_data)
                self.strategies[strategy_type][strategy_name] = strategy_config
                self.logger.info(f"Estrategia {strategy_type}/{strategy_name} recargada exitosamente")
                return True
            else:
                self.logger.error(f"Archivo {yaml_file} no contiene configuración válida")
                return False
                
        except Exception:
            self.logger.exception(f"Error al recargar estrategia {strategy_type}/{strategy_name}")
            return False
    
    def get_strategy_categories(self) -> List[str]:
        """Obtiene la lista de todas las categorías de estrategias disponibles"""
        return list(self.strategies.keys())
    
    def get_strategies_in_category(self, category: str) -> List[str]:
        """
        Obtiene la lista de nombres de estrategias en una categoría específica.
        
        Args:
            category: Categoría de estrategias
            
        Returns:
            List: Lista de nombres de estrategias en la categoría
        """
        return list(self.strategies.get(category, {}).keys())
