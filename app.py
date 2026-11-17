# -*- coding: utf-8 -*-
"""
Веб-бот «IT-помощник лицея №37»
Flask + NLTK + маршрутизация по службам + админ-режим
"""

import json
import re
import csv
import os
from datetime import datetime
from difflib import SequenceMatcher

import nltk
from nltk.stem.snowball import SnowballStemmer
from flask import Flask, render_template, request, jsonify

for pkg in ("punkt", "punkt_tab"):
    try:
        nltk.download(pkg, quiet=True)
    except Exception:
        pass

STEMMER = SnowballStemmer("russian")

INTENTS_FILE = "intents.json"
REQUESTS_FILE = "requests.csv"

ADMIN_PASSWORD = "aaadir37@"
ADMIN_COMMAND = "администратор"
app = Flask(__name__)

with open(INTENTS_FILE, "r", encoding="utf-8") as f:
    INTENTS = json.load(f)["intents"]
# ─── Справочник служб ───
# ─── Справочник служб ───
# ─── Справочник служб ───
SERVICES = {
    "плотник": {
        "name": "Плотник",
        "cabinet": "103",
        "topics": ["мебель", "стол", "стул", "дверь", "замок", "полка", "окно", "парта", "шкаф", "ручка", "петля", "сломал", "шатается", "скрип", "сломался", "сломалось", "починить"],
        "hint": "мебель, двери, замки, полки, окна"
    },
    "it": {
        "name": "Технический специалист (IT)",
        "cabinet": "204",
        "topics": ["компьютер", "пк", "ноутбук", "проектор", "принтер", "сканер", "панель", "сеть", "интернет", "журнал", "пароль", "программа", "монитор", "клавиатура", "мышь", "экран", "кабель", "зависает", "тормозит", "включается"],
        "hint": "компьютеры, проекторы, принтеры, сеть, электронный журнал"
    },
    "бухгалтерия": {
        "name": "Бухгалтерия",
        "cabinet": "207",
        "topics": ["зарплата", "зарплату", "аванс", "справка", "налог", "оплата", "квитанция", "компенсация", "выплата", "ндфл", "расчет", "бухгалтер", "деньги", "доход", "пришла", "пришел", "перевод"],
        "hint": "зарплата, справки, выплаты, налоги"
    },
    "администрация": {
        "name": "Администрация",
        "cabinet": "101",
        "topics": ["директор", "завуч", "жалоба", "пожаловаться", "конфликт", "перевод", "перевести", "прием", "отпуск", "документ", "приказ", "заявление", "администрация", "устав", "правила", "ребенок", "ребёнка", "учитель", "учителя", "класс"],
        "hint": "директор, завуч, жалобы, перевод, документы, отпуск"
    }
}


