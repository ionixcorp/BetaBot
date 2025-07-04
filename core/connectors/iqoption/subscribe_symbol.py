"""
Módulo para manejar la suscripción a símbolos y obtención de datos de velas en IQOption.

Este módulo contiene funcionalidades para:
- Suscribirse a streams de velas (candles) para múltiples activos
- Obtener datos históricos de velas
- Manejar datos en tiempo real de velas
- Optimizado para procesar hasta 50 activos en paralelo
"""

import logging
import time
from threading import Lock
from typing import Any, Dict, List, Optional, Set, Union

from core.broker_connectors.iqoption.account import IQOptionAccount, require_connection
from core.config_manager import BrokerManager, ConfigManager

# Constantes para tamaños de velas
CANDLE_INTERVALS = {
    1: 1,             # 1 segundo
    5: 5,             # 5 segundos
    10: 10,           # 10 segundos
    15: 15,           # 15 segundos
    30: 30,           # 30 segundos
    60: 60,           # 1 minuto
    120: 120,         # 2 minutos
    300: 300,         # 5 minutos
    600: 600,         # 10 minutos
    900: 900,         # 15 minutos
    1800: 1800,       # 30 minutos
    3600: 3600,       # 1 hora
    7200: 7200,       # 2 horas
    14400: 14400,     # 4 horas
    28800: 28800,     # 8 horas
    43200: 43200,     # 12 horas
    86400: 86400,     # 1 día
    604800: 604800,   # 1 semana
    2592000: 2592000, # 1 mes
}

# Configuración de logging
logger = logging.getLogger(__name__)


