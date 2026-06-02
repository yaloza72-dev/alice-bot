# -*- coding: utf-8 -*-
"""
Webhook для навыка Яндекс Алисы — управление ботом автопостинга через голос.
Команды:
  - "покажи заявки"      → статистика постов в Telegram
  - "запусти публикацию" → запускает autoposting скрипт
  - "отправь сообщение"  → отправляет сообщение в TG канал
  - "статус / отчёт"     → сводка о последних публикациях
"""

import os, subprocess, requests
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

# ── Настройки ────────────────────────────────────────────────────────────────
TG_TOKEN      = "8556165985:AAGOkZqJbSfUNMkh5EFa4BA8v5KE7M6upag"
TG_CHANNEL_ID = "-1001470617712"
AUTOPOST_DIR  = r"C:\Users\user\Desktop\Скрипты\autoposting"

def tg_send(text: str) -> bool:
    r = requests.post(
        f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
        json={"chat_id": TG_CHANNEL_ID, "text": text},
        timeout=10
    )
    return r.ok

def tg_get_updates() -> list:
    r = requests.get(
        f"https://api.telegram.org/bot{TG_TOKEN}/getUpdates",
        params={"limit": 10, "offset": -10},
        timeout=10
    )
    if r.ok:
        return r.json().get("result", [])
    return []

def run_autopost(slot: str = "morning") -> str:
    try:
        result = subprocess.run(
            ["python", "event_main.py", "--slot", slot],
            cwd=AUTOPOST_DIR,
            capture_output=True, text=True, timeout=120
        )
        if "ГОТОВО" in result.stdout:
            return "Публикация успешно запущена"
        return "Публикация запущена, проверь результат"
    except Exception as e:
        return f"Ошибка запуска: {e}"

def parse_command(text: str) -> tuple[str, str]:
    """Возвращает (команда, параметр)"""
    t = text.lower().strip()

    if any(w in t for w in ["заявк", "запрос", "обращени"]):
        return "заявки", ""

    if any(w in t for w in ["публикац", "пост", "запусти", "опубликуй"]):
        slot = "evening" if any(w in t for w in ["вечер", "ночь"]) else "morning"
        return "публикация", slot

    if any(w in t for w in ["отправь", "напиши", "сообщени"]):
        # Ищем текст после ключевого слова
        for kw in ["отправь", "напиши", "сообщение"]:
            if kw in t:
                msg = t.split(kw, 1)[-1].strip()
                return "сообщение", msg
        return "сообщение", ""

    if any(w in t for w in ["статус", "отчёт", "отчет", "как дела", "что нового"]):
        return "статус", ""

    return "неизвестно", text

def build_response(text: str, end_session: bool = False) -> dict:
    return {
        "version": "1.0",
        "response": {
            "text": text,
            "tts": text,
            "end_session": end_session
        }
    }

# ── Основной webhook ─────────────────────────────────────────────────────────
@app.route("/alice", methods=["POST"])
def alice():
    body = request.get_json(force=True)

    # Приветствие при первом запуске
    if body.get("session", {}).get("new"):
        return jsonify(build_response(
            "Привет! Я управляю ботом автопостинга. "
            "Скажи: покажи заявки, запусти публикацию, статус или отправь сообщение."
        ))

    user_text = body.get("request", {}).get("original_utterance", "")
    command, param = parse_command(user_text)

    # ── Заявки ───────────────────────────────────────────────────────────────
    if command == "заявки":
        updates = tg_get_updates()
        count = len([u for u in updates if "message" in u])
        now = datetime.now().strftime("%d.%m в %H:%M")
        reply = f"На {now} получено обновлений: {count}. Канал активен."
        return jsonify(build_response(reply))

    # ── Запустить публикацию ──────────────────────────────────────────────────
    elif command == "публикация":
        slot_name = "вечернюю" if param == "evening" else "утреннюю"
        reply_start = build_response(f"Запускаю {slot_name} публикацию, подожди немного.")
        result = run_autopost(param)
        return jsonify(build_response(result))

    # ── Отправить сообщение ───────────────────────────────────────────────────
    elif command == "сообщение":
        if not param:
            return jsonify(build_response(
                "Что именно отправить? Скажи, например: отправь сообщение — сегодня акция."
            ))
        ok = tg_send(f"📢 {param}")
        if ok:
            return jsonify(build_response(f"Отправила в канал: {param}"))
        return jsonify(build_response("Не удалось отправить сообщение, проверь соединение."))

    # ── Статус ────────────────────────────────────────────────────────────────
    elif command == "статус":
        now = datetime.now()
        hour = now.hour
        if 6 <= hour < 12:
            time_of_day = "утро"
        elif 12 <= hour < 18:
            time_of_day = "день"
        else:
            time_of_day = "вечер"

        reply = (
            f"Добрый {time_of_day}! "
            f"Сегодня {now.strftime('%d %B')}. "
            "Бот автопостинга работает. "
            "Расписание: утренняя публикация в 10 утра, вечерняя в 7 вечера."
        )
        return jsonify(build_response(reply))

    # ── Не понял ──────────────────────────────────────────────────────────────
    else:
        return jsonify(build_response(
            "Не поняла команду. Скажи: покажи заявки, запусти публикацию, "
            "статус или отправь сообщение."
        ))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
