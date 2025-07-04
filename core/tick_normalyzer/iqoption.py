# Archivo generado autom�ticamente

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict

from ..config_manager import ConfigManager
from .base import BaseTickNormalizer, UnifiedTick


class IqOptionTickNormalizer(BaseTickNormalizer):
    """
    Normalizador de ticks para IQ Option.
    Convierte un tick crudo de IQ Option en un UnifiedTick usando la configuración del sistema.
    """
    def __init__(self, config_manager: ConfigManager = None):
        self.config_manager = config_manager if config_manager else ConfigManager()
        self.broker_name = "iqoption"
        super().__init__()

    def _get_broker_name(self) -> str:
        return self.broker_name

    def normalize(self, raw_tick: Dict[str, Any]) -> UnifiedTick:
        # Obtener configuración del broker y del asset
        symbol = self._extract_symbol(raw_tick)
        broker_config = self.config_manager.get_broker_config(self.broker_name)
        
        # Verificar que el broker esté habilitado
        if not broker_config or not broker_config.enabled:
            raise ValueError(f"El broker {self.broker_name} no está habilitado en la configuración")
        
        # Intentar obtener configuración del asset desde diferentes categorías
        asset_config = None
        for category in ['forex_traditional', 'crypto_traditional', 'binary_options']:
            asset_config = self.config_manager.get_asset_config(category, symbol)
            if asset_config:
                break

        # Extraer campos básicos
        timestamp = self._extract_timestamp(raw_tick)
        price = self._extract_price(raw_tick)
        volume = self._extract_volume(raw_tick)
        bid = self._extract_bid(raw_tick)
        ask = self._extract_ask(raw_tick)
        
        # Aplicar configuración de normalización del asset si está disponible
        if asset_config and hasattr(asset_config, 'parameters'):
            asset_params = asset_config.parameters.get('asset_config', {})
            
            # Aplicar configuración de dígitos
            digits = asset_params.get('digits', 5)
            truncate = asset_params.get('truncate', False)
            tolerance = asset_params.get('tolerance', 0.0001)
            
            # Aplicar configuración de dígitos con tolerancia
            price = self._apply_digits_config(price, digits, truncate, tolerance)
            if bid:
                bid = self._apply_digits_config(bid, digits, truncate, tolerance)
            if ask:
                ask = self._apply_digits_config(ask, digits, truncate, tolerance)
        
        # Calcular spread final
        spread = ask - bid if bid and ask else None

        # Crear el tick unificado
        tick = UnifiedTick(
            timestamp=timestamp,
            symbol=symbol,
            broker=self.broker_name,
            price=price,
            volume=volume,
            bid=bid,
            ask=ask,
            spread=spread,
            raw_data=raw_tick,
        )
        return tick

    def _apply_digits_config(self, value: Decimal, digits: int, truncate: bool, tolerance: float) -> Decimal:
        """
        Aplica la configuración de dígitos a un valor decimal.
        
        Args:
            value: Valor decimal a procesar
            digits: Número de dígitos decimales
            truncate: Si True, trunca; si False, redondea
            tolerance: Tolerancia de error para el truncado/redondeo
            
        Returns:
            Valor procesado según la configuración
        """
        tolerance_decimal = Decimal(str(tolerance))
        
        if truncate:
            # Truncar a los dígitos especificados
            str_value = str(value)
            if '.' in str_value:
                integer_part, decimal_part = str_value.split('.')
                if len(decimal_part) > digits:
                    decimal_part = decimal_part[:digits]
                str_value = f"{integer_part}.{decimal_part}"
            truncated_value = Decimal(str_value)
            
            # Verificar si el error de truncado excede la tolerancia
            if abs(truncated_value - value) > tolerance_decimal:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Error de truncado {abs(truncated_value - value)} excede la tolerancia {tolerance} para valor {value}")
            
            return truncated_value
        else:
            # Redondear a los dígitos especificados
            rounded_value = round(value, digits)
            
            # Verificar si el error de redondeo excede la tolerancia
            if abs(rounded_value - value) > tolerance_decimal:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Error de redondeo {abs(rounded_value - value)} excede la tolerancia {tolerance} para valor {value}")
            
            return rounded_value

    def _extract_timestamp(self, raw_tick: Dict[str, Any]) -> datetime:
        # IQ Option suele tener el campo 'timestamp' o 'from' (en velas)
        ts = raw_tick.get("timestamp") or raw_tick.get("from")
        if isinstance(ts, (int, float)):
            return datetime.utcfromtimestamp(ts)
        elif isinstance(ts, str):
            return datetime.fromisoformat(ts)
        raise ValueError("No se pudo extraer el timestamp del tick IQ Option")

    def _extract_symbol(self, raw_tick: Dict[str, Any]) -> str:
        # El campo puede ser 'symbol', 'active', 'asset', etc.
        return raw_tick.get("symbol") or raw_tick.get("active") or raw_tick.get("asset")

    def _extract_price(self, raw_tick: Dict[str, Any]) -> Decimal:
        # Puede ser 'close', 'price', 'value', etc.
        price = raw_tick.get("close") or raw_tick.get("price") or raw_tick.get("value")
        return Decimal(str(price))

    def _extract_volume(self, raw_tick: Dict[str, Any]) -> Decimal:
        v = raw_tick.get("volume")
        return Decimal(str(v)) if v is not None else None

    def _extract_bid(self, raw_tick: Dict[str, Any]) -> Decimal:
        b = raw_tick.get("bid")
        return Decimal(str(b)) if b is not None else None

    def _extract_ask(self, raw_tick: Dict[str, Any]) -> Decimal:
        a = raw_tick.get("ask")
        return Decimal(str(a)) if a is not None else None
