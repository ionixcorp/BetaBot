"""
Módulo para gestionar operaciones de opciones binarias en IQOption.

Este módulo contiene funcionalidades para:
- Comprar opciones binarias (individuales y múltiples)
- Vender opciones binarias
- Verificar resultados de operaciones
- Obtener detalles de opciones y beneficios
"""

import logging
import time
from typing import Any, Dict, List, Optional, Tuple, Union

from core.config_manager import BrokerManager, ConfigManager
from iqoption.account import IQOptionAccount, check_connection

# Constantes
ACTION_CALL = "call"  # Opción de compra (sube)
ACTION_PUT = "put"    # Opción de venta (baja)

# Configuración de logging
logger = logging.getLogger(__name__)


class IQOptionBinaryOption:
    """
    Clase para gestionar operaciones de opciones binarias en IQOption.
    """
    
    def __init__(self, account: IQOptionAccount, config_manager: Optional[ConfigManager] = None):
        """
        Inicializa el gestor de opciones binarias.
        
        Args:
            account: Instancia de IQOptionAccount para interactuar con la API
            config_manager: Instancia opcional de ConfigManager para acceder a la configuración
        """
        self.account = account
        self.config_manager = config_manager if config_manager else ConfigManager()
        self.broker_manager = BrokerManager(self.config_manager)
        
        # Verificar si el broker está habilitado
        broker_config = self.broker_manager.get_broker_config("iqoption")
        if not broker_config or not broker_config.enabled:
            logger.warning("El broker IQOption no está habilitado en la configuración")
        
        # Cargar configuración específica del broker
        broker_config = self.broker_manager.get_broker_config("iqoption")
        
        # Configurar parámetros según la configuración
        self.default_expiration = broker_config.get("binary_options", {}).get("expiration_time", 60)
        self.default_amount = broker_config.get("binary_options", {}).get("amount", 1)
        self.retry_attempts = broker_config.get("settings", {}).get("retry_attempts", 3)
        self.retry_delay = broker_config.get("settings", {}).get("retry_delay", 2)  # en segundos
        
        # Caché para almacenar detalles de opciones y beneficios
        self._binary_option_detail_cache = {}
        self._profit_cache = {}
        self._last_cache_update = 0
        self.cache_ttl = 60  # Tiempo de vida de la caché en segundos
        
        logger.info("IQOptionBinaryOption inicializado")
    
    @check_connection
    def buy(self, amount: float, asset: str, direction: str, 
            expiration: Optional[int] = None) -> Tuple[bool, Optional[int]]:
        """
        Compra una opción binaria.
        
        Args:
            amount: Cantidad a invertir
            asset: Nombre del activo (ej: "EURUSD")
            direction: Dirección de la operación ("call" para subida, "put" para bajada)
            expiration: Tiempo de expiración en minutos (si es None, se usa el valor por defecto)
            
        Returns:
            Tupla con (éxito, id_operación)
        """
        # Usar el valor por defecto si no se especifica expiración
        if expiration is None:
            expiration = self.default_expiration
        
        # Validar la dirección
        if direction.lower() not in [ACTION_CALL, ACTION_PUT]:
            logger.error(f"Dirección inválida: {direction}. Debe ser 'call' o 'put'")
            return False, None
        
        # Normalizar el nombre del activo (convertir a mayúsculas)
        asset = asset.upper()
        
        # Implementar reintentos
        for attempt in range(self.retry_attempts):
            try:
                logger.info(f"Comprando opción binaria: {asset}, {direction}, {amount}, expiración: {expiration}")
                success, operation_id = self.account.api.buy(amount, asset, direction, expiration)
                
                if success:
                    logger.info(f"Compra exitosa de opción binaria en {asset}, ID: {operation_id}")
                    return True, operation_id
                else:
                    logger.warning(f"Fallo en compra de opción binaria en {asset}: {operation_id}")
                    
                    if attempt < self.retry_attempts - 1:
                        logger.info(f"Reintentando compra ({attempt+1}/{self.retry_attempts})...")
                        time.sleep(self.retry_delay)
                    else:
                        logger.error(f"Fallo al comprar opción binaria después de {self.retry_attempts} intentos")
                        return False, None
            except Exception:
                if attempt < self.retry_attempts - 1:
                    logger.warning(f"Error al comprar opción binaria, reintentando ({attempt+1}/{self.retry_attempts})...")
                    time.sleep(self.retry_delay)
                else:
                    logger.exception(f"Error al comprar opción binaria después de {self.retry_attempts} intentos")
                    return False, None
        
        return False, None
    
    @check_connection
    def buy_multi(self, amounts: List[float], assets: List[str], 
                 directions: List[str], expirations: List[int]) -> List[int]:
        """
        Compra múltiples opciones binarias.
        
        Args:
            amounts: Lista de cantidades a invertir
            assets: Lista de nombres de activos
            directions: Lista de direcciones ("call" o "put")
            expirations: Lista de tiempos de expiración en minutos
            
        Returns:
            Lista de IDs de operaciones (las operaciones fallidas no se incluyen)
        """
        # Verificar que todas las listas tengan la misma longitud
        if not (len(amounts) == len(assets) == len(directions) == len(expirations)):
            logger.error("Todas las listas deben tener la misma longitud")
            return []
        
        # Normalizar los nombres de los activos (convertir a mayúsculas)
        assets = [asset.upper() for asset in assets]
        
        try:
            logger.info(f"Comprando {len(assets)} opciones binarias")
            operation_ids = self.account.api.buy_multi(amounts, assets, directions, expirations)
            
            if operation_ids:
                logger.info(f"Compra múltiple exitosa, {len(operation_ids)} operaciones realizadas")
                return operation_ids
            else:
                logger.warning("Fallo en compra múltiple de opciones binarias")
                return []
        except Exception:
            logger.exception("Error al comprar múltiples opciones binarias")
            return []
    
    @check_connection
    def buy_by_raw_expirations(self, amount: float, asset: str, direction: str, 
                              option_type: str, expiration_timestamp: int) -> Tuple[bool, Optional[int]]:
        """
        Compra una opción binaria con un tiempo de expiración específico.
        
        Args:
            amount: Cantidad a invertir
            asset: Nombre del activo
            direction: Dirección de la operación ("call" o "put")
            option_type: Tipo de opción ("turbo" o "binary")
            expiration_timestamp: Timestamp de expiración
            
        Returns:
            Tupla con (éxito, id_operación)
        """
        # Normalizar el nombre del activo
        asset = asset.upper()
        
        # Validar la dirección
        if direction.lower() not in [ACTION_CALL, ACTION_PUT]:
            logger.error(f"Dirección inválida: {direction}. Debe ser 'call' o 'put'")
            return False, None
        
        # Validar el tipo de opción
        if option_type.lower() not in ["turbo", "binary"]:
            logger.error(f"Tipo de opción inválido: {option_type}. Debe ser 'turbo' o 'binary'")
            return False, None
        
        # Implementar reintentos
        for attempt in range(self.retry_attempts):
            try:
                logger.info(f"Comprando opción {option_type} con expiración específica: {asset}, {direction}, {amount}")
                success, operation_id = self.account.api.buy_by_raw_expirations(
                    amount, asset, direction, option_type, expiration_timestamp
                )
                
                if success:
                    logger.info(f"Compra exitosa de opción con expiración específica en {asset}, ID: {operation_id}")
                    return True, operation_id
                else:
                    logger.warning(f"Fallo en compra de opción con expiración específica en {asset}")
                    
                    if attempt < self.retry_attempts - 1:
                        logger.info(f"Reintentando compra ({attempt+1}/{self.retry_attempts})...")
                        time.sleep(self.retry_delay)
                    else:
                        logger.error(f"Fallo al comprar opción después de {self.retry_attempts} intentos")
                        return False, None
            except Exception:
                if attempt < self.retry_attempts - 1:
                    logger.warning(f"Error al comprar opción, reintentando ({attempt+1}/{self.retry_attempts})...")
                    time.sleep(self.retry_delay)
                else:
                    logger.exception(f"Error al comprar opción después de {self.retry_attempts} intentos")
                    return False, None
        
        return False, None
    
    @check_connection
    def get_remaining_time(self, expiration_mode: int) -> int:
        """
        Obtiene el tiempo restante para una expiración específica.
        
        Args:
            expiration_mode: Modo de expiración (1 para turbo, etc.)
            
        Returns:
            Tiempo restante en segundos
        """
        try:
            remaining = self.account.api.get_remaning(expiration_mode)
            return remaining
        except Exception:
            logger.exception("Error al obtener tiempo restante")
            return 0
    
    @check_connection
    def sell_option(self, option_ids: Union[int, List[int]]) -> Dict[str, Any]:
        """
        Vende una o varias opciones binarias.
        
        Args:
            option_ids: ID o lista de IDs de las opciones a vender
            
        Returns:
            Resultado de la operación de venta
        """
        try:
            logger.info(f"Vendiendo opción(es): {option_ids}")
            result = self.account.api.sell_option(option_ids)
            logger.info(f"Resultado de venta: {result}")
            return result
        except Exception:
            logger.exception("Error al vender opción(es)")
            return {"error": "Error al vender opción(es)"}
    
    @check_connection
    def check_win(self, option_id: int) -> float:
        """
        Verifica el resultado de una operación (ganancia/pérdida).
        Este método espera hasta que la operación finalice.
        
        Args:
            option_id: ID de la operación
            
        Returns:
            Ganancia (positiva) o pérdida (negativa)
        """
        try:
            logger.info(f"Verificando resultado de operación {option_id}")
            result = self.account.api.check_win(option_id)
            logger.info(f"Resultado de operación {option_id}: {result}")
            return result
        except Exception:
            logger.exception(f"Error al verificar resultado de operación {option_id}")
            return 0
    
    @check_connection
    def check_win_v2(self, option_id: int, polling_time: int = 1) -> float:
        """
        Verifica el resultado de una operación con un tiempo de polling específico.
        
        Args:
            option_id: ID de la operación
            polling_time: Tiempo de espera entre verificaciones (segundos)
            
        Returns:
            Ganancia (positiva) o pérdida (negativa)
        """
        try:
            logger.info(f"Verificando resultado de operación {option_id} (v2)")
            result = self.account.api.check_win_v2(option_id, polling_time)
            logger.info(f"Resultado de operación {option_id}: {result}")
            return result
        except Exception:
            logger.exception(f"Error al verificar resultado de operación {option_id}")
            return 0
    
    @check_connection
    def check_win_v3(self, option_id: int) -> float:
        """
        Verifica el resultado de una operación (método mejorado).
        
        Args:
            option_id: ID de la operación
            
        Returns:
            Ganancia (positiva) o pérdida (negativa)
        """
        try:
            logger.info(f"Verificando resultado de operación {option_id} (v3)")
            result = self.account.api.check_win_v3(option_id)
            logger.info(f"Resultado de operación {option_id}: {result}")
            return result
        except Exception:
            logger.exception(f"Error al verificar resultado de operación {option_id}")
            return 0
    
    @check_connection
    def get_binary_option_detail(self) -> Dict[str, Any]:
        """
        Obtiene detalles de las opciones binarias disponibles.
        
        Returns:
            Diccionario con detalles de las opciones binarias
        """
        # Verificar si la caché está actualizada
        current_time = time.time()
        if self._binary_option_detail_cache and current_time - self._last_cache_update < self.cache_ttl:
            return self._binary_option_detail_cache
        
        try:
            logger.debug("Obteniendo detalles de opciones binarias")
            details = self.account.api.get_binary_option_detail()
            
            # Actualizar caché
            self._binary_option_detail_cache = details
            self._last_cache_update = current_time
            
            return details
        except Exception:
            logger.exception("Error al obtener detalles de opciones binarias")
            return {}
    
    @check_connection
    def get_all_profit(self) -> Dict[str, Any]:
        """
        Obtiene los beneficios para todas las opciones binarias.
        
        Returns:
            Diccionario con beneficios por activo y tipo
        """
        # Verificar si la caché está actualizada
        current_time = time.time()
        if self._profit_cache and current_time - self._last_cache_update < self.cache_ttl:
            return self._profit_cache
        
        try:
            logger.debug("Obteniendo beneficios de opciones binarias")
            profits = self.account.api.get_all_profit()
            
            # Actualizar caché
            self._profit_cache = profits
            self._last_cache_update = current_time
            
            return profits
        except Exception:
            logger.exception("Error al obtener beneficios de opciones binarias")
            return {}
    
    @check_connection
    def get_betinfo(self, option_id: int) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Obtiene información detallada de una operación específica.
        
        Args:
            option_id: ID de la operación
            
        Returns:
            Tupla con (éxito, información)
        """
        try:
            logger.debug(f"Obteniendo información de operación {option_id}")
            success, info = self.account.api.get_betinfo(option_id)
            
            if success:
                return True, info
            else:
                logger.warning(f"No se pudo obtener información de operación {option_id}")
                return False, None
        except Exception:
            logger.exception(f"Error al obtener información de operación {option_id}")
            return False, None
    
    @check_connection
    def get_option_history(self, count: int = 10) -> List[Dict[str, Any]]:
        """
        Obtiene el historial de operaciones de opciones binarias.
        
        Args:
            count: Número de operaciones a obtener
            
        Returns:
            Lista de operaciones
        """
        try:
            logger.debug(f"Obteniendo historial de {count} operaciones")
            history = self.account.api.get_optioninfo_v2(count)
            return history
        except Exception:
            logger.exception("Error al obtener historial de operaciones")
            return []
    
    @check_connection
    def get_options_open_by_other_pc(self) -> Dict[str, Any]:
        """
        Obtiene las operaciones abiertas por otras sesiones de la misma cuenta.
        
        Returns:
            Diccionario con operaciones abiertas
        """
        try:
            logger.debug("Obteniendo operaciones abiertas por otras sesiones")
            operations = self.account.api.get_option_open_by_other_pc()
            return operations
        except Exception:
            logger.exception("Error al obtener operaciones abiertas por otras sesiones")
            return {}
    
    @check_connection
    def del_option_open_by_other_pc(self, option_id: int) -> bool:
        """
        Elimina una operación abierta por otra sesión.
        
        Args:
            option_id: ID de la operación
            
        Returns:
            True si se eliminó correctamente, False en caso contrario
        """
        try:
            logger.info(f"Eliminando operación {option_id} abierta por otra sesión")
            result = self.account.api.del_option_open_by_other_pc(option_id)
            return result
        except Exception:
            logger.exception(f"Error al eliminar operación {option_id} abierta por otra sesión")
            return False
    
    def get_profit_for_asset(self, asset: str, option_type: str = "turbo") -> float:
        """
        Obtiene el beneficio para un activo y tipo de opción específicos.
        
        Args:
            asset: Nombre del activo
            option_type: Tipo de opción ("turbo" o "binary")
            
        Returns:
            Beneficio como porcentaje (0.0 - 1.0)
        """
        # Normalizar el nombre del activo
        asset = asset.upper()
        
        # Validar el tipo de opción
        if option_type.lower() not in ["turbo", "binary"]:
            logger.error(f"Tipo de opción inválido: {option_type}. Debe ser 'turbo' o 'binary'")
            return 0.0
        
        # Obtener todos los beneficios
        all_profits = self.get_all_profit()
        
        try:
            # Intentar obtener el beneficio para el activo y tipo especificados
            if asset in all_profits and option_type in all_profits[asset]:
                profit = all_profits[asset][option_type]
                return profit
            else:
                logger.warning(f"No se encontró beneficio para {asset} con tipo {option_type}")
                return 0.0
        except Exception:
            logger.exception(f"Error al obtener beneficio para {asset} con tipo {option_type}")
            return 0.0
    
    def calculate_optimal_time_to_buy(self, expiration_mode: int, buffer_seconds: int = 30) -> int:
        """
        Calcula el tiempo óptimo para comprar una opción.
        
        Args:
            expiration_mode: Modo de expiración
            buffer_seconds: Segundos de margen antes de la expiración
            
        Returns:
            Tiempo de compra óptimo en segundos
        """
        remaining_time = self.get_remaining_time(expiration_mode)
        purchase_time = remaining_time - buffer_seconds
        
        # Asegurarse de que el tiempo de compra sea positivo
        if purchase_time < 0:
            purchase_time = 0
            
        return purchase_time
