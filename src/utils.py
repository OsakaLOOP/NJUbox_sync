import logging
import logging.handlers
import sys
import io
import os
import yaml

def setup_logging(log_dir="logs", log_level="INFO", max_bytes=5*1024*1024, backup_count=3):
    log_dir = str(log_dir)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Windows console encoding fix
    if sys.platform == 'win32':
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        except AttributeError:
             # In case sys.stdout is replaced or doesn't have buffer (e.g. during tests)
            pass

    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Create handlers
    file_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, "app.log"),
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    stream_handler = logging.StreamHandler(sys.stdout)
    
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[file_handler, stream_handler]
    )

def load_config(config_path="config/config.yaml"):
    if not os.path.exists(config_path):
        # Fallback to print if logging isn't set up yet, or rely on implicit basicConfig
        print(f"Error: Config file not found: {config_path}", file=sys.stderr)
        sys.exit(1)
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)
