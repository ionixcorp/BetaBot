"""
Sistema de Gestión de Configuración para Bet-AG

Este módulo proporciona una interfaz unificada para cargar y gestionar
todas las configuraciones del sistema de trading automatizado.
"""

from .asset_manager import AssetManager
from .broker_manager import BrokerManager
from .config_manager import ConfigManager
from .risk_manager import RiskManager
from .strategy_manager import StrategyManager
from .validation import ConfigValidator

__all__ = [
    'AssetManager',
    'BrokerManager',
    'ConfigManager',
    'ConfigValidator',
    'RiskManager',
    'StrategyManager'
]

# Versión del sistema de configuración
__version__ = "1.0.0"
