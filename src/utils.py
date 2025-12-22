import logging
import sys
import io
import os
import yaml

def setup_logging(log_dir="logs"):
    log_dir = str(log_dir) # Ensure it's a string if passed as Path
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Windows console encoding fix
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(os.path.join(log_dir, "app.log"), encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

def load_config(config_path="config/config.yaml"):
    if not os.path.exists(config_path):
        logging.error(f"Config file not found: {config_path}")
        sys.exit(1)
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)
