"""
Gestor de Configuración de Gestión de Riesgo

Este módulo maneja la carga y gestión de configuraciones para todos
los parámetros de gestión de riesgo del sistema de trading.
"""

import logging
import os  # noqa: F401
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


@dataclass
class RiskConfig:
    """Configuración de gestión de riesgo específica"""
    name: str
    type: str
    enabled: bool
    parameters: Dict[str, Any]
    limits: Dict[str, Any]
    thresholds: Dict[str, Any]
    raw_config: Dict[str, Any] = field(default_factory=dict)


class RiskManager:
    """
    Gestor de configuración de gestión de riesgo que carga y valida las configuraciones
    de todos los parámetros de riesgo disponibles en el sistema.
    """
    
    def __init__(self, risk_path: Path):
        """
        Inicializa el gestor de gestión de riesgo.
        
        Args:
            risk_path: Ruta al directorio de configuración de gestión de riesgo
        """
        self.logger = logging.getLogger(__name__)
        self.risk_path = risk_path
        self.risk_configs: Dict[str, RiskConfig] = {}
        self._loaded = False
        
        if not self.risk_path.exists():
            raise FileNotFoundError(f"Directorio de gestión de riesgo no encontrado: {risk_path}")
    
    def load_all_risk_configs(self) -> bool:
        """
        Carga todas las configuraciones de gestión de riesgo disponibles.
        
        Returns:
            bool: True si la carga fue exitosa
        """
        try:
            self.logger.info(f"Cargando configuraciones de riesgo desde: {self.risk_path}")
            
            # Buscar todos los archivos YAML en el directorio
            yaml_files = list(self.risk_path.glob("*.yaml"))
            
            if not yaml_files:
                self.logger.warning("No se encontraron archivos de configuración de gestión de riesgo")
                return True
            
            for yaml_file in yaml_files:
                risk_type = yaml_file.stem  # Nombre del archivo sin extensión
                self.logger.info(f"Cargando configuración de riesgo: {risk_type}")
                
                try:
                    with open(yaml_file, 'r', encoding='utf-8') as f:
                        config_data = yaml.safe_load(f)
                    
                    if config_data:
                        risk_config = self._parse_risk_config(risk_type, config_data)
                        self.risk_configs[risk_type] = risk_config
                        self.logger.info(f"Configuración de riesgo {risk_type} cargada exitosamente")
                    else:
                        self.logger.warning(f"Archivo {yaml_file} no contiene configuración válida")
                        
                except Exception:
                    self.logger.exception(f"Error al cargar configuración de riesgo {risk_type}")
                    continue
            
            self._loaded = True
            self.logger.info(f"Total de configuraciones de riesgo cargadas: {len(self.risk_configs)}")
            return True
            
        except Exception:
            self.logger.exception("Error al cargar configuraciones de riesgo")
            return False
    
    def _parse_risk_config(self, risk_type: str, config_data: Dict[str, Any]) -> RiskConfig:
        """
        Parsea la configuración de gestión de riesgo desde el diccionario de datos.
        
        Args:
            risk_type: Tipo de configuración de riesgo
            config_data: Datos de configuración del archivo YAML
            
        Returns:
            RiskConfig: Configuración parseada de gestión de riesgo
        """
        return RiskConfig(
            name=risk_type,
            type=risk_type,
            enabled=config_data.get('enabled', True),
            parameters=config_data.get('parameters', {}),
            limits=config_data.get('limits', {}),
            thresholds=config_data.get('thresholds', {}),
            raw_config=config_data
        )
    
    def get_risk_config(self, risk_type: str) -> Optional[RiskConfig]:
        """
        Obtiene la configuración de gestión de riesgo específica.
        
        Args:
            risk_type: Tipo de configuración de riesgo
            
        Returns:
            RiskConfig: Configuración de gestión de riesgo o None si no existe
        """
        return self.risk_configs.get(risk_type)
    
    def get_all_risk_configs(self) -> Dict[str, Dict[str, Any]]:
        """
        Obtiene todas las configuraciones de gestión de riesgo como diccionarios.
        
        Returns:
            Dict: Diccionario con todas las configuraciones de gestión de riesgo
        """
        return {
            name: {
                'name': config.name,
                'type': config.type,
                'enabled': config.enabled,
                'parameters': config.parameters,
                'limits': config.limits,
                'thresholds': config.thresholds
            }
            for name, config in self.risk_configs.items()
        }
    
    def get_enabled_risk_configs(self) -> Dict[str, RiskConfig]:
        """
        Obtiene solo las configuraciones de gestión de riesgo habilitadas.
        
        Returns:
            Dict: Diccionario con las configuraciones habilitadas
        """
        return {
            name: config 
            for name, config in self.risk_configs.items() 
            if config.enabled
        }
    
    def get_risk_parameters(self, risk_type: str) -> Dict[str, Any]:
        """
        Obtiene los parámetros de configuración de gestión de riesgo específica.
        
        Args:
            risk_type: Tipo de configuración de riesgo
            
        Returns:
            Dict: Parámetros de configuración de gestión de riesgo
        """
        risk_config = self.get_risk_config(risk_type)
        if risk_config:
            return risk_config.parameters
        return {}
    
    def get_risk_limits(self, risk_type: str) -> Dict[str, Any]:
        """
        Obtiene los límites de configuración de gestión de riesgo específica.
        
        Args:
            risk_type: Tipo de configuración de riesgo
            
        Returns:
            Dict: Límites de configuración de gestión de riesgo
        """
        risk_config = self.get_risk_config(risk_type)
        if risk_config:
            return risk_config.limits
        return {}
    
    def get_risk_thresholds(self, risk_type: str) -> Dict[str, Any]:
        """
        Obtiene los umbrales de configuración de gestión de riesgo específica.
        
        Args:
            risk_type: Tipo de configuración de riesgo
            
        Returns:
            Dict: Umbrales de configuración de gestión de riesgo
        """
        risk_config = self.get_risk_config(risk_type)
        if risk_config:
            return risk_config.thresholds
        return {}
    
    def get_correlation_limits(self) -> Dict[str, Any]:
        """
        Obtiene los límites de correlación.
        
        Returns:
            Dict: Límites de correlación
        """
        return self.get_risk_limits('correlation_limits')
    
    def get_drawdown_limits(self) -> Dict[str, Any]:
        """
        Obtiene los límites de drawdown.
        
        Returns:
            Dict: Límites de drawdown
        """
        return self.get_risk_limits('drawdown_limits')
    
    def get_exposure_limits(self) -> Dict[str, Any]:
        """
        Obtiene los límites de exposición.
        
        Returns:
            Dict: Límites de exposición
        """
        return self.get_risk_limits('exposure_limits')
    
    def get_position_sizing_config(self) -> Dict[str, Any]:
        """
        Obtiene la configuración de dimensionamiento de posiciones.
        
        Returns:
            Dict: Configuración de dimensionamiento de posiciones
        """
        return self.get_risk_parameters('position_sizing')
    
    def validate_all(self) -> bool:
        """
        Valida todas las configuraciones de gestión de riesgo cargadas.
        
        Returns:
            bool: True si todas las validaciones pasan
        """
        try:
            for risk_type, risk_config in self.risk_configs.items():
                if not self._validate_risk_config(risk_config):
                    self.logger.error(f"Validación falló para configuración de riesgo: {risk_type}")
                    return False
            
            self.logger.info("Todas las configuraciones de gestión de riesgo validadas exitosamente")
            return True
            
        except Exception:
            self.logger.exception("Error en validación de gestión de riesgo:")
            return False
    
    def _validate_risk_config(self, risk_config: RiskConfig) -> bool:
        """
        Valida la configuración de gestión de riesgo específica.
        
        Args:
            risk_config: Configuración de gestión de riesgo a validar
            
        Returns:
            bool: True si la configuración es válida
        """
        try:
            # Validar campos requeridos
            if not risk_config.name:
                self.logger.error("Nombre de configuración de riesgo requerido")
                return False
            
            if not risk_config.type:
                self.logger.error(f"Tipo de configuración de riesgo requerido para {risk_config.name}")
                return False
            
            # Validar que tenga al menos parámetros, límites o umbrales
            if not risk_config.parameters and not risk_config.limits and not risk_config.thresholds:
                self.logger.warning(f"No hay parámetros, límites o umbrales configurados para {risk_config.name}")
            
            return True
            
        except Exception:
            self.logger.exception("Error al validar configuración de gestión de riesgo")
            return False
    
    def is_loaded(self) -> bool:
        """Verifica si las configuraciones de gestión de riesgo han sido cargadas"""
        return self._loaded
    
    def get_risk_summary(self) -> Dict[str, Any]:
        """Obtiene un resumen de todas las configuraciones de gestión de riesgo"""
        return {
            "total_configs": len(self.risk_configs),
            "enabled_configs": len(self.get_enabled_risk_configs()),
            "risk_types": list(self.risk_configs.keys()),
            "loaded": self._loaded
        }
    
    def reload_risk_config(self, risk_type: str) -> bool:
        """
        Recarga la configuración de gestión de riesgo específica.
        
        Args:
            risk_type: Tipo de configuración de riesgo a recargar
            
        Returns:
            bool: True si la recarga fue exitosa
        """
        try:
            yaml_file = self.risk_path / f"{risk_type}.yaml"
            
            if not yaml_file.exists():
                self.logger.error(f"Archivo de configuración no encontrado: {yaml_file}")
                return False
            
            with open(yaml_file, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            if config_data:
                risk_config = self._parse_risk_config(risk_type, config_data)
                self.risk_configs[risk_type] = risk_config
                self.logger.info(f"Configuración de riesgo {risk_type} recargada exitosamente")
                return True
            else:
                self.logger.error(f"Archivo {yaml_file} no contiene configuración válida")
                return False
                
        except Exception:
            self.logger.exception(f"Error al recargar configuración de riesgo {risk_type}")
            return False
    
    def get_risk_types(self) -> List[str]:
        """Obtiene la lista de todos los tipos de configuración de riesgo disponibles"""
        return list(self.risk_configs.keys())
    
    def check_risk_compliance(self, risk_metrics: Dict[str, Any]) -> Dict[str, bool]:
        """
        Verifica el cumplimiento de las configuraciones de riesgo.
        
        Args:
            risk_metrics: Métricas de riesgo actuales
            
        Returns:
            Dict: Diccionario con el estado de cumplimiento por tipo de riesgo
        """
        compliance = {}
        
        for risk_type, risk_config in self.get_enabled_risk_configs().items():
            try:
                if risk_type == 'correlation_limits':
                    compliance[risk_type] = self._check_correlation_compliance(risk_metrics, risk_config)
                elif risk_type == 'drawdown_limits':
                    compliance[risk_type] = self._check_drawdown_compliance(risk_metrics, risk_config)
                elif risk_type == 'exposure_limits':
                    compliance[risk_type] = self._check_exposure_compliance(risk_metrics, risk_config)
                else:
                    compliance[risk_type] = True  # Por defecto, cumplir
                    
            except Exception:
                self.logger.exception(f"Error al verificar cumplimiento de {risk_type}")
                compliance[risk_type] = False
        
        return compliance
    
    def _check_correlation_compliance(self, risk_metrics: Dict[str, Any], risk_config: RiskConfig) -> bool:
        """Verifica el cumplimiento de límites de correlación"""
        # Implementar lógica específica de correlación
        return True
    
    def _check_drawdown_compliance(self, risk_metrics: Dict[str, Any], risk_config: RiskConfig) -> bool:
        """Verifica el cumplimiento de límites de drawdown"""
        # Implementar lógica específica de drawdown
        return True
    
    def _check_exposure_compliance(self, risk_metrics: Dict[str, Any], risk_config: RiskConfig) -> bool:
        """Verifica el cumplimiento de límites de exposición"""
        # Implementar lógica específica de exposición
        return True