def normalize(text: str) -> str:
    text = text.lower().replace("ё", "е")
    text = re.sub(r"[^а-яa-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tokenize(text: str) -> list:
    tokens = nltk.word_tokenize(normalize(text))
    return [STEMMER.stem(t) for t in tokens if t.strip()]


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def recognize_intent(user_text: str):
    user_tokens = tokenize(user_text)
    if not user_tokens:
        return None
    user_set = set(user_tokens)
    best_intent, best_score = None, 0.0
    for intent in INTENTS:
        for pattern in intent["patterns"]:
            pat_tokens = tokenize(pattern)
            if not pat_tokens:
                continue
            pat_set = set(pat_tokens)
            if pat_set.issubset(user_set):
                score = 1.0
            else:
                inter = pat_set & user_set
                score = 0.7 * (len(inter) / len(pat_set)) + 0.3 * (len(inter) / len(user_set))
                pat_str, user_str = " ".join(pat_tokens), " ".join(user_tokens)
                if len(pat_str) >= 4 and len(user_str) >= 4:
                    fuzzy = similarity(pat_str, user_str)
                    if fuzzy >= 0.8:
                        score = max(score, fuzzy)
            if score > best_score:
                best_score, best_intent = score, intent
    return best_intent if best_score >= 0.55 else None


# ─── Маршрутизация по службам ───
def detect_service(user_text: str):
    """
    Возвращает (key, service_dict, score) или None.
    Считает пересечение стемов запроса с темами каждой службы.
    """
    user_tokens = set(tokenize(user_text))
    if not user_tokens:
        return None
    best_key, best_score = None, 0.0
    for key, svc in SERVICES.items():
        topic_tokens = set()
        for t in svc["topics"]:
            topic_tokens |= set(tokenize(t))

        inter = user_tokens & topic_tokens
        if not inter:
            continue

        # МЕНЯЕМ ФОРМУЛУ: считаем долю слов ЗАПРОСА, которые попали в тему
        score = len(inter) / len(user_tokens)

        if score > best_score:
            best_score, best_key = score, key

    # Понижаем порог до 0.1 (достаточно одного совпадения)
    if best_key and best_score >= 0.1:
        return best_key, SERVICES[best_key], best_score
    return None


def service_answer(user_text: str):
    """Формирует ответ с направлением к службе + альтернатива заявки."""
    det = detect_service(user_text)
    if not det:
        return None
    key, svc, score = det
    text = (f"По вашему вопросу рекомендуем обратиться: {svc['name']}, кабинет {svc['cabinet']}.\n"
            f"Этот кабинет занимается: {svc['hint']}.\n\n"
            f"Если хотите, я могу оформить заявку — напишите «заявка». "
            f"Или уточните вопрос, и я подскажу подробнее.")
    return text, key


# ─── Заявки ───
def ensure_csv():
    if not os.path.exists(REQUESTS_FILE):
        with open(REQUESTS_FILE, "w", newline="", encoding="utf-8") as f:
            csv.writer(f, delimiter=";").writerow(["Дата", "ФИО", "Кабинет", "Проблема", "Статус", "Служба"])


def read_all_rows() -> list:
    ensure_csv()
    with open(REQUESTS_FILE, "r", encoding="utf-8") as f:
        return [{"id": i, **row} for i, row in enumerate(csv.DictReader(f, delimiter=";"), start=1)]


def save_request(fio: str, cabinet: str, problem: str, service: str = "—") -> int:
    ensure_csv()
    rows = read_all_rows()
    num = len(rows) + 1
    with open(REQUESTS_FILE, "a", newline="", encoding="utf-8") as f:
        csv.writer(f, delimiter=";").writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M"), fio, cabinet, problem, "Новая", service
        ])
    return num


def parse_request(text: str):
    parts = [p.strip() for p in text.split(",")]
    if len(parts) >= 3 and parts[0] and parts[1] and parts[2]:
        return parts[0], parts[1], ", ".join(parts[2:])
    return None


def format_rows(rows: list, title: str) -> str:
    if not rows:
        return f"{title}: пусто."
    lines = [f"{title}:"]
    for r in rows:
        mark = "✔" if r.get("Статус") == "Выполнена" else "•"
        svc = r.get("Служба", "—")
        lines.append(f"{mark} {r['id']}. [{r['Дата']}] {r['ФИО']}, {r['Кабинет']} — {r['Проблема']} "
                     f"(служба: {svc}, статус: {r.get('Статус', '—')})")
    return "\n".join(lines)


def mark_done(rid: int) -> bool:
    rows = read_all_rows()
    if rid < 1 or rid > len(rows) or rows[rid - 1]["Статус"] == "Выполнена":
        return False
    rows[rid - 1]["Статус"] = "Выполнена"
    _write_rows(rows)
    return True


def delete_row(rid: int) -> bool:
    rows = read_all_rows()
    if rid < 1 or rid > len(rows):
        return False
    rows.pop(rid - 1)
    _write_rows(rows)
    return True


