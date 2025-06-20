import logging
import os
from pathlib import Path

# Папка для логов (создаем, если её нет)
log_dir = Path(__file__).parent
log_file = log_dir / "reception.log"

if not log_dir.exists():
    log_dir.mkdir(parents=True, exist_ok=True)

# Настройка логирования (единая для всего проекта)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
)

# Глобальный логгер для импорта в других модулях
my_logging = logging.getLogger(__name__)