"""
Gestor de Configuración de Brokers

Este módulo maneja la carga y gestión de configuraciones para todos
los brokers disponibles en el sistema de trading.
"""

import logging
import os  # noqa: F401
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional  # noqa: F401

import yaml


@dataclass
class BrokerConfig:
    """Configuración de un broker específico"""
    name: str
    type: str
    enabled: bool
    connection: Dict[str, Any]
    auth: Dict[str, Any]
    tick_normalizer: Dict[str, Any]
    symbols: Dict[str, Any]
    performance: Dict[str, Any]
    logging: Dict[str, Any]
    metrics: Dict[str, Any]
    raw_config: Dict[str, Any] = field(default_factory=dict)


class BrokerManager:
    """
    Gestor de configuración de brokers que carga y valida las configuraciones
    de todos los brokers disponibles en el sistema.
    """
    
    def __init__(self, brokers_path: Path):
        """
        Inicializa el gestor de brokers.
        
        Args:
            brokers_path: Ruta al directorio de configuración de brokers
        """
        self.logger = logging.getLogger(__name__)
        self.brokers_path = brokers_path
        self.brokers: Dict[str, BrokerConfig] = {}
        self._loaded = False
        
        if not self.brokers_path.exists():
            raise FileNotFoundError(f"Directorio de brokers no encontrado: {brokers_path}")
    
    def load_all_brokers(self) -> bool:
        """
        Carga todas las configuraciones de brokers disponibles (estructura nueva).
        
        Returns:
            bool: True si la carga fue exitosa
        """
        try:
            self.logger.info(f"Cargando brokers desde: {self.brokers_path}")
            
            # Buscar todos los archivos YAML en el directorio
            yaml_files = list(self.brokers_path.glob("*.yaml"))
            
            if not yaml_files:
                self.logger.warning("No se encontraron archivos de configuración de brokers")
                return True
            
            for yaml_file in yaml_files:
                broker_name = yaml_file.stem  # Nombre del archivo sin extensión
                self.logger.info(f"Cargando broker: {broker_name}")
                
                try:
                    with open(yaml_file, 'r', encoding='utf-8') as f:
                        config_data = yaml.safe_load(f)
                    
                    if config_data and 'broker_settings' in config_data:
                        broker_config = self._parse_broker_config(broker_name, config_data)
                        self.brokers[broker_name.lower()] = broker_config
                        self.logger.info(f"Broker {broker_name} cargado exitosamente")
                    else:
                        self.logger.warning(f"Archivo {yaml_file} no contiene configuración válida de broker")
                        
                except Exception:
                    self.logger.exception(f"Error al cargar broker {broker_name}")
                    continue
            
            self._loaded = True
            self.logger.info(f"Total de brokers cargados: {len(self.brokers)}")
            return True
            
        except Exception:
            self.logger.exception("Error al cargar brokers")
            return False
    
    def _parse_broker_config(self, broker_name: str, config_data: Dict[str, Any]) -> BrokerConfig:
        """
        Parsea la configuración de un broker desde el diccionario de datos (estructura nueva).
        
        Args:
            broker_name: Nombre del broker
            config_data: Datos de configuración del archivo YAML
            
        Returns:
            BrokerConfig: Configuración parseada del broker
        """
        broker_info = config_data.get('broker_settings', {})
        
        return BrokerConfig(
            name=broker_info.get('broker_name', broker_name.upper()),
            type=broker_info.get('broker_type', broker_name.lower()),
            enabled=broker_info.get('enabled', True),
            connection=config_data.get('connection', {}),
            auth=config_data.get('auth', {}),
            tick_normalizer=config_data.get('tick_normalizer', {}),
            symbols=config_data.get('active_symbols', {}),
            performance=config_data.get('tick_normalizer', {}).get('performance', {}),
            logging=config_data.get('tick_normalizer', {}).get('logging', {}),
            metrics={},  # No existe sección metrics en la nueva estructura
            raw_config=config_data
        )
    
    def get_broker_config(self, broker_name: str) -> Optional[BrokerConfig]:
        """
        Obtiene la configuración de un broker específico.
        
        Args:
            broker_name: Nombre del broker
            
        Returns:
            BrokerConfig: Configuración del broker o None si no existe
        """
        return self.brokers.get(broker_name.lower())
    
    def get_all_brokers(self) -> Dict[str, Dict[str, Any]]:
        """
        Obtiene todas las configuraciones de brokers como diccionarios.
        
        Returns:
            Dict: Diccionario con todas las configuraciones de brokers
        """
        return {
            name: {
                'name': config.name,
                'type': config.type,
                'enabled': config.enabled,
                'connection': config.connection,
                'auth': config.auth,
                'tick_normalizer': config.tick_normalizer,
                'symbols': config.symbols,
                'performance': config.performance,
                'logging': config.logging,
                'metrics': config.metrics
            }
            for name, config in self.brokers.items()
        }
    
    def get_enabled_brokers(self) -> Dict[str, BrokerConfig]:
        """
        Obtiene solo los brokers habilitados.
        
        Returns:
            Dict: Diccionario con los brokers habilitados
        """
        return {
            name: config 
            for name, config in self.brokers.items() 
            if config.enabled
        }
    
    def get_brokers_by_type(self, broker_type: str) -> Dict[str, BrokerConfig]:
        """
        Obtiene brokers filtrados por tipo.
        
        Args:
            broker_type: Tipo de broker a filtrar
            
        Returns:
            Dict: Diccionario con los brokers del tipo especificado
        """
        return {
            name: config 
            for name, config in self.brokers.items() 
            if config.type.lower() == broker_type.lower()
        }
    
    def get_broker_symbols(self, broker_name: str) -> Dict[str, Any]:
        """
        Obtiene los símbolos configurados para un broker específico.
        
        Args:
            broker_name: Nombre del broker
            
        Returns:
            Dict: Configuración de símbolos del broker
        """
        broker_config = self.get_broker_config(broker_name)
        if broker_config:
            return broker_config.symbols
        return {}
    
    def get_broker_connection_config(self, broker_name: str) -> Dict[str, Any]:
        """
        Obtiene la configuración de conexión de un broker específico.
        
        Args:
            broker_name: Nombre del broker
            
        Returns:
            Dict: Configuración de conexión del broker
        """
        broker_config = self.get_broker_config(broker_name)
        if broker_config:
            return broker_config.connection
        return {}
    
    def get_broker_auth_config(self, broker_name: str) -> Dict[str, Any]:
        """
        Obtiene la configuración de autenticación de un broker específico.
        
        Args:
            broker_name: Nombre del broker
            
        Returns:
            Dict: Configuración de autenticación del broker
        """
        broker_config = self.get_broker_config(broker_name)
        if broker_config:
            return broker_config.auth
        return {}
    
    def get_broker_tick_normalizer_config(self, broker_name: str) -> Dict[str, Any]:
        """
        Obtiene la configuración del normalizador de ticks de un broker específico.
        
        Args:
            broker_name: Nombre del broker
            
        Returns:
            Dict: Configuración del normalizador de ticks
        """
        broker_config = self.get_broker_config(broker_name)
        if broker_config:
            return broker_config.tick_normalizer
        return {}
    
    def validate_all(self) -> bool:
        """
        Valida todas las configuraciones de brokers cargadas.
        
        Returns:
            bool: True si todas las validaciones pasan
        """
        try:
            for broker_name, broker_config in self.brokers.items():
                if not self._validate_broker_config(broker_config):
                    self.logger.error(f"Validación falló para broker: {broker_name}")
                    return False
            
            self.logger.info("Todas las configuraciones de brokers validadas exitosamente")
            return True
            
        except Exception:
            self.logger.exception("Error en validación de brokers")
            return False
    
    def _validate_broker_config(self, broker_config: BrokerConfig) -> bool:
        """
        Valida la configuración de un broker específico.
        
        Args:
            broker_config: Configuración del broker a validar
            
        Returns:
            bool: True si la configuración es válida
        """
        try:
            # Validar campos requeridos
            if not broker_config.name:
                self.logger.error("Nombre de broker requerido")
                return False
            
            if not broker_config.type:
                self.logger.error(f"Tipo de broker requerido para {broker_config.name}")
                return False
            
            # Validar configuración de conexión
            if not broker_config.connection:
                self.logger.error(f"Configuración de conexión requerida para {broker_config.name}")
                return False
            
            # Validar configuración de autenticación
            if not broker_config.auth:
                self.logger.error(f"Configuración de autenticación requerida para {broker_config.name}")
                return False
            
            # Validar configuración de símbolos
            if not broker_config.symbols:
                self.logger.warning(f"No hay símbolos configurados para {broker_config.name}")
            
            return True
            
        except Exception:
            self.logger.exception("Error al validar configuración de broker")
            return False
    
    def is_loaded(self) -> bool:
        """Verifica si las configuraciones de brokers han sido cargadas"""
        return self._loaded
    
    def get_broker_summary(self) -> Dict[str, Any]:
        """Obtiene un resumen de todos los brokers configurados"""
        return {
            "total_brokers": len(self.brokers),
            "enabled_brokers": len(self.get_enabled_brokers()),
            "broker_types": list(set(config.type for config in self.brokers.values())),
            "broker_names": list(self.brokers.keys()),
            "loaded": self._loaded
        }
    
    def reload_broker(self, broker_name: str) -> bool:
        """
        Recarga la configuración de un broker específico.
        
        Args:
            broker_name: Nombre del broker a recargar
            
        Returns:
            bool: True si la recarga fue exitosa
        """
        try:
            yaml_file = self.brokers_path / f"{broker_name}.yaml"
            
            if not yaml_file.exists():
                self.logger.error(f"Archivo de configuración no encontrado: {yaml_file}")
                return False
            
            with open(yaml_file, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            if config_data and 'broker_settings' in config_data:
                broker_config = self._parse_broker_config(broker_name, config_data)
                self.brokers[broker_name.lower()] = broker_config
                self.logger.info(f"Broker {broker_name} recargado exitosamente")
                return True
            else:
                self.logger.error(f"Archivo {yaml_file} no contiene configuración válida")
                return False
                
        except Exception:
            self.logger.exception(f"Error al recargar broker {broker_name}")
            return False
