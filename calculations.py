"""Точные базовые вычисления для учебного прототипа ArchCalc AI."""
import math

VALID_TASKS = ("area", "volume", "scale")


def _positive(value, name):
    if value is None or isinstance(value, bool):
        raise ValueError(f"Не указано значение: {name}")
    try:
        number = float(str(value).replace(",", "."))
    except (ValueError, TypeError) as error:
        raise ValueError(f"Неверное значение: {name}") from error
    if not math.isfinite(number) or number <= 0 or number > 1_000_000:
        raise ValueError(f"{name}: введите положительное число в допустимом диапазоне")
    return number


def calculate(parsed):
    """Вычисляет только явно запрошенные виды расчёта, без догадок о размерах."""
    tasks = parsed.get("tasks", [])
    if not isinstance(tasks, list):
        raise ValueError("Неверный формат списка расчётов")
    tasks = [x for x in tasks if x in VALID_TASKS]
    if not tasks:
        raise ValueError("Не удалось определить вид расчёта. Уточните запрос")
    results = []
    missing = []
    length = parsed.get("length_m")
    width = parsed.get("width_m")
    height = parsed.get("height_m")
    scale = parsed.get("scale_denominator")

    def get(value, name):
        if value is None:
            missing.append(name)
            return None
        return _positive(value, name)

    if "area" in tasks:
        a, b = get(length, "длина (м)"), get(width, "ширина (м)")
        if a is not None and b is not None:
            results.append({"label": "Площадь пола", "value": round(a * b, 6), "unit": "м²",
                            "formula": "S = a × b", "substitution": f"S = {a:g} × {b:g} = {a*b:g} м²"})
    if "volume" in tasks:
        a, b, h = get(length, "длина (м)"), get(width, "ширина (м)"), get(height, "высота (м)")
        if a is not None and b is not None and h is not None:
            results.append({"label": "Объём помещения", "value": round(a * b * h, 6), "unit": "м³",
                            "formula": "V = a × b × h", "substitution": f"V = {a:g} × {b:g} × {h:g} = {a*b*h:g} м³"})
    if "scale" in tasks:
        a, b, n = get(length, "длина (м)"), get(width, "ширина (м)"), get(scale, "знаменатель масштаба")
        if a is not None and b is not None and n is not None:
            length_cm = a * 100 / n
            width_cm = b * 100 / n
            results.extend([
                {"label": f"Длина на чертеже 1:{n:g}", "value": round(length_cm, 6), "unit": "см",
                 "formula": "l = L × 100 / n", "substitution": f"l = {a:g} × 100 / {n:g} = {length_cm:g} см"},
                {"label": f"Ширина на чертеже 1:{n:g}", "value": round(width_cm, 6), "unit": "см",
                 "formula": "l = L × 100 / n", "substitution": f"l = {b:g} × 100 / {n:g} = {width_cm:g} см"},
            ])
    return results, list(dict.fromkeys(missing))
