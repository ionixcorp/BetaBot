"""
Gestor de Configuración de Assets

Este módulo maneja la carga y gestión de configuraciones para todos
los tipos de activos disponibles en el sistema de trading.
"""

import logging
import os  # noqa: F401
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


@dataclass
class AssetConfig:
    """Configuración de un asset específico"""
    name: str
    type: str
    category: str
    enabled: bool
    parameters: Dict[str, Any]
    raw_config: Dict[str, Any] = field(default_factory=dict)


class AssetManager:
    """
    Gestor de configuración de assets que carga y valida las configuraciones
    de todos los tipos de activos disponibles en el sistema.
    """
    
    def __init__(self, assets_path: Path):
        """
        Inicializa el gestor de assets.
        
        Args:
            assets_path: Ruta al directorio de configuración de assets
        """
        self.logger = logging.getLogger(__name__)
        self.assets_path = assets_path
        self.assets: Dict[str, Dict[str, AssetConfig]] = {}  # {category: {asset_name: config}}
        self._loaded = False
        
        if not self.assets_path.exists():
            raise FileNotFoundError(f"Directorio de assets no encontrado: {assets_path}")
    
    def load_all_assets(self) -> bool:
        """
        Carga todas las configuraciones de assets disponibles.
        
        Returns:
            bool: True si la carga fue exitosa
        """
        try:
            self.logger.info(f"Cargando assets desde: {self.assets_path}")
            
            # Buscar todos los subdirectorios (categorías de assets)
            asset_categories = [d for d in self.assets_path.iterdir() if d.is_dir()]
            
            if not asset_categories:
                self.logger.warning("No se encontraron categorías de assets")
                return True
            
            for category_path in asset_categories:
                category_name = category_path.name
                self.logger.info(f"Cargando categoría de assets: {category_name}")
                
                # Buscar archivos YAML en la categoría
                yaml_files = list(category_path.glob("*.yaml"))
                
                if not yaml_files:
                    self.logger.warning(f"No se encontraron archivos de configuración en categoría: {category_name}")
                    continue
                
                self.assets[category_name] = {}
                
                for yaml_file in yaml_files:
                    asset_name = yaml_file.stem  # Nombre del archivo sin extensión
                    self.logger.info(f"Cargando asset: {category_name}/{asset_name}")
                    
                    try:
                        with open(yaml_file, 'r', encoding='utf-8') as f:
                            config_data = yaml.safe_load(f)
                        
                        if config_data:
                            asset_config = self._parse_asset_config(asset_name, category_name, config_data)
                            self.assets[category_name][asset_name] = asset_config
                            self.logger.info(f"Asset {category_name}/{asset_name} cargado exitosamente")
                        else:
                            self.logger.warning(f"Archivo {yaml_file} no contiene configuración válida")
                            
                    except Exception:
                        self.logger.exception(f"Error al cargar asset {category_name}/{asset_name}")
                        continue
            
            self._loaded = True
            total_assets = sum(len(assets) for assets in self.assets.values())
            self.logger.info(f"Total de assets cargados: {total_assets} en {len(self.assets)} categorías")
            return True
            
        except Exception:
            self.logger.exception("Error al cargar assets")
            return False
    
    def _parse_asset_config(self, asset_name: str, category: str, config_data: Dict[str, Any]) -> AssetConfig:
        """
        Parsea la configuración de un asset desde el diccionario de datos.
        
        Args:
            asset_name: Nombre del asset
            category: Categoría del asset
            config_data: Datos de configuración del archivo YAML
            
        Returns:
            AssetConfig: Configuración parseada del asset
        """
        return AssetConfig(
            name=asset_name,
            type=config_data.get('type', category),
            category=category,
            enabled=config_data.get('enabled', True),
            parameters=config_data.get('parameters', {}),
            raw_config=config_data
        )
    
    def get_asset_config(self, asset_type: str, asset_name: str) -> Optional[AssetConfig]:
        """
        Obtiene la configuración de un asset específico.
        
        Args:
            asset_type: Tipo/categoría del asset
            asset_name: Nombre del asset
            
        Returns:
            AssetConfig: Configuración del asset o None si no existe
        """
        return self.assets.get(asset_type, {}).get(asset_name)
    
    def get_all_assets(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """
        Obtiene todas las configuraciones de assets como diccionarios.
        
        Returns:
            Dict: Diccionario con todas las configuraciones de assets
        """
        result = {}
        for category, assets in self.assets.items():
            result[category] = {}
            for asset_name, asset_config in assets.items():
                result[category][asset_name] = {
                    'name': asset_config.name,
                    'type': asset_config.type,
                    'category': asset_config.category,
                    'enabled': asset_config.enabled,
                    'parameters': asset_config.parameters
                }
        return result
    
    def get_assets_by_category(self, category: str) -> Dict[str, AssetConfig]:
        """
        Obtiene todos los assets de una categoría específica.
        
        Args:
            category: Categoría de assets a obtener
            
        Returns:
            Dict: Diccionario con los assets de la categoría
        """
        return self.assets.get(category, {})
    
    def get_enabled_assets(self, category: Optional[str] = None) -> Dict[str, Dict[str, AssetConfig]]:
        """
        Obtiene solo los assets habilitados.
        
        Args:
            category: Categoría específica (opcional)
            
        Returns:
            Dict: Diccionario con los assets habilitados
        """
        if category:
            return {
                category: {
                    name: config 
                    for name, config in self.assets.get(category, {}).items() 
                    if config.enabled
                }
            }
        else:
            return {
                cat: {
                    name: config 
                    for name, config in assets.items() 
                    if config.enabled
                }
                for cat, assets in self.assets.items()
            }
    
    def get_assets_by_type(self, asset_type: str) -> Dict[str, AssetConfig]:
        """
        Obtiene assets filtrados por tipo.
        
        Args:
            asset_type: Tipo de asset a filtrar
            
        Returns:
            Dict: Diccionario con los assets del tipo especificado
        """
        result = {}
        for category, assets in self.assets.items():
            for asset_name, asset_config in assets.items():
                if asset_config.type.lower() == asset_type.lower():
                    result[f"{category}/{asset_name}"] = asset_config
        return result
    
    def get_asset_parameters(self, asset_type: str, asset_name: str) -> Dict[str, Any]:
        """
        Obtiene los parámetros de configuración de un asset específico.
        
        Args:
            asset_type: Tipo/categoría del asset
            asset_name: Nombre del asset
            
        Returns:
            Dict: Parámetros de configuración del asset
        """
        asset_config = self.get_asset_config(asset_type, asset_name)
        if asset_config:
            return asset_config.parameters
        return {}
    
    def validate_all(self) -> bool:
        """
        Valida todas las configuraciones de assets cargadas.
        
        Returns:
            bool: True si todas las validaciones pasan
        """
        try:
            for category, assets in self.assets.items():
                for asset_name, asset_config in assets.items():
                    if not self._validate_asset_config(asset_config):
                        self.logger.error(f"Validación falló para asset: {category}/{asset_name}")
                        return False
            
            self.logger.info("Todas las configuraciones de assets validadas exitosamente")
            return True
            
        except Exception:
            self.logger.exception("Error en validación de assets")
            return False
    
    def _validate_asset_config(self, asset_config: AssetConfig) -> bool:
        """
        Valida la configuración de un asset específico.
        
        Args:
            asset_config: Configuración del asset a validar
            
        Returns:
            bool: True si la configuración es válida
        """
        try:
            # Validar campos requeridos
            if not asset_config.name:
                self.logger.error("Nombre de asset requerido")
                return False
            
            if not asset_config.type:
                self.logger.error(f"Tipo de asset requerido para {asset_config.name}")
                return False
            
            if not asset_config.category:
                self.logger.error(f"Categoría de asset requerida para {asset_config.name}")
                return False
            
            return True
            
        except Exception:
            self.logger.exception("Error al validar configuración de asset")
            return False
    
    def is_loaded(self) -> bool:
        """Verifica si las configuraciones de assets han sido cargadas"""
        return self._loaded
    
    def get_asset_summary(self) -> Dict[str, Any]:
        """Obtiene un resumen de todos los assets configurados"""
        total_assets = sum(len(assets) for assets in self.assets.values())
        enabled_assets = sum(
            len([config for config in assets.values() if config.enabled])
            for assets in self.assets.values()
        )
        
        return {
            "total_assets": total_assets,
            "enabled_assets": enabled_assets,
            "categories": list(self.assets.keys()),
            "asset_types": list(set(
                config.type 
                for assets in self.assets.values() 
                for config in assets.values()
            )),
            "loaded": self._loaded
        }
    
    def reload_asset(self, asset_type: str, asset_name: str) -> bool:
        """
        Recarga la configuración de un asset específico.
        
        Args:
            asset_type: Tipo/categoría del asset
            asset_name: Nombre del asset a recargar
            
        Returns:
            bool: True si la recarga fue exitosa
        """
        try:
            yaml_file = self.assets_path / asset_type / f"{asset_name}.yaml"
            
            if not yaml_file.exists():
                self.logger.error(f"Archivo de configuración no encontrado: {yaml_file}")
                return False
            
            with open(yaml_file, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            if config_data:
                asset_config = self._parse_asset_config(asset_name, asset_type, config_data)
                self.assets[asset_type][asset_name] = asset_config
                self.logger.info(f"Asset {asset_type}/{asset_name} recargado exitosamente")
                return True
            else:
                self.logger.error(f"Archivo {yaml_file} no contiene configuración válida")
                return False
                
        except Exception:
            self.logger.exception(f"Error al recargar asset {asset_type}/{asset_name}")
            return False
    
    def get_asset_categories(self) -> List[str]:
        """Obtiene la lista de todas las categorías de assets disponibles"""
        return list(self.assets.keys())
    
    def get_assets_in_category(self, category: str) -> List[str]:
        """
        Obtiene la lista de nombres de assets en una categoría específica.
        
        Args:
            category: Categoría de assets
            
        Returns:
            List: Lista de nombres de assets en la categoría
        """
        return list(self.assets.get(category, {}).keys())
