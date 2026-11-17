# -*- coding: utf-8 -*-
"""
Автотест веб-бота «IT-помощник лицея №37»
Сравнивает фактический результат detect_service / recognize_intent с эталоном.
Запуск: python test_bot.py
"""

import sys

try:
    import app as bot
except Exception as e:
    print(f"❌ Не удалось импортировать app.py: {e}")
    sys.exit(1)


# ─── Тест-кейсы для маршрутизации по службам ───
ROUTE_TESTS = [
    # (запрос, ожидаемая служба)
    ("сломался стул в 305 кабинете",              "плотник"),
    ("не закрывается дверь в кабинете 12",         "плотник"),
    ("шатается парта в 4 классе",                  "плотник"),
    ("сломалась полка в шкафу",                    "плотник"),
    ("не работает компьютер в 204",                "it"),
    ("зависает проектор",                          "it"),
    ("не печатает принтер",                        "it"),
    ("не могу войти в электронный журнал",         "it"),
    ("не работает интернет в кабинете 18",         "it"),
    ("пропал пароль от журнала",                   "it"),
    ("не пришла зарплата за октябрь",              "бухгалтерия"),
    ("как получить справку о доходах",             "бухгалтерия"),
    ("нужна квитанция на оплату",                  "бухгалтерия"),
    ("где моя компенсация",                        "бухгалтерия"),
    ("хочу перевести ребёнка в другой класс",      "администрация"),
    ("хочу пожаловаться на учителя",               "администрация"),
    ("как написать заявление на отпуск",           "администрация"),
    ("где найти директора",                        "администрация"),
]

# ─── Тест-кейсы для обычных интентов ───
INTENT_TESTS = [
    # (запрос, ожидаемый tag)
    ("привет",                                     "greeting"),
    ("здравствуйте",                               "greeting"),
    ("добрый день",                                "greeting"),
    ("забыл пароль от журнала",                    "password"),
    ("как сбросить пароль",                        "password"),
    ("не включается компьютер",                    "computer"),
    ("контакты",                                   "contacts"),
    ("где вы находитесь",                          "contacts"),
    ("расписание звонков",                         "schedule"),
    ("где сайт лицея",                             "site"),
    ("моя школа не работает",                      "my_school"),
    ("спасибо",                                    "thanks"),
    ("пока",                                       "goodbye"),
]

# ─── Тест-кейсы для fallback (бот НЕ должен распознавать) ───
FALLBACK_TESTS = [
    "абракадабра",
    "фывапролдж",
    "ааааааа",
]


def run_tests():
    total, passed = 0, 0
    print("=" * 72)
    print("ТЕСТ 1: Маршрутизация по службам (detect_service)")
    print("=" * 72)
    for query, expected in ROUTE_TESTS:
        total += 1
        det = bot.detect_service(query)
        actual = det[0] if det else None
        ok = actual == expected
        passed += ok
        mark = "✅ OK  " if ok else "❌ FAIL"
        print(f"{mark} | «{query}»")
        print(f"        Ожидалось: {expected:15} | Получено: {str(actual):15}")
    print()

    print("=" * 72)
    print("ТЕСТ 2: Обычные интенты (recognize_intent)")
    print("=" * 72)
    for query, expected in INTENT_TESTS:
        total += 1
        intent = bot.recognize_intent(query)
        actual = intent["tag"] if intent else None
        ok = actual == expected
        passed += ok
        mark = "✅ OK  " if ok else "❌ FAIL"
        print(f"{mark} | «{query}»")
        print(f"        Ожидалось: {expected:15} | Получено: {str(actual):15}")
    print()

    print("=" * 72)
    print("ТЕСТ 3: Fallback (бот не должен распознавать)")
    print("=" * 72)
    for query in FALLBACK_TESTS:
        total += 1
        intent = bot.recognize_intent(query)
        det = bot.detect_service(query)
        ok = (intent is None) and (det is None)
        passed += ok
        mark = "✅ OK  " if ok else "❌ FAIL"
        print(f"{mark} | «{query}»")
        print(f"        Ожидалось: None            | Интент: {str(intent['tag'] if intent else None):15} | Служба: {str(det[0] if det else None)}")
    print()

    print("=" * 72)
    print(f"ИТОГО: {passed} из {total} пройдено ({passed / total * 100:.1f}%)")
    print("=" * 72)
    return passed == total


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)