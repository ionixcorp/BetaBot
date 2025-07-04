"""
Paquete de conectores para la API de IQOption.

Este paquete contiene módulos para interactuar con la API de IQOption:
- account: Gestión de cuentas y operaciones de usuario
- subscribe_symbol: Suscripción a símbolos y obtención de datos de velas
"""

from .account import (
    MODE_PRACTICE,
    MODE_REAL,
    IQOptionAccount,
    require_connection,
)
from .subscribe_symbol import IQOptionSymbolSubscriber

__all__ = [
    'MODE_PRACTICE',
    'MODE_REAL',
    'IQOptionAccount',
    'IQOptionSymbolSubscriber',
    'require_connection'
] 