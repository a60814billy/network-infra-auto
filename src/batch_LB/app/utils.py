from pathlib import Path
import yaml

def load_config() -> dict:
    """從 config.yaml 載入配置"""
    config_path = Path(__file__).parent.parent / "config.yaml"
    try:
        with open(config_path, 'r', encoding='utf-8') as file:
            return yaml.safe_load(file)
    except Exception as e:
        print(f"Error loading config.yaml: {e}")
        return {}