class IQOptionSymbolSubscriber:
    """
    Clase para manejar la suscripción a símbolos y obtención de datos de velas en IQOption.
    """
    
    def __init__(self, account: IQOptionAccount, config_manager: Optional[ConfigManager] = None):
        """
        Inicializa el suscriptor de símbolos.
        
        Args:
            account: Instancia de IQOptionAccount para interactuar con la API
            config_manager: Instancia opcional de ConfigManager para acceder a la configuración
        """
        self.account = account
        self.config_manager = config_manager if config_manager else ConfigManager()
        self.broker_manager = BrokerManager(self.config_manager)
        self.active_streams: Dict[str, Set[int]] = {}  # Mapeo de {activo: conjunto de intervalos activos}
        self.stream_lock = Lock()  # Para sincronización de operaciones de stream
        
        # Verificar si el broker está habilitado
        broker_config = self.broker_manager.get_broker_config("iqoption")
        if not broker_config or not broker_config.enabled:
            logger.warning("El broker IQOption no está habilitado en la configuración")
        
        # Cargar configuración específica del broker
        broker_config_data = self.broker_manager.get_broker_config("iqoption")
        
        # Configurar máximos según la configuración
        self.max_concurrent_assets = broker_config_data.raw_config.get("max_concurrent_operations", 50)
        self.default_max_dict_size = broker_config_data.raw_config.get("max_candles", 100)
        self.retry_attempts = broker_config_data.raw_config.get("retry_attempts", 3)
        self.retry_delay = broker_config_data.raw_config.get("retry_delay", 2)  # en segundos
        
        # Mapeo interno para normalizar los nombres de activos
        self._asset_name_map: Dict[str, str] = {}
        
        # Precargar mapeo de nombres de activos desde la configuración
        self._load_asset_names_from_config()
        
        logger.info(f"IQOptionSymbolSubscriber inicializado, máx. activos concurrentes: {self.max_concurrent_assets}")
    
    def check_connection(self) -> bool:
        """
        Verifica si la conexión con la API está activa.
        
        Returns:
            True si la conexión está activa, False en caso contrario
        """
        return self.account.check_connection()
    
    def _load_asset_names_from_config(self) -> None:
        """
        Carga los nombres de activos desde la configuración para el mapeo interno.
        """
        try:
            # Obtener la configuración del broker
            broker_config = self.broker_manager.get_broker_config("iqoption")
            
            # Verificar si hay configuración de active_assets
            if broker_config and 'active_assets' in broker_config.raw_config:
                # Procesar cada categoría (forex, otc, etc.)
                for category, config in broker_config.raw_config['active_assets'].items():
                    if config.get('enabled', False):
                        assets_list = config.get('assets', [])
                        
                        logger.debug(f"Cargando {len(assets_list)} activos de la categoría '{category}'")
                        
                        # En la configuración actual, los activos son strings simples
                        for asset_name in assets_list:
                            # Mapear el nombre del activo a sí mismo (en IQOption el nombre es el ID)
                            self._asset_name_map[asset_name] = asset_name
                            # También mapear el nombre en minúsculas para mayor flexibilidad
                            self._asset_name_map[asset_name.lower()] = asset_name
                            # Guardar la categoría del activo para referencia futura
                            self._asset_name_map[f"{asset_name}_category"] = category
                
                total_assets = len(self._asset_name_map) // 3  # Dividir por 3 porque tenemos: nombre, nombre_lower, y categoria
                logger.debug(f"Se cargaron {total_assets} mapeos de nombres de activos desde la configuración")
        except Exception:
            logger.exception("Error al cargar nombres de activos desde la configuración")
    
    def _normalize_interval(self, interval: Union[int, str]) -> Union[int, str]:
        """
        Normaliza el intervalo de tiempo al formato requerido por IQOption.
        
        Args:
            interval: Intervalo de tiempo en segundos o 'all'
            
        Returns:
            Intervalo normalizado en segundos o 'all'
            
        Raises:
            ValueError: Si el intervalo no es válido
        """
        def _raise_interval_error(interval, err=None):
            msg = f"Intervalo inválido: {interval}. Debe ser un número entero válido o 'all'"
            if err:
                raise ValueError(msg) from err
            raise ValueError(msg)
            
        try:
            interval_int = int(interval)
            if interval_int in CANDLE_INTERVALS:
                return interval_int
            else:
                _raise_interval_error(interval)
        except (ValueError, TypeError) as err:
            _raise_interval_error(interval, err)
    
    def _normalize_asset_name(self, asset: str) -> str:
        """
        Normaliza el nombre del activo según la configuración de IQOption.
        
        Args:
            asset: Nombre del activo
            
        Returns:
            Nombre normalizado del activo
        """
        # Si ya tenemos el nombre normalizado en caché, lo devolvemos
        if asset in self._asset_name_map:
            return self._asset_name_map[asset]
            
        # En IQOption, el nombre del activo es el mismo que se usa en la API
        # No se requiere un mapeo especial como en otros brokers
        normalized = asset.upper()
        
        # Guardar en caché para futuras consultas
        self._asset_name_map[asset] = normalized
        
        return normalized
    
    @require_connection
    def get_candles(self, asset: str, interval: Union[int, str], count: int, end_time: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Obtiene velas históricas para un activo.
        
        Args:
            asset: Nombre del activo (ej: "EURUSD")
            interval: Intervalo de tiempo en segundos o 'all'
            count: Número de velas a obtener
            end_time: Timestamp final (por defecto es el tiempo actual)
            
        Returns:
            Lista de velas históricas
        """
        normalized_asset = self._normalize_asset_name(asset)
        normalized_interval = self._normalize_interval(interval)
        
        # Si no se especifica end_time, se usa el tiempo actual
        if end_time is None:
            end_time = int(time.time())
            
        logger.debug(f"Obteniendo {count} velas históricas para {normalized_asset}, intervalo {normalized_interval}")
        
        # Implementar reintentos
        for attempt in range(self.retry_attempts):
            try:
                candles = self.account.api.get_candles(normalized_asset, normalized_interval, count, end_time)
                logger.debug(f"Se obtuvieron {len(candles)} velas históricas para {normalized_asset}")
                return candles
            except Exception:
                if attempt < self.retry_attempts - 1:
                    logger.warning(f"Error al obtener velas históricas para {normalized_asset}, reintentando ({attempt+1}/{self.retry_attempts})...")
                    time.sleep(self.retry_delay)
                else:
                    logger.exception(f"Error al obtener velas históricas para {normalized_asset} después de {self.retry_attempts} intentos")
        
        return []
    
    def get_candles_batch(self, asset: str, interval: Union[int, str], count: int, batch_size: int = 1000) -> List[Dict[str, Any]]:
        """
        Obtiene un gran número de velas históricas para un activo, haciendo múltiples solicitudes.
        
        Args:
            asset: Nombre del activo (ej: "EURUSD")
            interval: Intervalo de tiempo en segundos o 'all'
            count: Número total de velas a obtener
            batch_size: Tamaño de cada lote de velas (máximo 1000 por solicitud)
            
        Returns:
            Lista de velas históricas
        """
        if batch_size > 1000:
            batch_size = 1000  # IQOption limita a 1000 velas por solicitud
            
        result = []
        remaining = count
        end_from_time = int(time.time())
        
        logger.info(f"Obteniendo {count} velas en lotes para {asset}, intervalo {interval}")
        
        while remaining > 0:
            current_batch = min(batch_size, remaining)
            candles = self.get_candles(asset, interval, current_batch, end_from_time)
            
            if not candles:
                logger.warning(f"No se pudieron obtener más velas para {asset}. Deteniéndose después de {len(result)} velas.")
                break
                
            result = candles + result
            remaining -= len(candles)
            
            # Actualizar el tiempo para la siguiente solicitud
            if candles:
                end_from_time = int(candles[0]["from"]) - 1
            
            # Si obtenemos menos velas de las solicitadas, significa que llegamos al límite
            if len(candles) < current_batch:
                break
        
        logger.info(f"Total de velas obtenidas para {asset}: {len(result)}")
        return result
    
    @require_connection
    def start_candles_stream(self, asset: str, interval: Union[int, str], max_dict_size: Optional[int] = None) -> bool:
        """
        Inicia un stream de velas para un activo e intervalo específicos.
        
        Args:
            asset: Nombre del activo (ej: "EURUSD")
            interval: Intervalo de tiempo en segundos o 'all'
            max_dict_size: Tamaño máximo del diccionario de velas
            
        Returns:
            True si el stream se inició correctamente, False en caso contrario
        """
        normalized_asset = self._normalize_asset_name(asset)
        normalized_interval = self._normalize_interval(interval)
        
        # Usar el tamaño de diccionario predeterminado si no se especifica uno
        if max_dict_size is None:
            max_dict_size = self.default_max_dict_size
        
        with self.stream_lock:
            # Verificar si ya hemos alcanzado el límite de activos concurrentes
            unique_assets = set()
            for asset_name in self.active_streams:
                unique_assets.add(asset_name)
                
            if len(unique_assets) >= self.max_concurrent_assets and normalized_asset not in unique_assets:
                logger.error(f"No se puede iniciar stream para {normalized_asset}: se alcanzó el límite de {self.max_concurrent_assets} activos concurrentes")
                return False
            
            # Comprobar si ya hay un stream activo para este activo e intervalo
            if normalized_asset in self.active_streams and normalized_interval in self.active_streams[normalized_asset]:
                logger.debug(f"Ya existe un stream activo para {normalized_asset} con intervalo {normalized_interval}")
                return True
                
            # Implementar reintentos para iniciar el stream
            for attempt in range(self.retry_attempts):
                try:
                    logger.info(f"Iniciando stream de velas para {normalized_asset}, intervalo {normalized_interval}")
                    self.account.api.start_candles_stream(normalized_asset, normalized_interval, max_dict_size)
                    
                    # Actualizar el registro de streams activos
                    if normalized_asset not in self.active_streams:
                        self.active_streams[normalized_asset] = set()
                    self.active_streams[normalized_asset].add(normalized_interval)
                    
                    return True
                except Exception:
                    if attempt < self.retry_attempts - 1:
                        logger.warning(f"Error al iniciar stream para {normalized_asset}, reintentando ({attempt+1}/{self.retry_attempts})...")
                        time.sleep(self.retry_delay)
                    else:
                        logger.exception(f"Error al iniciar stream para {normalized_asset} después de {self.retry_attempts} intentos")
            
            return False
    
    @require_connection
    def stop_candles_stream(self, asset: str, interval: Union[int, str]) -> bool:
        """
        Detiene un stream de velas para un activo e intervalo específicos.
        
        Args:
            asset: Nombre del activo (ej: "EURUSD")
            interval: Intervalo de tiempo en segundos o 'all'
            
        Returns:
            True si el stream se detuvo correctamente, False en caso contrario
        """
        normalized_asset = self._normalize_asset_name(asset)
        normalized_interval = self._normalize_interval(interval)
        
        with self.stream_lock:
            # Comprobar si hay un stream activo para este activo e intervalo
            if normalized_asset not in self.active_streams or normalized_interval not in self.active_streams[normalized_asset]:
                logger.debug(f"No hay stream activo para {normalized_asset} con intervalo {normalized_interval}")
                return True
                
            # Implementar reintentos para detener el stream
            for attempt in range(self.retry_attempts):
                try:
                    logger.info(f"Deteniendo stream de velas para {normalized_asset}, intervalo {normalized_interval}")
                    self.account.api.stop_candles_stream(normalized_asset, normalized_interval)
                    
                    # Actualizar el registro de streams activos
                    self.active_streams[normalized_asset].remove(normalized_interval)
                    if not self.active_streams[normalized_asset]:
                        del self.active_streams[normalized_asset]
                    
                    return True
                except Exception:
                    if attempt < self.retry_attempts - 1:
                        logger.warning(f"Error al detener stream para {normalized_asset}, reintentando ({attempt+1}/{self.retry_attempts})...")
                        time.sleep(self.retry_delay)
                    else:
                        logger.exception(f"Error al detener stream para {normalized_asset} después de {self.retry_attempts} intentos")
            
            return False
    
    def stop_all_streams(self) -> bool:
        """
        Detiene todos los streams de velas activos.
        
        Returns:
            True si todos los streams se detuvieron correctamente, False si ocurrió algún error
        """
        with self.stream_lock:
            success = True
            streams_to_stop = []
            
            # Crear una copia de los streams activos para no modificar el diccionario durante la iteración
            for asset, intervals in self.active_streams.items():
                for interval in intervals:
                    streams_to_stop.append((asset, interval))
            
            # Detener cada stream
            for asset, interval in streams_to_stop:
                if not self.stop_candles_stream(asset, interval):
                    success = False
            
            return success
    
    @require_connection
    def get_realtime_candles(self, asset: str, interval: Union[int, str]) -> Dict[int, Dict[str, Any]]:
        """
        Obtiene velas en tiempo real para un activo e intervalo específicos.
        
        Se debe haber llamado previamente a start_candles_stream para este activo e intervalo.
        
        Args:
            asset: Nombre del activo (ej: "EURUSD")
            interval: Intervalo de tiempo en segundos o 'all'
            
        Returns:
            Diccionario de velas en tiempo real, con el timestamp como clave
        """
        normalized_asset = self._normalize_asset_name(asset)
        normalized_interval = self._normalize_interval(interval)
        
        # Comprobar si hay un stream activo para este activo e intervalo
        with self.stream_lock:
            if normalized_asset not in self.active_streams or normalized_interval not in self.active_streams[normalized_asset]:
                logger.warning(f"No hay stream activo para {normalized_asset} con intervalo {normalized_interval}. Intentando iniciar stream.")
                if not self.start_candles_stream(normalized_asset, normalized_interval):
                    logger.error(f"No se pudo iniciar stream para {normalized_asset} con intervalo {normalized_interval}")
                    return {}
        
        # Implementar reintentos para obtener las velas en tiempo real
        for attempt in range(self.retry_attempts):
            try:
                candles = self.account.api.get_realtime_candles(normalized_asset, normalized_interval)
                logger.debug(f"Se obtuvieron {len(candles)} velas en tiempo real para {normalized_asset}")
                return candles
            except Exception:
                if attempt < self.retry_attempts - 1:
                    logger.warning(f"Error al obtener velas en tiempo real para {normalized_asset}, reintentando ({attempt+1}/{self.retry_attempts})...")
                    time.sleep(self.retry_delay)
                else:
                    logger.exception(f"Error al obtener velas en tiempo real para {normalized_asset} después de {self.retry_attempts} intentos")
        
        return {}
    
    @require_connection
    def get_active_streams(self) -> Dict[str, List[Union[int, str]]]:
        """
        Obtiene la lista de streams de velas activos.
        
        Returns:
            Diccionario con los activos como claves y listas de intervalos como valores
        """
        result = {}
        with self.stream_lock:
            for asset, intervals in self.active_streams.items():
                result[asset] = list(intervals)
        return result
    
    def subscribe_to_multiple_assets(self, assets: List[str], interval: Union[int, str], max_dict_size: Optional[int] = None) -> Dict[str, bool]:
        """
        Suscribe a múltiples activos para un intervalo específico.
        
        Args:
            assets: Lista de nombres de activos
            interval: Intervalo de tiempo en segundos o 'all'
            max_dict_size: Tamaño máximo del diccionario de velas
            
        Returns:
            Diccionario con los activos como claves y el resultado de la suscripción como valores
        """
        results = {}
        for asset in assets:
            results[asset] = self.start_candles_stream(asset, interval, max_dict_size)
        return results
    
    def unsubscribe_from_multiple_assets(self, assets: List[str], interval: Union[int, str]) -> Dict[str, bool]:
        """
        Cancela la suscripción a múltiples activos para un intervalo específico.
        
        Args:
            assets: Lista de nombres de activos
            interval: Intervalo de tiempo en segundos o 'all'
            
        Returns:
            Diccionario con los activos como claves y el resultado de la cancelación como valores
        """
        results = {}
        for asset in assets:
            results[asset] = self.stop_candles_stream(asset, interval)
        return results
    
    def get_realtime_candles_for_multiple_assets(self, assets: List[str], interval: Union[int, str]) -> Dict[str, Dict[int, Dict[str, Any]]]:
        """
        Obtiene velas en tiempo real para múltiples activos con un intervalo específico.
        
        Args:
            assets: Lista de nombres de activos
            interval: Intervalo de tiempo en segundos o 'all'
            
        Returns:
            Diccionario con los activos como claves y diccionarios de velas como valores
        """
        results = {}
        for asset in assets:
            results[asset] = self.get_realtime_candles(asset, interval)
        return results
    
    def get_asset_config(self, asset_name: str) -> Dict[str, Any]:
        """
        Obtiene la configuración completa para un activo específico.
        
        Args:
            asset_name: Nombre del activo (ej: 'EURUSD-OTC')
            
        Returns:
            Configuración completa del activo
        """
        # Obtener la configuración del broker
        broker_config = self.broker_manager.get_broker_config("iqoption")
        
        # Obtener la categoría del activo desde nuestro mapeo
        asset_category = self.get_asset_category(asset_name)
        
        # Si no encontramos la categoría en el mapeo, intentar determinarla por el nombre
        if not asset_category:
            if '-OTC' in asset_name:
                asset_category = 'otc'
            else:
                asset_category = 'forex'
        
        # Verificar si el activo está en la lista de activos activos
        if broker_config and 'active_assets' in broker_config.raw_config and asset_category in broker_config.raw_config['active_assets']:
            category_config = broker_config.raw_config['active_assets'][asset_category]
            if category_config.get('enabled', False) and asset_name in category_config.get('assets', []):
                # Crear un diccionario con la información básica del activo
                asset_config = {
                    'name': asset_name,
                    'category': asset_category,
                    'broker': 'iqoption',
                    'timeframe': broker_config.raw_config.get('settings', {}).get('timeframe_base', 60),
                    'expiration': broker_config.raw_config.get('binary_options', {}).get('expiration_time', 60),
                    'amount': broker_config.raw_config.get('binary_options', {}).get('amount', 1)
                }
                return asset_config
        
        # Si no se encuentra el activo, devolver un diccionario básico
        return {
            'name': asset_name,
            'category': asset_category,
            'broker': 'iqoption',
            'error': f"El activo {asset_name} no está configurado o no está activo",
            'is_valid': False
        }
    
    def get_active_asset_names(self, category: Optional[str] = None) -> List[str]:
        """
        Obtiene los nombres de los activos activos para IQOption, opcionalmente filtrados por categoría.
        
        Args:
            category: Categoría para filtrar (forex, otc, etc.)
            
        Returns:
            Lista de nombres de activos
        """
        # Obtener la configuración del broker
        broker_config = self.broker_manager.get_broker_config("iqoption")
        asset_names = []
        
        # Verificar si hay configuración de active_assets
        if broker_config and 'active_assets' in broker_config.raw_config:
            # Procesar cada categoría o solo la categoría especificada
            for cat_name, cat_config in broker_config.raw_config['active_assets'].items():
                if category is None or cat_name == category:
                    if cat_config.get('enabled', False):
                        asset_names.extend(cat_config.get('assets', []))
        
        return asset_names
    
    def get_asset_category(self, asset_name: str) -> Optional[str]:
        """
        Obtiene la categoría de un activo específico.
        
        Args:
            asset_name: Nombre del activo
            
        Returns:
            Categoría del activo (forex, otc, etc.) o None si no se encuentra
        """
        normalized_asset = self._normalize_asset_name(asset_name)
        category_key = f"{normalized_asset}_category"
        return self._asset_name_map.get(category_key)
    
    def __del__(self):
        """
        Detiene todos los streams activos cuando se destruye la instancia.
        """
        try:
            if hasattr(self, 'active_streams'):
                self.stop_all_streams()
                logger.info("Se detuvieron todos los streams activos al destruir la instancia")
        except Exception:
            logger.exception("Error al detener streams durante la destrucción de la instancia")
