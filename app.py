"""ArchCalc AI — учебный работающий прототип: Gemini API + проверенные вычисления."""
import json
import os
from pathlib import Path

import streamlit as st
from calculations import calculate, VALID_TASKS

BASE = Path(__file__).resolve().parent
KNOWLEDGE = json.loads((BASE / "knowledge_base.json").read_text(encoding="utf-8"))

st.set_page_config(page_title="ArchCalc AI", page_icon="📐", layout="centered")
st.title("📐 ArchCalc AI")
st.caption("Учебный ИИ-помощник по архитектурным расчётам · прототип КТ3")


def secret(key, default=""):
    try:
        return st.secrets.get(key, os.getenv(key, default))
    except (FileNotFoundError, KeyError):
        return os.getenv(key, default)
    except Exception:
        return os.getenv(key, default)

API_KEY = secret("GEMINI_API_KEY")
MODEL = secret("GEMINI_MODEL", "gemini-3.5-flash-lite")

st.info("Поддерживаемые расчёты: площадь, объём и перевод размеров в масштаб чертежа. Только прямоугольные помещения.")
if API_KEY:
    st.success(f"ИИ-подключение настроено · модель: {MODEL}")
else:
    st.warning("ИИ пока НЕ подключён: добавьте GEMINI_API_KEY в секреты. Ниже доступна только проверка точности формул вручную — она НЕ заменяет ИИ.")


def gemini_client():
    from google import genai
    return genai.Client(api_key=API_KEY)


def interpret_request(text):
    client = gemini_client()
    instructions = f"""Ты — маршрутизатор запросов учебного ArchCalc AI.\n
Справочник приложения: {json.dumps(KNOWLEDGE, ensure_ascii=False)}\n
Верни ТОЛЬКО один JSON объект без Markdown и без комментариев с ключами:
{{"tasks":["area","volume","scale"],"length_m":5,"width_m":4,"height_m":3,"scale_denominator":100}}
Правила:
- Определи из русского запроса реальные задачи из area, volume, scale. Включай только запрошенные действия.
- Переведи размеры в метры: 300 см -> 3 м, 4000 мм -> 4 м.
- Не придумывай размеры. Для неуказанного параметра верни null.
- Для масштаба 1:100 scale_denominator=100; если масштаб не указан, null.
- Пользователь может не указывать высоту, это допустимо для площади.
- Ни один другой вид задачи не поддерживается. Если запрос не подходит, верни tasks: [].
- Никаких вычислений, нормативных заключений и внешних источников: только выбор задачи и извлечение параметров.
"""
    response = client.models.generate_content(
        model=MODEL,
        contents=instructions + "\nЗАПРОС ПОЛЬЗОВАТЕЛЯ: " + text,
        config={"response_mime_type": "application/json", "temperature": 0},
    )
    raw = (response.text or "").strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("ИИ вернул данные в неправильном формате")
    parsed["tasks"] = [t for t in parsed.get("tasks", []) if t in VALID_TASKS]
    return parsed


def explain_with_ai(request, results):
    client = gemini_client()
    payload = json.dumps(results, ensure_ascii=False)
    response = client.models.generate_content(
        model=MODEL,
        contents=(
            "Ты учебный помощник начинающим архитекторам. Объясни результаты простым русским языком "
            "в 3–5 предложениях. Пользуйся только заданными вычисленными цифрами, формулами и параметрами: "
            "не меняй значения, не вводи новые нормативы и не утверждай соответствие СН РК или СП РК. "
            f"Запрос: {request}\nВычисленные результаты: {payload}"
        ),
    )
    return (response.text or "").strip()

st.subheader("Запрос обычным текстом")
request = st.text_area(
    "Опишите задачу",
    value="Комната длиной 5 метров, шириной 4 метра и высотой 3 метра. Вычисли площадь пола, объём и размеры комнаты на чертеже в масштабе 1:100.",
    height=110,
)

if st.button("✨ Рассчитать через ИИ", type="primary", use_container_width=True):
    if not API_KEY:
        st.error("Для настоящего ИИ-анализа нужен API-ключ. Нельзя сдавать ручной режим как ИИ-прототип.")
    elif not request.strip():
        st.error("Введите запрос")
    else:
        try:
            with st.spinner("ИИ разбирает запрос, Python выполняет расчёты..."):
                parsed = interpret_request(request)
                results, missing = calculate(parsed)
            st.subheader("Как ИИ понял запрос")
            st.json(parsed)
            if missing:
                st.warning("Для части расчётов не хватает данных: " + ", ".join(missing) + ". Уточните запрос.")
            if results:
                st.subheader("Результаты вычислений Python")
                for item in results:
                    st.metric(item["label"], f'{item["value"]:g} {item["unit"]}')
                    st.caption(f'{item["formula"]} · {item["substitution"]}')
                st.subheader("Объяснение ИИ")
                try:
                    with st.spinner("ИИ формулирует объяснение..."):
                        explanation = explain_with_ai(request, results)
                    if explanation:
                        st.write(explanation)
                    else:
                        st.warning("ИИ не вернул пояснение. Результаты вычислений выше корректны по указанным формулам.")
                except Exception as exc:
                    st.warning(f"Объяснение ИИ временно недоступно: {type(exc).__name__}. Расчётные результаты показаны выше.")
            elif not missing:
                st.warning("Запрос не относится к поддерживаемым расчётам. Попробуйте площадь, объём или масштаб.")
        except Exception as exc:
            st.error("Не удалось получить результат. Проверьте модель, доступность API, лимиты и параметры запроса.")
            with st.expander("Техническая информация"):
                st.code(f"{type(exc).__name__}: {exc}")

with st.expander("🔧 Проверить формулы вручную (без ИИ)"):
    st.caption("Этот режим нужен только для проверки Python-формул, не является демонстрацией работы нейросети.")
    col1, col2, col3 = st.columns(3)
    with col1:
        length = st.number_input("Длина, м", min_value=0.01, value=5.0, step=0.5)
    with col2:
        width = st.number_input("Ширина, м", min_value=0.01, value=4.0, step=0.5)
    with col3:
        height = st.number_input("Высота, м", min_value=0.01, value=3.0, step=0.5)
    scale = st.number_input("Масштаб 1:", min_value=1, value=100, step=10)
    if st.button("Проверить вычисления"):
        results, _ = calculate({"tasks": ["area", "volume", "scale"], "length_m": length,
                                "width_m": width, "height_m": height, "scale_denominator": scale})
        for item in results:
            st.write(f'**{item["label"]}: {item["value"]:g} {item["unit"]}** — {item["substitution"]}')

st.divider()
st.caption("⚠️ Учебный прототип. Не предназначен для конструктивных расчётов и подтверждения соответствия строительным нормам.")
