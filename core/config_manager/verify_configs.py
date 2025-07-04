"""
Verificación de carga y acceso de configuraciones del sistema completo
Incluye brokers, assets, estrategias, riesgos y tick_normalizer
"""

from .config_manager import ConfigManager


def verify_all_configs():
    print("🔍 Verificando carga de todas las configuraciones...")
    config = ConfigManager()
    if not config.load_all_configurations():
        print("❌ Error al cargar configuraciones (load_all_configurations)")
        return False
    print("✅ Configuraciones cargadas correctamente")

    # Verificar brokers y activos validados por broker
    try:
        for broker in ["iqoption", "binance", "deriv", "mt5"]:
            broker_cfg = config.get_broker_config(broker)
            if broker_cfg is None:
                print(f"❌ Broker '{broker}' no encontrado")
            else:
                print(f"✅ Broker '{broker}' cargado")
                # Mostrar activos validados por categoría
                valid_assets = getattr(broker_cfg, 'valid_assets', {})
                for category, assets in valid_assets.items():
                    asset_names = [a.name for a in assets]
                    print(f"   • Activos válidos en '{category}': {asset_names if asset_names else 'Ninguno'}")
    except Exception as e:
        print(f"❌ Error accediendo a brokers/activos: {e}")

    # Verificar assets (ejemplo: forex_traditional/EURUSD)
    try:
        asset_cfg = config.get_asset_config("forex_traditional", "EURUSD")
        if asset_cfg is None:
            print("❌ Asset 'forex_traditional/EURUSD' no encontrado")
        else:
            print("✅ Asset 'forex_traditional/EURUSD' cargado")
    except Exception as e:
        print(f"❌ Error accediendo a assets: {e}")

    # Verificar estrategias (ejemplo: forex_traditional/prediction_force)
    try:
        strat_cfg = config.get_strategy_config("forex_traditional", "prediction_force")
        if strat_cfg is None:
            print("❌ Estrategia 'forex_traditional/prediction_force' no encontrada")
        else:
            print("✅ Estrategia 'forex_traditional/prediction_force' cargada")
    except Exception as e:
        print(f"❌ Error accediendo a estrategias: {e}")

    # Verificar riesgos (ejemplo: default)
    try:
        risk_cfg = config.get_risk_config("default")
        if risk_cfg is None:
            print("❌ Configuración de riesgo 'default' no encontrada")
        else:
            print("✅ Configuración de riesgo 'default' cargada")
    except Exception as e:
        print(f"❌ Error accediendo a riesgos: {e}")

    # Verificar tick_normalizer dentro de brokers
    try:
        broker_cfg = config.get_broker_config("iqoption")
        if broker_cfg and hasattr(broker_cfg, "tick_normalizer"):
            print("✅ tick_normalizer presente en broker 'iqoption'")
        else:
            print("❌ tick_normalizer no presente en broker 'iqoption'")
    except Exception as e:
        print(f"❌ Error accediendo a tick_normalizer: {e}")

    print("\n🎉 Verificación de configuraciones finalizada.")
    return True


if __name__ == "__main__":
    verify_all_configs()
