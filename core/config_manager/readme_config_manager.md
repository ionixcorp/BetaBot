# Módulo Config Manager

## 1. Archivos y Responsabilidades

| Archivo | Responsabilidad |
|---------|-----------------|
| `config_manager.py` | Punto de entrada principal que coordina todos los gestores de configuración |
| `broker_manager.py` | Gestiona configuraciones de brokers (IQ Option, Binance, etc.) |
| `asset_manager.py` | Maneja configuraciones de activos (forex, criptomonedas, etc.) |
| `strategy_manager.py` | Administra configuraciones de estrategias de trading |
| `risk_manager.py` | Gestiona parámetros de gestión de riesgo |
| `validation.py` | Proporciona validación para todas las configuraciones |
| `__init__.py` | Inicialización del paquete |

## 2. Relación entre Archivos

```
config_manager.py
    ├──> broker_manager.py
    ├──> asset_manager.py
    ├──> strategy_manager.py
    ├──> risk_manager.py
    └──> validation.py
```

## 3. Entradas por Archivo

### config_manager.py
- **Entrada**: Ruta al directorio de configuración (opcional)
- **Procesa**: Directorio raíz de configuración

### broker_manager.py
- **Entrada**: `brokers/` (directorio)
- **Procesa**: Archivos YAML de configuración de brokers

### asset_manager.py
- **Entrada**: `assets/` (directorio)
- **Procesa**: Archivos YAML de configuración de activos

### strategy_manager.py
- **Entrada**: `strategies/` (directorio)
- **Procesa**: Archivos YAML de configuración de estrategias

### risk_manager.py
- **Entrada**: `risk_management/` (directorio)
- **Procesa**: Archivos YAML de parámetros de riesgo

### validation.py
- **Entrada**: Objetos de configuración
- **Procesa**: Validación de estructura y valores

## 4. Salidas por Archivo

### config_manager.py
- **Salida**: Objeto `ConfigManager` con acceso unificado a todas las configuraciones

### broker_manager.py
- **Salida**: Diccionario de objetos `BrokerConfig` indexados por nombre de broker

### asset_manager.py
- **Salida**: Diccionario anidado `{categoría: {nombre_asset: AssetConfig}}`

### strategy_manager.py
- **Salida**: Diccionario anidado `{categoría: {nombre_estrategia: StrategyConfig}}`

### risk_manager.py
- **Salida**: Diccionario de objetos `RiskConfig` indexados por nombre de configuración

### validation.py
- **Salida**: Objetos `ValidationResult` con resultados de validación

## 5. Punto de Entrada

`config_manager.py` es el punto de entrada principal a través de la clase `ConfigManager`.

## 6. Módulos que Importan ConfigManager

- Módulos principales del sistema
- Motores de trading
- Backtesting
- Interfaces de usuario
- Herramientas de monitoreo

## 7. Validación de Configuraciones

- **Dónde**: `validation.py`
- **Qué valida**:
  - Estructura de archivos YAML
  - Valores requeridos
  - Tipos de datos
  - Rangos y restricciones
  - Dependencias entre configuraciones

## 8. Componentes Reutilizables

- Clases base de configuración (`BrokerConfig`, `AssetConfig`, etc.)
- Sistema de validación (`ConfigValidator`)
- Utilidades de carga de YAML
- Manejo de errores estandarizado

## 9. Integrar Nueva Fuente de Configuración

1. Crear nuevo manager siguiendo el patrón existente
2. Implementar métodos de carga y validación
3. Registrar en `ConfigManager`
4. Agregar directorio correspondiente en `config/`

Ejemplo para nuevo módulo `backtesting`:

```python
# backtest_manager.py
class BacktestConfig:
    # Definir estructura de configuración

class BacktestManager:
    def __init__(self, config_path: Path):
        # Inicialización
    
    def load_configs(self) -> bool:
        # Lógica de carga
```

## 10. Interface de ConfigManager

```python
class ConfigManager:
    # Inicialización
    def __init__(self, config_path: Optional[str] = None)
    
    # Carga de configuraciones
    def load_all_configs() -> bool
    
    # Acceso a configuraciones
    def get_broker_config(broker_name: str) -> BrokerConfig
    def get_asset_config(category: str, asset_name: str) -> AssetConfig
    def get_strategy_config(category: str, strategy_name: str) -> StrategyConfig
    def get_risk_config(config_name: str) -> RiskConfig
    
    # Validación
    def validate_configs() -> bool
    
    # Recarga
    def reload_configs() -> bool
```

## 11. Uso desde Otros Módulos

### Inicialización
```python
from core.config_manager import ConfigManager

# Uso con ruta por defecto (config/)
config = ConfigManager()
config.load_all_configs()

# O con ruta personalizada
custom_config = ConfigManager("/ruta/a/mis/configs")
custom_config.load_all_configs()
```

### Obtener Configuración de Broker
```python
# Obtener configuración de IQ Option
iq_config = config.get_broker_config("iqoption")

# Acceder a parámetros
api_key = iq_config.auth.get("api_key")
account_type = iq_config.connection.get("account_type")
```

### Obtener Configuración de Activo
```python
# Obtener configuración de EUR/USD
eurusd = config.get_asset_config("forex_traditional", "EURUSD")

# Acceder a parámetros
digits = eurusd.parameters.get("digits")
lot_size = eurusd.parameters.get("lot_size")
```

### Obtener Configuración de Estrategia
```python
# Obtener configuración de estrategia
strategy_cfg = config.get_strategy_config("forex_traditional", "prediction_force")

# Acceder a parámetros
indicators = strategy_cfg.strategy_params.get("indicators")
timeframes = strategy_cfg.multi_timeframes.get("timeframes")
```

### Validar Configuraciones
```python
if not config.validate_configs():
    # Manejar error de configuración
    raise RuntimeError("Configuración inválida")
```

### Recargar Configuraciones
```python
if not config.reload_configs():
    # Manejar error de recarga
    logger.error("Error al recargar configuraciones")
```