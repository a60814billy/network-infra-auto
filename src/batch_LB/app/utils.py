from pathlib import Path
import yaml

def load_device() -> dict:
    """從 device.yaml 載入配置"""
    config_path = Path(__file__).parent.parent / "device.yaml"
    try:
        with open(config_path, 'r', encoding='utf-8') as file:
            return yaml.safe_load(file)
    except Exception as e:
        print(f"Error loading device.yaml: {e}")
        return {}