def _write_rows(rows: list):
    with open(REQUESTS_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(["Дата", "ФИО", "Кабинет", "Проблема", "Статус", "Служба"])
        for r in rows:
            writer.writerow([r["Дата"], r["ФИО"], r["Кабинет"], r["Проблема"], r["Статус"], r.get("Служба", "—")])


# ─── Админ-команды ───
def handle_admin_command(text: str):
    t = normalize(text)
    if re.search(r"\b(все|всё|покажи все|список всех)\b", t) and not re.search(r"выполн|невыполн|активн", t):
        return format_rows(read_all_rows(), "Все заявки"), True
    if re.search(r"выполнен|сделан|закрыт|готов", t) and not re.search(r"выполн\w*\s+\d", t):
        rows = [r for r in read_all_rows() if r["Статус"] == "Выполнена"]
        return format_rows(rows, "Выполненные заявки"), True
    if re.search(r"активн|невыполн|не выполнен|в работе|ожида|нов", t):
        rows = [r for r in read_all_rows() if r["Статус"] != "Выполнена"]
        return format_rows(rows, "Активные заявки"), True
    m = re.search(r"выполн\w*\s+(\d+)|отмет\w*\s+(?:как\s+)?выполн\w*\s+(\d+)|сдела\w*\s+(\d+)", t)
    if m:
        rid = int(next(g for g in m.groups() if g))
        ok = mark_done(rid)
        rows = [r for r in read_all_rows() if r["Статус"] != "Выполнена"]
        msg = f"Заявка №{rid} отмечена выполненной." if ok else f"Заявка №{rid} не найдена или уже выполнена."
        return msg + "\n\n" + format_rows(rows, "Активные заявки"), True
    m = re.search(r"(?:удал|сотр|убери|убрать|стереть)\w*\s+(?:заявк\w*\s*)?(\d+)", t)
    if m:
        rid = int(m.group(1))
        ok = delete_row(rid)
        msg = f"Заявка №{rid} удалена." if ok else f"Заявка №{rid} не найдена."
        return msg + "\n\n" + format_rows(read_all_rows(), "Все заявки"), True
    if re.search(r"заявк", t) and re.search(r"покаж|список|вывед|посмотр", t):
        return format_rows(read_all_rows(), "Все заявки"), True
    return None


# ─── Маршруты ───
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/get_response", methods=["POST"])
def get_response():
    data = request.get_json(silent=True) or {}
    user_message = (data.get("message") or "").strip()
    if not user_message:
        return jsonify({"response": "Пустое сообщение.", "tag": "empty"})

    low = normalize(user_message)

    # админ-вход
    if low.startswith(ADMIN_COMMAND):
        pwd = user_message[len(user_message.split()[0]):].strip()
        if pwd == ADMIN_PASSWORD:
            return jsonify({
                "response": "Админ-режим включён. Команды: «все заявки», «активные», "
                            "«выполненные», «выполнено N», «удалить N», «выход».",
                "tag": "admin_on", "admin": True
            })
        return jsonify({"response": "Неверный пароль администратора.", "tag": "admin_fail", "admin": False})

    if low in ("выход", "выйти", "выйти из админа", "админ выход", "стоп админ"):
        return jsonify({"response": "Админ-режим выключен.", "tag": "admin_off", "admin": False})

    admin_res = handle_admin_command(user_message)
    if admin_res:
        text, is_admin = admin_res
        return jsonify({"response": text, "tag": "admin_cmd", "admin": is_admin})

    # 1) явная команда «заявка» → режим заявки
    if re.search(r"\bзаявк", low) and re.search(r"остав|подать|создать|оформ|нужна|хочу", low):
        return jsonify({
            "response": "Оформляем заявку. Напишите: ФИО, кабинет, описание проблемы.\n"
                        "Пример: Иванова А.П., каб. 305, не работает проектор.",
            "tag": "request"
        })

    # 2) маршрутизация по службам (контекст)
    svc_res = service_answer(user_message)
    if svc_res:
        text, key = svc_res
        return jsonify({"response": text, "tag": f"route_{key}"})

    # 3) обычные интенты
    intent = recognize_intent(user_message)
    if intent:
        return jsonify({"response": intent["responses"][0], "tag": intent["tag"]})

    # 4) fallback со списком служб
    hint = "\n".join(f"• {s['name']} — каб. {s['cabinet']} ({s['hint']})" for s in SERVICES.values())
    return jsonify({
        "response": "Не совсем понял, о чём речь. Могу направить вас в нужную службу:\n"
                    f"{hint}\n\nОпишите проблему подробнее или напишите «заявка».",
        "tag": "fallback"
    })


@app.route("/submit_request", methods=["POST"])
def submit_request():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    parsed = parse_request(text)
    if not parsed:
        return jsonify({"ok": False, "response": "Формат: ФИО, кабинет, описание проблемы."})
    fio, cabinet, problem = parsed
    det = detect_service(problem)
    service = SERVICES[det[0]]["name"] if det else "—"
    num = save_request(fio, cabinet, problem, service)
    return jsonify({
        "ok": True,
        "response": f"Заявка №{num} принята: {fio}, {cabinet}. Служба: {service}."
    })


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)