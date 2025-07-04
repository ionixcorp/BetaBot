"""
Verificación de Configuraciones del Tick Normalizer
Bet-AG Trading System - Verificación de configuraciones YAML
"""

from pathlib import Path
from typing import Any, Dict, List  # noqa: F401

import yaml


def verify_tick_normalizer_configs():
    """Verifica que todas las configuraciones del tick_normalizer estén completas."""
    
    # Estructura esperada actualizada según los YAML reales
    expected_sections = {
        'data_quality': [
            'min_quality_score',
            'duplicate_detection',
            'duplicate_window_seconds'
        ],
        'latency_compensation': [
            'enabled',
            'method',
            'fixed_latency_ms',
            'min_latency_ms',
            'max_latency_ms',
            'confidence_threshold',
            'measurement_window_size'
        ],
        'validation': [
            'price_positive',
            'volume_non_negative',
            'timestamp_validation',
            'sequence_validation'
        ],
        'anomaly_detection': [
            'enabled',
            'price_sigma_threshold',
            'volume_sigma_threshold',
            'window_size',
            'min_samples'
        ],
        'performance': [
            'buffer_size',
            'batch_size',
            'max_latency_ms',
            'processing_threads',
            'queue_max_size'
        ],
        'logging': [
            'log_level',
            'log_raw_data',
            'log_normalized_ticks',
            'log_validation_details',
            'log_latency_measurements'
        ]
    }
    
    # Ruta a los archivos de configuración
    config_path = Path(__file__).parent.parent.parent / "config" / "brokers"
    
    print("🔍 Verificando configuraciones del tick_normalizer...")
    print("=" * 60)
    
    all_valid = True
    
    for yaml_file in config_path.glob("*.yaml"):
        broker_name = yaml_file.stem
        print(f"\n📊 Verificando {broker_name.upper()}:")
        
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            tick_normalizer = config_data.get('tick_normalizer', {})
            
            if not tick_normalizer:
                print("  ❌ No se encontró sección tick_normalizer")
                all_valid = False
                continue
            
            # Verificar cada sección
            for section_name, expected_fields in expected_sections.items():
                section = tick_normalizer.get(section_name, {})
                
                if not section:
                    print(f"  ❌ Sección '{section_name}' faltante")
                    all_valid = False
                    continue
                
                missing_fields = []
                for field in expected_fields:
                    if field not in section:
                        missing_fields.append(field)
                
                if missing_fields:
                    print(f"  ⚠️  Sección '{section_name}': campos faltantes: {missing_fields}")
                    all_valid = False
                else:
                    print(f"  ✅ Sección '{section_name}': completa")
            
            # Verificar valores específicos
            data_quality = tick_normalizer.get('data_quality', {})
            if data_quality:
                min_quality = data_quality.get('min_quality_score')
                if min_quality is not None and (min_quality < 0 or min_quality > 1):
                    print(f"  ⚠️  min_quality_score debe estar entre 0 y 1, actual: {min_quality}")
                    all_valid = False
                
                max_spread = data_quality.get('max_spread_percentage')
                if max_spread is not None and max_spread <= 0:
                    print(f"  ⚠️  max_spread_percentage debe ser positivo, actual: {max_spread}")
                    all_valid = False
            
            print(f"  📋 Resumen: {'✅ Válido' if all_valid else '❌ Con problemas'}")
            
        except Exception as e:
            print(f"  ❌ Error al leer {yaml_file}: {e}")
            all_valid = False
    
    print("\n" + "=" * 60)
    if all_valid:
        print("🎉 ¡Todas las configuraciones están completas y válidas!")
    else:
        print("⚠️  Se encontraron problemas en algunas configuraciones")
    
    return all_valid


def show_config_summary():
    """Muestra un resumen de las configuraciones de cada broker."""
    
    config_path = Path(__file__).parent.parent.parent / "config" / "brokers"
    
    print("\n📋 Resumen de Configuraciones por Broker:")
    print("=" * 60)
    
    for yaml_file in config_path.glob("*.yaml"):
        broker_name = yaml_file.stem
        
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            tick_normalizer = config_data.get('tick_normalizer', {})
            data_quality = tick_normalizer.get('data_quality', {})
            performance = tick_normalizer.get('performance', {})
            
            print(f"\n🔹 {broker_name.upper()}:")
            print(f"   • Quality Score: {data_quality.get('min_quality_score', 'N/A')}")
            print(f"   • Max Spread: {data_quality.get('max_spread_percentage', 'N/A')}%")
            print(f"   • Max Age: {data_quality.get('max_age_seconds', 'N/A')}s")
            print(f"   • Buffer Size: {performance.get('buffer_size', 'N/A')}")
            print(f"   • Processing Threads: {performance.get('processing_threads', 'N/A')}")
            
        except Exception as e:
            print(f"  ❌ Error al leer {yaml_file}: {e}")


if __name__ == "__main__":
    verify_tick_normalizer_configs()
    show_config_summary()