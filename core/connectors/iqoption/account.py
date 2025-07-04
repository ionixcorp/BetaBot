"""
Módulo para gestionar las operaciones de cuenta con la API de IQOption.

Este módulo contiene funcionalidades para:
- Conectarse a la API de IQOption
- Gestionar balances de cuenta
- Cambiar entre cuentas de práctica y real
- Obtener información de usuario
- Suscribirse y manejar datos de acuerdos en vivo
"""

import logging
import time
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Tuple, Union  # noqa: F401

# Importar la API estable de IQOption
from iqoptionapi.stable_api import IQ_Option

# Importar el sistema de configuración de BetaBot
from core.config_manager import BrokerManager, ConfigManager

# Constantes
MODE_PRACTICE = "PRACTICE"
MODE_REAL = "REAL"
ERROR_PASSWORD = """{"code":"invalid_credentials","message":"You entered the wrong credentials. Please check that the login/password is correct."}"""

# Configuración de logging
logger = logging.getLogger(__name__)


def require_connection(func):
    """
    Decorador para verificar la conexión antes de ejecutar un método.
    Intenta reconectar si la conexión se ha perdido.
    
    Args:
        func: La función a decorar
        
    Returns:
        La función decorada
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self.check_connection():
            logger.warning("La conexión con IQOption se ha perdido. Intentando reconectar...")
            connected, reason = self.connect()
            if not connected:
                logger.error(f"Error al reconectar: {reason}")
                return None
            logger.info("Reconexión exitosa")
        return func(self, *args, **kwargs)
    return wrapper


class IQOptionAccount:
    """
    Clase para gestionar cuentas y operaciones de usuario con IQOption.
    """
    
    def __init__(self, email: Optional[str] = None, password: Optional[str] = None, 
                 account_type: Optional[str] = None, config_manager: Optional[ConfigManager] = None):
        """
        Inicializa la conexión con la API de IQOption.
        
        Args:
            email: Correo electrónico de la cuenta (opcional si se proporciona config_manager)
            password: Contraseña de la cuenta (opcional si se proporciona config_manager)
            account_type: Tipo de cuenta ('PRACTICE' o 'REAL') (opcional si se proporciona config_manager)
            config_manager: Instancia opcional de ConfigManager para cargar la configuración
        """
        self.config_manager = config_manager if config_manager else ConfigManager()
        self.broker_manager = BrokerManager(self.config_manager)
        
        # Verificar si el broker está habilitado
        broker_config = self.broker_manager.get_broker_config("iqoption")
        if not broker_config or not broker_config.enabled:
            logger.warning("El broker IQOption no está habilitado en la configuración")
        
        # Cargar configuración del broker
        connection_config = self.broker_manager.get_broker_connection_config("iqoption")
        auth_config = self.broker_manager.get_broker_auth_config("iqoption")
        
        # Priorizar parámetros pasados directamente, luego usar los de la configuración
        self.email = email if email is not None else auth_config.get("username", "")
        self.password = password if password is not None else auth_config.get("password", "")
        self.account_type = account_type if account_type is not None else auth_config.get("account_type", MODE_PRACTICE)
        
        # Verificar que tenemos las credenciales necesarias
        if not self.email or not self.password:
            logger.error("No se proporcionaron credenciales para IQOption y no se encontraron en la configuración")
            raise ValueError("Se requieren credenciales (email y password) para conectar con IQOption")
        
        # Configurar opciones adicionales desde la configuración
        self.max_reconnect_attempts = connection_config.get("max_reconnection_attempts", 3)
        self.reconnect_delay = connection_config.get("reconnection_delay_seconds", 5)  # en segundos
        
        # Inicializar la API de IQOption
        self.api = IQ_Option(self.email, self.password)
        self.connected = False
        self.connection_error = None
        
    def connect(self) -> Tuple[bool, Optional[str]]:
        """
        Establece la conexión con la API de IQOption.
        
        Returns:
            Tupla con (éxito, mensaje_de_error)
                - Si la conexión es exitosa: (True, None)
                - Si falla: (False, razón_del_fallo)
        """
        attempt = 0
        while attempt < self.max_reconnect_attempts:
            try:
                logger.info(f"Conectando a IQOption con usuario: {self.email} (intento {attempt + 1}/{self.max_reconnect_attempts})")
                connected, reason = self.api.connect()
                
                if connected:
                    logger.info("Conexión exitosa a IQOption")
                    self.connected = True
                    self.connection_error = None
                    
                    # Cambiar al tipo de cuenta indicado
                    self.change_account_mode(self.account_type)
                    return True, None
                else:
                    logger.error(f"Error al conectar con IQOption: {reason}")
                    attempt += 1
                    if attempt < self.max_reconnect_attempts:
                        logger.info(f"Esperando {self.reconnect_delay} segundos antes de reintentar...")
                        time.sleep(self.reconnect_delay)
                    else:
                        self.connected = False
                        self.connection_error = reason
                        return False, reason
                    
            except Exception as e:
                logger.exception("Excepción al conectar con IQOption")
                attempt += 1
                if attempt < self.max_reconnect_attempts:
                    logger.info(f"Esperando {self.reconnect_delay} segundos antes de reintentar...")
                    time.sleep(self.reconnect_delay)
                else:
                    self.connected = False
                    self.connection_error = str(e)
                    return False, str(e)
        
        return False, "Máximo número de intentos de conexión alcanzado"
    
    def set_session(self, header: Dict | None = None, cookie: Dict | None = None) -> None:
        """
        Establece los parámetros de la sesión HTTP.
        
        Args:
            header: Cabeceras HTTP personalizadas
            cookie: Cookies HTTP personalizadas
        """
        self.api.set_session(header, cookie)
        
    def check_connection(self) -> bool:
        """
        Verifica si la conexión con la API está activa.
        
        Returns:
            True si la conexión está activa, False en caso contrario
        """
        return self.api.check_connect()
    
    @require_connection
    def get_server_timestamp(self) -> int:
        """
        Obtiene el timestamp del servidor de IQOption.
        
        Returns:
            Timestamp actual del servidor
        """
        return self.api.get_server_timestamp()
    
    @require_connection
    def get_balance(self) -> float:
        """
        Obtiene el saldo actual de la cuenta.
        
        Returns:
            El saldo actual
        """
        return self.api.get_balance()
    
    @require_connection
    def get_balance_v2(self) -> float:
        """
        Obtiene el saldo de la cuenta con mayor precisión.
        
        Returns:
            El saldo actual con mayor precisión
        """
        return self.api.get_balance_v2()
    
    @require_connection
    def get_currency(self) -> str:
        """
        Obtiene la moneda de la cuenta.
        
        Returns:
            Código de la moneda (USD, EUR, etc.)
        """
        return self.api.get_currency()
    
    @require_connection
    def reset_practice_balance(self) -> bool:
        """
        Recarga el saldo de la cuenta de práctica a $10000.
        
        Returns:
            True si se reestableció el saldo, False en caso contrario
        """
        logger.info("Reestableciendo saldo de cuenta de práctica")
        return self.api.reset_practice_balance()
    
    @require_connection
    def change_account_mode(self, mode: str) -> bool:
        """
        Cambia entre los modos de cuenta práctica y real.
        
        Args:
            mode: Modo de cuenta ('PRACTICE' o 'REAL')
            
        Returns:
            True si el cambio fue exitoso, False en caso contrario
        """
        if mode not in [MODE_PRACTICE, MODE_REAL]:
            logger.error(f"Modo de cuenta no válido: {mode}")
            return False
            
        logger.info(f"Cambiando al modo de cuenta: {mode}")
        try:
            result = self.api.change_balance(mode)
            if result:
                self.account_type = mode
                logger.info(f"Modo de cuenta cambiado exitosamente a: {mode}")
            return result
        except Exception:
            logger.exception("Error al cambiar el modo de cuenta")
            return False
    
    @require_connection
    def get_user_profile_client(self, user_id: int) -> Dict[str, Any]:
        """
        Obtiene el perfil de un usuario por su ID.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Datos del perfil del usuario
        """
        return self.api.get_user_profile_client(user_id)
    
    @require_connection
    def request_leaderboard_userinfo_deals_client(self, user_id: int, country_id: int) -> Dict[str, Any]:
        """
        Obtiene información de las operaciones de un usuario en la tabla de clasificación.
        
        Args:
            user_id: ID del usuario
            country_id: ID del país
            
        Returns:
            Datos del usuario en la tabla de clasificación
        """
        return self.api.request_leaderboard_userinfo_deals_client(user_id, country_id)
    
    @require_connection
    def get_users_availability(self, user_id: int) -> Dict[str, Any]:
        """
        Verifica la disponibilidad de un usuario.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Datos de disponibilidad del usuario
        """
        return self.api.get_users_availability(user_id)
    
    @require_connection
    def subscribe_live_deal(self, name: str, active: str, _type: str, buffer_size: Optional[int] = None) -> None:
        """
        Suscribe a eventos de acuerdos en vivo.
        
        Args:
            name: Nombre del evento ('live-deal-binary-option-placed'/'live-deal-digital-option')
            active: Activo (ej: 'EURUSD')
            _type: Tipo ('turbo'/'binary' para opciones binarias, 'PT1M'/'PT5M'/'PT15M' para opciones digitales)
            buffer_size: Tamaño del búfer (si es None, se usa el valor de la configuración)
        """
        # Obtener tamaño de búfer de la configuración si no se especifica
        if buffer_size is None:
            broker_settings = self.broker_manager.get_broker_settings("iqoption")
            buffer_size = broker_settings.get("live_deal_buffer_size", 50)
            
        logger.info(f"Suscribiéndose a acuerdos en vivo - {name} para {active}, tipo: {_type}")
        self.api.subscribe_live_deal(name, active, _type, buffer_size)
    
    @require_connection
    def unsubscribe_live_deal(self, name: str, active: str, _type: str) -> None:
        """
        Cancela la suscripción a eventos de acuerdos en vivo.
        
        Args:
            name: Nombre del evento ('live-deal-binary-option-placed'/'live-deal-digital-option')
            active: Activo (ej: 'EURUSD')
            _type: Tipo ('turbo'/'binary' para opciones binarias, 'PT1M'/'PT5M'/'PT15M' para opciones digitales)
        """
        logger.info(f"Cancelando suscripción a acuerdos en vivo - {name} para {active}, tipo: {_type}")
        self.api.unscribe_live_deal(name, active, _type)
    
    @require_connection
    def get_live_deal(self, name: str, active: str, _type: str) -> List[Dict[str, Any]]:
        """
        Obtiene los datos de acuerdos en vivo.
        
        Args:
            name: Nombre del evento ('live-deal-binary-option-placed'/'live-deal-digital-option')
            active: Activo (ej: 'EURUSD')
            _type: Tipo ('turbo'/'binary' para opciones binarias, 'PT1M'/'PT5M'/'PT15M' para opciones digitales)
            
        Returns:
            Lista de acuerdos en vivo
        """
        return self.api.get_live_deal(name, active, _type)
    
    @require_connection
    def pop_live_deal(self, name: str, active: str, _type: str) -> Dict[str, Any]:
        """
        Extrae y elimina el último acuerdo en vivo de la lista.
        
        Args:
            name: Nombre del evento ('live-deal-binary-option-placed'/'live-deal-digital-option')
            active: Activo (ej: 'EURUSD')
            _type: Tipo ('turbo'/'binary' para opciones binarias, 'PT1M'/'PT5M'/'PT15M' para opciones digitales)
            
        Returns:
            Último acuerdo en vivo
        """
        return self.api.pop_live_deal(name, active, _type)
    
    def get_active_assets_for_broker(self) -> List[Dict[str, Any]]:
        """
        Obtiene los activos activos para IQOption desde la configuración.
        
        Returns:
            Lista de configuraciones de activos activos
        """
        return self.broker_manager.get_active_assets("iqoption")
    
    def get_active_asset_names(self, category: Optional[str] = None) -> List[str]:
        """
        Obtiene los nombres de los activos activos para IQOption, opcionalmente filtrados por categoría.
        
        Args:
            category: Categoría para filtrar (forex, otc, etc.)
            
        Returns:
            Lista de nombres de activos
        """
        return self.broker_manager.get_active_asset_names("iqoption", category)
    
    def get_asset_config(self, asset_name: str) -> Dict[str, Any]:
        """
        Obtiene la configuración completa para un activo específico.
        
        Args:
            asset_name: Nombre del activo (ej: 'EURUSD-OTC')
            
        Returns:
            Configuración completa del activo
        """
        return self.broker_manager.build_asset_data("iqoption", asset_name)
    
    def __del__(self):
        """
        Cierra la conexión al destruir la instancia.
        """
        try:
            if hasattr(self, 'api') and self.connected:
                # La API no tiene un método explícito para cerrar la conexión,
                # pero podemos cerrar el websocket si está disponible
                if hasattr(self.api, 'websocket') and self.api.websocket:
                    self.api.websocket.close()
                    logger.info("Conexión con IQOption cerrada correctamente")
        except Exception:
            logger.exception("Error al cerrar la conexión")
