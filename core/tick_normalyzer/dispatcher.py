# Archivo generado autom�ticamente

from ..config_manager import ConfigManager
from .iqoption import IqOptionTickNormalizer


class TickDispatcher:
    """
    Dispatcher de ticks: enruta ticks crudos al normalizador correspondiente según el broker.
    """
    def __init__(self, config_manager: ConfigManager = None):
        self.config_manager = config_manager if config_manager else ConfigManager()
        self.normalizers = {
            'iqoption': IqOptionTickNormalizer(self.config_manager),
            # Aquí se pueden agregar otros normalizadores de brokers
        }

    def dispatch(self, broker: str, raw_tick: dict):
        broker = broker.lower()
        if broker not in self.normalizers:
            raise ValueError(f"No hay normalizador implementado para el broker: {broker}")
        normalizer = self.normalizers[broker]
        return normalizer.normalize(raw_tick)
