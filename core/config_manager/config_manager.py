"""
Gestor Principal de Configuración

Este módulo proporciona la interfaz principal para cargar y gestionar
todas las configuraciones del sistema de trading automatizado.
"""

import logging
import os  # noqa: F401
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional  # noqa: F401

import yaml

from .asset_manager import AssetManager
from .broker_manager import BrokerManager
from .risk_manager import RiskManager
from .strategy_manager import StrategyManager
from .validation import ConfigValidator


@dataclass
class SystemConfig:
    """Configuración global del sistema"""
    metrics: Dict[str, Any] = field(default_factory=dict)
    live_global_candle: Dict[str, Any] = field(default_factory=dict)
    system: Dict[str, Any] = field(default_factory=dict)


class ConfigManager:
    """
    Gestor principal de configuración que coordina todos los demás gestores
    y proporciona una interfaz unificada para acceder a las configuraciones.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Inicializa el gestor de configuración.
        
        Args:
            config_path: Ruta al directorio de configuración. 
                        Si es None, usa la ruta por defecto.
        """
        self.logger = logging.getLogger(__name__)
        
        # Establecer ruta de configuración
        if config_path is None:
            # Buscar la ruta de configuración relativa al directorio actual
            current_dir = Path(__file__).parent.parent.parent
            self.config_path = current_dir / "config"
        else:
            self.config_path = Path(config_path)
            
        if not self.config_path.exists():
            raise FileNotFoundError(f"Directorio de configuración no encontrado: {self.config_path}")
            
        self.logger.info(f"Directorio de configuración: {self.config_path}")
        
        # Inicializar gestores específicos
        self.broker_manager = BrokerManager(self.config_path / "brokers")
        self.asset_manager = AssetManager(self.config_path / "assets")
        self.strategy_manager = StrategyManager(self.config_path / "strategies")
        self.risk_manager = RiskManager(self.config_path / "risk_management")
        
        # Configuración global del sistema
        self.system_config = SystemConfig()
        
        # Validador de configuración
        self.validator = ConfigValidator()
        
        # Estado de carga
        self._loaded = False
        self._config_cache = {}
        
    def _cross_validate_brokers_assets(self) -> bool:
        """
        Valida que los activos habilitados en cada broker existan y estén correctamente configurados.
        Busca en la subcarpeta real según broker y tipo de mercado.
        Si un activo está mal configurado o no existe, lo omite y reporta el motivo.
        """
        all_ok = True
        for broker_name, broker_cfg in self.broker_manager.brokers.items():
            broker_assets = {}
            symbols = broker_cfg.symbols or {}
            broker_type = broker_cfg.type.lower()
            for category, cat_info in symbols.items():
                if not cat_info.get('enabled', False):
                    continue
                valid_assets = []
                for asset in cat_info.get('active_assets', []):
                    # Lógica de ruta según broker y mercado
                    asset_cfg = None
                    if broker_type == 'deriv' and category == 'binary_options':
                        asset_cfg = self.asset_manager.get_asset_config('binary_options/deriv/synthetic', asset)
                    elif broker_type == 'iqoption' and category == 'forex':
                        asset_cfg = self.asset_manager.get_asset_config('binary_options/iqoption/forex', asset)
                    elif broker_type == 'iqoption' and category == 'otc':
                        asset_cfg = self.asset_manager.get_asset_config('binary_options/iqoption/otc', asset)
                    elif category == 'forex_traditional':
                        asset_cfg = self.asset_manager.get_asset_config('forex_traditional', asset)
                    else:
                        # fallback: buscar por categoría simple
                        asset_cfg = self.asset_manager.get_asset_config(category, asset)
                    if asset_cfg is None:
                        self.logger.error(f"[Broker: {broker_name}] Activo '{asset}' en categoría '{category}' no está configurado o es inválido. Se omite.")
                        all_ok = False
                        continue
                    if not getattr(asset_cfg, 'enabled', True):
                        self.logger.error(f"[Broker: {broker_name}] Activo '{asset}' en categoría '{category}' está deshabilitado. Se omite.")
                        all_ok = False
                        continue
                    valid_assets.append(asset_cfg)
                broker_assets[category] = valid_assets
            broker_cfg.valid_assets = broker_assets  # Se agrega atributo dinámico para acceso posterior
        return all_ok

    def load_all_configurations(self) -> bool:
        """
        Carga todas las configuraciones del sistema.
        
        Returns:
            bool: True si la carga fue exitosa, False en caso contrario
        """
        try:
            self.logger.info("Iniciando carga de todas las configuraciones...")
            
            # Cargar configuración global
            self._load_global_config()
            
            # Cargar configuraciones específicas
            self.broker_manager.load_all_brokers()
            self.asset_manager.load_all_assets()
            self.strategy_manager.load_all_strategies()
            self.risk_manager.load_all_risk_configs()
            
            # Validación cruzada brokers-activos
            if not self._cross_validate_brokers_assets():
                self.logger.error("Validación cruzada brokers-activos falló. Revisa los logs para detalles.")
                
            # Validar configuraciones
            if not self._validate_all_configs():
                self.logger.error("Validación de configuraciones falló")
                return False
                
            self._loaded = True
            self.logger.info("Todas las configuraciones cargadas exitosamente")
            return True
            
        except Exception:
            self.logger.exception("Error al cargar configuraciones")
            return False
    
    def _load_global_config(self):
        """Carga la configuración global del sistema"""
        global_path = self.config_path / "global"
        
        # Cargar metrics.yaml
        metrics_file = global_path / "metrics.yaml"
        if metrics_file.exists():
            with open(metrics_file, 'r', encoding='utf-8') as f:
                self.system_config.metrics = yaml.safe_load(f)
                
        # Cargar live_global_candle.yaml
        live_candle_file = global_path / "live_global_candle.yaml"
        if live_candle_file.exists():
            with open(live_candle_file, 'r', encoding='utf-8') as f:
                self.system_config.live_global_candle = yaml.safe_load(f)
                
        # Cargar system.yaml
        system_file = global_path / "system.yaml"
        if system_file.exists():
            with open(system_file, 'r', encoding='utf-8') as f:
                self.system_config.system = yaml.safe_load(f)
    
    def _validate_all_configs(self) -> bool:
        """Valida todas las configuraciones cargadas"""
        try:
            # Validar configuración global
            if not self.validator.validate_global_config(self.system_config):
                return False
                
            # Validar brokers
            if not self.broker_manager.validate_all():
                return False
                
            # Validar assets
            if not self.asset_manager.validate_all():
                return False
                
            # Validar estrategias
            if not self.strategy_manager.validate_all():
                return False
                
            # Validar gestión de riesgo
            if not self.risk_manager.validate_all():
                return False
                
            return True
            
        except Exception:
            self.logger.exception("Error en validación")
            return False
    
    def get_broker_config(self, broker_name: str) -> Optional[Dict[str, Any]]:
        """Obtiene la configuración de un broker específico"""
        return self.broker_manager.get_broker_config(broker_name)
    
    def get_asset_config(self, asset_type: str, asset_name: str) -> Optional[Dict[str, Any]]:
        """Obtiene la configuración de un asset específico"""
        return self.asset_manager.get_asset_config(asset_type, asset_name)
    
    def get_strategy_config(self, strategy_type: str, strategy_name: str) -> Optional[Dict[str, Any]]:
        """Obtiene la configuración de una estrategia específica"""
        return self.strategy_manager.get_strategy_config(strategy_type, strategy_name)
    
    def get_risk_config(self, risk_type: str) -> Optional[Dict[str, Any]]:
        """Obtiene la configuración de gestión de riesgo específica"""
        return self.risk_manager.get_risk_config(risk_type)
    
    def get_system_config(self) -> SystemConfig:
        """Obtiene la configuración global del sistema"""
        return self.system_config
    
    def get_all_brokers(self) -> Dict[str, Dict[str, Any]]:
        """Obtiene todas las configuraciones de brokers"""
        return self.broker_manager.get_all_brokers()
    
    def get_all_assets(self) -> Dict[str, Dict[str, Any]]:
        """Obtiene todas las configuraciones de assets"""
        return self.asset_manager.get_all_assets()
    
    def get_all_strategies(self) -> Dict[str, Dict[str, Any]]:
        """Obtiene todas las configuraciones de estrategias"""
        return self.strategy_manager.get_all_strategies()
    
    def get_all_risk_configs(self) -> Dict[str, Dict[str, Any]]:
        """Obtiene todas las configuraciones de gestión de riesgo"""
        return self.risk_manager.get_all_risk_configs()
    
    def reload_configuration(self, config_type: str = "all") -> bool:
        """
        Recarga las configuraciones especificadas.
        
        Args:
            config_type: Tipo de configuración a recargar 
                        ("all", "brokers", "assets", "strategies", "risk")
        
        Returns:
            bool: True si la recarga fue exitosa
        """
        try:
            if config_type in ["all", "brokers"]:
                self.broker_manager.load_all_brokers()
                
            if config_type in ["all", "assets"]:
                self.asset_manager.load_all_assets()
                
            if config_type in ["all", "strategies"]:
                self.strategy_manager.load_all_strategies()
                
            if config_type in ["all", "risk"]:
                self.risk_manager.load_all_risk_configs()
                
            if config_type == "all":
                self._load_global_config()
                
            return True
            
        except Exception:
            self.logger.exception("Error al recargar configuración")
            return False
    
    def export_configuration(self, output_path: str) -> bool:
        """
        Exporta todas las configuraciones a un archivo YAML.
        
        Args:
            output_path: Ruta del archivo de salida
            
        Returns:
            bool: True si la exportación fue exitosa
        """
        try:
            config_data = {
                "system": self.system_config.__dict__,
                "brokers": self.get_all_brokers(),
                "assets": self.get_all_assets(),
                "strategies": self.get_all_strategies(),
                "risk_management": self.get_all_risk_configs()
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(config_data, f, default_flow_style=False, indent=2)
                
            self.logger.info(f"Configuración exportada a: {output_path}")
            return True
            
        except Exception:
            self.logger.exception("Error al exportar configuración")
            return False
    
    @contextmanager
    def config_context(self):
        """Contexto para gestionar configuraciones de forma segura"""
        try:
            if not self._loaded:
                self.load_all_configurations()
            yield self
        except Exception:
            self.logger.exception("Error en contexto de configuración")
            raise
    
    def is_loaded(self) -> bool:
        """Verifica si las configuraciones han sido cargadas"""
        return self._loaded
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Obtiene un resumen de todas las configuraciones cargadas"""
        return {
            "system_config": {
                "metrics_modules": len(self.system_config.metrics.get("metrics", {})),
                "live_global_candle": bool(self.system_config.live_global_candle),
                "system_config": bool(self.system_config.system)
            },
            "brokers": len(self.get_all_brokers()),
            "assets": len(self.get_all_assets()),
            "strategies": len(self.get_all_strategies()),
            "risk_configs": len(self.get_all_risk_configs()),
            "loaded": self._loaded
        }
