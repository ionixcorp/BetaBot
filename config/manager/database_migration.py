import sqlite3
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import yaml
from pathlib import Path
from config_manager import ConfigManager

class ConfigDatabase:
    """Base de datos para configuraciones con migración desde YAML"""
    
    def __init__(self, db_path: str = "config/trading_config.db"):
        self.db_path = db_path
        self.conn = None
        self.init_database()
    
    def init_database(self):
        """Inicializa la base de datos con las tablas necesarias"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        
        # Tabla de brokers
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS brokers (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                type TEXT NOT NULL,
                enabled BOOLEAN DEFAULT 1,
                config JSON NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tabla de activos
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS assets (
                id INTEGER PRIMARY KEY,
                broker_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                asset_type TEXT NOT NULL,
                enabled BOOLEAN DEFAULT 1,
                config JSON NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (broker_id) REFERENCES brokers (id),
                UNIQUE(broker_id, symbol, asset_type)
            )
        """)
        
        # Tabla de estrategias
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS strategies (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                version TEXT NOT NULL,
                enabled BOOLEAN DEFAULT 1,
                config JSON NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(name, type, version)
            )
        """)
        
        # Tabla de métricas
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                type TEXT NOT NULL,
                enabled BOOLEAN DEFAULT 1,
                config JSON NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tabla de templates
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS templates (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                type TEXT NOT NULL,
                config JSON NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tabla de configuración de assets por estrategia
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS asset_strategy_config (
                id INTEGER PRIMARY KEY,
                asset_id INTEGER NOT NULL,
                strategy_id INTEGER NOT NULL,
                enabled BOOLEAN DEFAULT 1,
                override_config JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (asset_id) REFERENCES assets (id),
                FOREIGN KEY (strategy_id) REFERENCES strategies (id),
                UNIQUE(asset_id, strategy_id)
            )
        """)
        
        self.conn.commit()
    
    def migrate_from_yaml(self, config_manager):
        """Migra configuraciones desde YAML a base de datos"""
        print("Iniciando migración desde YAML...")
        
        # Migrar brokers
        broker_configs = self._load_all_brokers(config_manager)
        for broker_name, broker_config in broker_configs.items():
            self.upsert_broker(broker_name, broker_config)
        
        # Migrar assets
        asset_configs = config_manager.get_all_active_assets()
        for asset_config in asset_configs:
            broker_id = self.get_broker_id(asset_config.broker)
            if broker_id:
                self.upsert_asset(broker_id, asset_config)
        
        # Migrar estrategias
        strategy_configs = self._load_all_strategies(config_manager)
        for strategy_name, strategy_config in strategy_configs.items():
            self.upsert_strategy(strategy_name, strategy_config)
        
        # Migrar métricas
        metrics_configs = self._load_all_metrics(config_manager)
        for metrics_name, metrics_config in metrics_configs.items():
            self.upsert_metrics(metrics_name, metrics_config)
        
        print("Migración completada.")
    
    def _load_all_brokers(self, config_manager) -> Dict[str, Dict]:
        """Carga todas las configuraciones de brokers"""
        brokers = {}
        brokers_path = Path(config_manager.config_root) / "brokers"
        
        for broker_file in brokers_path.glob("*.yaml"):
            broker_name = broker_file.stem
            try:
                broker_config = config_manager.get_broker_config(broker_name)
                brokers[broker_name] = asdict(broker_config)
            except Exception as e:
                print(f"Error loading broker {broker_name}: {e}")
        
        return brokers
    
    def _load_all_strategies(self, config_manager) -> Dict[str, Dict]:
        """Carga todas las configuraciones de estrategias"""
        strategies = {}
        strategies_path = Path(config_manager.config_root) / "strategies"
        
        for strategy_type_dir in strategies_path.iterdir():
            if strategy_type_dir.is_dir():
                for strategy_file in strategy_type_dir.glob("*.yaml"):
                    strategy_name = strategy_file.stem
                    try:
                        strategy_config = config_manager.get_strategy_config(
                            strategy_name, strategy_type_dir.name
                        )
                        strategies[f"{strategy_name}_{strategy_type_dir.name}"] = asdict(strategy_config)
                    except Exception as e:
                        print(f"Error loading strategy {strategy_name}: {e}")
        
        return strategies
    
    def _load_all_metrics(self, config_manager) -> Dict[str, Dict]:
        """Carga todas las configuraciones de métricas"""
        metrics = {}
        metrics_path = Path(config_manager.config_root) / "metrics"
        
        for metrics_file in metrics_path.glob("*.yaml"):
            metrics_name = metrics_file.stem
            try:
                metrics_config = config_manager.get_metrics_config(metrics_name)
                metrics[metrics_name] = metrics_config
            except Exception as e:
                print(f"Error loading metrics {metrics_name}: {e}")
        
        return metrics
    
    def upsert_broker(self, name: str, config: Dict[str, Any]):
        """Inserta o actualiza configuración de broker"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO brokers (name, type, enabled, config, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (name, config.get('type', 'unknown'), config.get('enabled', True), json.dumps(config)))
        
        self.conn.commit()
    
    def upsert_asset(self, broker_id: int, asset_config):
        """Inserta o actualiza configuración de activo"""
        cursor = self.conn.cursor()
        
        config_dict = asdict(asset_config) if hasattr(asset_config, '__dict__') else asset_config
        
        cursor.execute("""
            INSERT OR REPLACE INTO assets (broker_id, symbol, asset_type, enabled, config, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (broker_id, config_dict['symbol'], config_dict['asset_type'], True, json.dumps(config_dict)))
        
        self.conn.commit()
    
    def upsert_strategy(self, name: str, config: Dict[str, Any]):
        """Inserta o actualiza configuración de estrategia"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO strategies (name, type, version, enabled, config, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (name, config.get('type', 'unknown'), config.get('version', '1.0.0'), 
              config.get('enabled', True), json.dumps(config)))
        
        self.conn.commit()
    
    def upsert_metrics(self, name: str, config: Dict[str, Any]):
        """Inserta o actualiza configuración de métricas"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO metrics (name, type, enabled, config, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (name, 'metrics', True, json.dumps(config)))
        
        self.conn.commit()
    
    def get_broker_id(self, broker_name: str) -> Optional[int]:
        """Obtiene ID del broker por nombre"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM brokers WHERE name = ?", (broker_name,))
        result = cursor.fetchone()
        return result[0] if result else None
    
    def get_active_assets(self, broker_name: str = None) -> List[Dict]:
        """Obtiene activos activos, opcionalmente filtrados por broker"""
        cursor = self.conn.cursor()
        
        if broker_name:
            cursor.execute("""
                SELECT a.*, b.name as broker_name 
                FROM assets a 
                JOIN brokers b ON a.broker_id = b.id 
                WHERE a.enabled = 1 AND b.name = ?
            """, (broker_name,))
        else:
            cursor.execute("""
                SELECT a.*, b.name as broker_name 
                FROM assets a 
                JOIN brokers b ON a.broker_id = b.id 
                WHERE a.enabled = 1
            """)
        
        results = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        
        return [dict(zip(columns, row)) for row in results]
    
    def get_asset_config(self, broker_name: str, symbol: str) -> Optional[Dict]:
        """Obtiene configuración específica de un activo"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT a.config 
            FROM assets a 
            JOIN brokers b ON a.broker_id = b.id 
            WHERE b.name = ? AND a.symbol = ?
        """, (broker_name, symbol))
        
        result = cursor.fetchone()
        return json.loads(result[0]) if result else None
    
    def update_asset_config(self, broker_name: str, symbol: str, config_updates: Dict[str, Any]):
        """Actualiza configuración de un activo específico"""
        current_config = self.get_asset_config(broker_name, symbol)
        if current_config:
            # Merge configurations
            updated_config = {**current_config, **config_updates}
            
            cursor = self.conn.cursor()
            cursor.execute("""
                UPDATE assets 
                SET config = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id IN (
                    SELECT a.id 
                    FROM assets a 
                    JOIN brokers b ON a.broker_id = b.id 
                    WHERE b.name = ? AND a.symbol = ?
                )
            """, (json.dumps(updated_config), broker_name, symbol))
            
            self.conn.commit()
            return True
        return False
    
    def close(self):
        """Cierra la conexión a la base de datos"""
        if self.conn:
            self.conn.close()

# Clase para gestión híbrida (YAML + DB)
class HybridConfigManager:
    """Gestor híbrido que puede usar YAML o base de datos"""
    
    def __init__(self, config_root: str = "config", use_database: bool = False):
        self.config_root = config_root
        self.use_database = use_database
        
        if use_database:
            self.db = ConfigDatabase()
            self.yaml_manager = ConfigManager(config_root)
            # Migrar datos si es necesario
            self._ensure_migration()
        else:
            self.yaml_manager = ConfigManager(config_root)
            self.db = None
    
    def _ensure_migration(self):
        """Asegura que los datos YAML estén migrados a la base de datos"""
        # Verificar si hay datos en la base de datos
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM brokers")
        broker_count = cursor.fetchone()[0]
        
        if broker_count == 0:
            print("Base de datos vacía, iniciando migración...")
            self.db.migrate_from_yaml(self.yaml_manager)
    
    def get_asset_config(self, broker_name: str, symbol: str) -> Optional[Dict]:
        """Obtiene configuración de activo desde DB o YAML"""
        if self.use_database:
            return self.db.get_asset_config(broker_name, symbol)
        else:
            # Necesitamos determinar el tipo de activo - esto se puede mejorar
            # Por simplicidad, asumimos que existe en algún lugar
            for asset_type in ['forex', 'crypto', 'binary_options']:
                try:
                    return asdict(self.yaml_manager.get_asset_config(broker_name, asset_type, symbol))
                except:
                    continue
            return None
    
    def get_all_active_assets(self) -> List[Dict]:
        """Obtiene todos los activos activos"""
        if self.use_database:
            return self.db.get_active_assets()
        else:
            assets = self.yaml_manager.get_all_active_assets()
            return [asdict(asset) for asset in assets]
    
    def update_asset_config(self, broker_name: str, symbol: str, config_updates: Dict[str, Any]) -> bool:
        """Actualiza configuración de un activo"""
        if self.use_database:
            return self.db.update_asset_config(broker_name, symbol, config_updates)
        else:
            # Para YAML, necesitaríamos implementar la actualización del archivo
            print("Actualización de YAML no implementada aún")
            return False
    
    def switch_to_database(self):
        """Cambia de YAML a base de datos"""
        if not self.use_database:
            self.db = ConfigDatabase()
            self.db.migrate_from_yaml(self.yaml_manager)
            self.use_database = True
            print("Migración a base de datos completada")
    
    def export_to_yaml(self):
        """Exporta configuraciones de base de datos a YAML"""
        if self.use_database:
            # Implementar exportación si es necesario
            print("Exportación a YAML no implementada aún")
        else:
            print("Ya estás usando YAML")

# Ejemplo de uso
if __name__ == "__main__":
    # Modo YAML
    print("=== Modo YAML ===")
    yaml_manager = HybridConfigManager(use_database=False)
    
    assets = yaml_manager.get_all_active_assets()
    print(f"Activos encontrados: {len(assets)}")
    for asset in assets[:3]:  # Mostrar solo los primeros 3
        print(f"- {asset['symbol']} ({asset['broker']})")
    
    # Modo híbrido con base de datos
    print("\n=== Modo Base de Datos ===")
    db_manager = HybridConfigManager(use_database=True)
    
    db_assets = db_manager.get_all_active_assets()
    print(f"Activos en DB: {len(db_assets)}")
    
    # Actualizar configuración
    success = db_manager.update_asset_config("iqoption", "EURUSD", {"risk_level": "high"})
    print(f"Actualización exitosa: {success}")
    
    # Cerrar conexión
    if db_manager.db:
        db_manager.db.close()