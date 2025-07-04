import yaml
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import json
from copy import deepcopy

@dataclass
class BrokerConfig:
    """Configuración base para brokers"""
    name: str
    type: str
    enabled: bool = True
    execution_modes: List[str] = field(default_factory=list)
    auth: Dict[str, Any] = field(default_factory=dict)
    connection: Dict[str, Any] = field(default_factory=dict)
    active_symbols: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AssetConfig:
    """Configuración base para activos"""
    symbol: str
    broker: str
    asset_type: str
    digits: int
    tolerance: float
    expiration: int
    timeframe_base: int
    risk_level: str = "medium"
    strategy_params: Dict[str, Any] = field(default_factory=dict)

@dataclass
class StrategyConfig:
    """Configuración base para estrategias"""
    name: str
    type: str
    version: str
    enabled: bool = True
    parameters: Dict[str, Any] = field(default_factory=dict)

class ConfigManager:
    """Gestor central de configuraciones con soporte para templates y herencia"""
    
    def __init__(self, config_root: str = "config"):
        self.config_root = Path(config_root)
        self.templates = {}
        self.loaded_configs = {}
        self.load_templates()
    
    def load_templates(self):
        """Carga templates base para diferentes tipos de configuración"""
        templates_path = self.config_root / "templates"
        if templates_path.exists():
            for template_file in templates_path.glob("*.yaml"):
                template_name = template_file.stem
                self.templates[template_name] = self._load_yaml(template_file)
    
    def _load_yaml(self, file_path: Path) -> Dict[str, Any]:
        """Carga archivo YAML con manejo de errores"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = yaml.safe_load(f) or {}
                # Expandir variables de entorno
                return self._expand_env_vars(content)
        except FileNotFoundError:
            return {}
        except yaml.YAMLError as e:
            raise ValueError(f"Error parsing YAML {file_path}: {e}")
    
    def _expand_env_vars(self, obj: Any) -> Any:
        """Expande variables de entorno en la configuración"""
        if isinstance(obj, dict):
            return {k: self._expand_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._expand_env_vars(item) for item in obj]
        elif isinstance(obj, str) and obj.startswith("${") and obj.endswith("}"):
            env_var = obj[2:-1]
            return os.getenv(env_var, obj)
        return obj
    
    def get_broker_config(self, broker_name: str) -> BrokerConfig:
        """Obtiene configuración de un broker específico"""
        config_path = self.config_root / "brokers" / f"{broker_name}.yaml"
        config_data = self._load_yaml(config_path)
        
        if not config_data:
            raise ValueError(f"No configuration found for broker: {broker_name}")
        
        # Aplicar template si existe
        if "template" in config_data:
            template = self.templates.get(config_data["template"], {})
            config_data = self._merge_configs(template, config_data)
        
        # Extraer configuración del broker
        broker_settings = config_data.get("broker_settings", {})
        
        return BrokerConfig(
            name=broker_settings.get("broker_name", broker_name),
            type=broker_settings.get("broker_type", "unknown"),
            enabled=broker_settings.get("enabled", True),
            execution_modes=broker_settings.get("execution_modes", []),
            auth=config_data.get("auth", {}),
            connection=config_data.get("connection", {}),
            active_symbols=config_data.get("active_symbols", {})
        )
    
    def get_asset_config(self, broker_name: str, asset_type: str, symbol: str) -> AssetConfig:
        """Obtiene configuración de un activo específico"""
        config_path = self.config_root / "assets" / asset_type / broker_name / f"{symbol}.yaml"
        config_data = self._load_yaml(config_path)
        
        if not config_data:
            raise ValueError(f"No configuration found for {symbol} on {broker_name}")
        
        # Aplicar template si existe
        if "template" in config_data:
            template = self.templates.get(config_data["template"], {})
            config_data = self._merge_configs(template, config_data)
        
        prediction_force = config_data.get("prediction_force", {})
        general = prediction_force.get("general", {})
        asset_config = prediction_force.get("asset_config", {})
        
        return AssetConfig(
            symbol=general.get("symbol", symbol),
            broker=broker_name,
            asset_type=asset_type,
            digits=asset_config.get("digits", 5),
            tolerance=asset_config.get("tolerance", 0.0002),
            expiration=asset_config.get("expiration", 1),
            timeframe_base=asset_config.get("timeframe_base", 1),
            risk_level=general.get("risk_level", "medium"),
            strategy_params=prediction_force.get("strategy_params", {})
        )
    
    def get_strategy_config(self, strategy_name: str, strategy_type: str) -> StrategyConfig:
        """Obtiene configuración de una estrategia específica"""
        config_path = self.config_root / "strategies" / strategy_type / f"{strategy_name}.yaml"
        config_data = self._load_yaml(config_path)
        
        if not config_data:
            raise ValueError(f"No configuration found for strategy: {strategy_name}")
        
        strategy = config_data.get("strategy", {})
        
        return StrategyConfig(
            name=strategy.get("name", strategy_name),
            type=strategy.get("type", strategy_type),
            version=strategy.get("version", "1.0.0"),
            enabled=strategy.get("enabled", True),
            parameters=strategy.get("strategy_parameters", {})
        )
    
    def get_metrics_config(self, metrics_name: str) -> Dict[str, Any]:
        """Obtiene configuración de métricas específicas"""
        config_path = self.config_root / "metrics" / f"{metrics_name}.yaml"
        config_data = self._load_yaml(config_path)
        
        if not config_data:
            raise ValueError(f"No configuration found for metrics: {metrics_name}")
        
        return config_data.get("metrics", {})
    
    def _merge_configs(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Combina configuraciones con precedencia del override"""
        result = deepcopy(base)
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def create_asset_config(self, broker_name: str, asset_type: str, symbol: str, 
                          template_name: str = None, **kwargs) -> AssetConfig:
        """Crea una nueva configuración de activo usando templates"""
        
        # Usar template si se especifica
        if template_name and template_name in self.templates:
            base_config = deepcopy(self.templates[template_name])
        else:
            # Template por defecto basado en tipo de activo
            base_config = {
                "prediction_force": {
                    "general": {
                        "description": f"Estrategia de prediccion para {asset_type}",
                        "author": "BetaBot Team",
                        "symbol": symbol,
                        "risk_level": "medium"
                    },
                    "asset_config": {
                        "digits": 5,
                        "tolerance": 0.0002,
                        "truncate": False,
                        "expiration": 1,
                        "timeframe_base": 1
                    },
                    "strategy_params": {}
                }
            }
        
        # Aplicar override con kwargs
        for key, value in kwargs.items():
            if key in base_config["prediction_force"]["asset_config"]:
                base_config["prediction_force"]["asset_config"][key] = value
            elif key in base_config["prediction_force"]["general"]:
                base_config["prediction_force"]["general"][key] = value
        
        # Guardar configuración
        config_path = self.config_root / "assets" / asset_type / broker_name / f"{symbol}.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(base_config, f, default_flow_style=False, allow_unicode=True)
        
        return self.get_asset_config(broker_name, asset_type, symbol)
    
    def get_all_active_assets(self) -> List[AssetConfig]:
        """Obtiene todas las configuraciones de activos activos"""
        active_assets = []
        
        assets_path = self.config_root / "assets"
        for asset_type_dir in assets_path.iterdir():
            if asset_type_dir.is_dir():
                for broker_dir in asset_type_dir.iterdir():
                    if broker_dir.is_dir():
                        for asset_file in broker_dir.glob("*.yaml"):
                            try:
                                asset_config = self.get_asset_config(
                                    broker_dir.name, 
                                    asset_type_dir.name, 
                                    asset_file.stem
                                )
                                active_assets.append(asset_config)
                            except Exception as e:
                                print(f"Error loading {asset_file}: {e}")
        
        return active_assets

# Ejemplo de uso
if __name__ == "__main__":
    # Inicializar gestor
    config_manager = ConfigManager()
    
    # Obtener configuración de broker
    try:
        iqoption_config = config_manager.get_broker_config("iqoption")
        print(f"IQOption config: {iqoption_config}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Obtener configuración de activo
    try:
        eurusd_config = config_manager.get_asset_config("iqoption", "forex", "EURUSD")
        print(f"EURUSD config: {eurusd_config}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Crear nueva configuración de activo
    try:
        new_asset = config_manager.create_asset_config(
            "iqoption", 
            "forex", 
            "GBPJPY",
            digits=3,
            expiration=5,
            risk_level="high"
        )
        print(f"New asset config: {new_asset}")
    except Exception as e:
        print(f"Error: {e}")