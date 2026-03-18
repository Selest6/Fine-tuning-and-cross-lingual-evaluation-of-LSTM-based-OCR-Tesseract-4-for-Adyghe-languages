import re
import random
from collections import defaultdict
import unicodedata


random.seed(42)

# Разрешённые символы

adyghe_uppercase = "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯVXLCDM"
adyghe_lowercase = "абвгдеёжзийклмнопрстуфхцчшщъыьэюяI"
letters = set(adyghe_uppercase + adyghe_lowercase)
digits = set("0123456789")

punctuation = {
    ".", ",", ":", ";", "?", "!", "-",
    "«", "»", "(", ")", "[", "]",
    "/", "*", "'", '"', "•",
    "_", "%", "№", "+", "=", "<", ">"
}

stress = {"\u0301"}  # комбинирующее ударение

ALLOWED_CHARS = letters | digits | punctuation | stress

# Регексы нормализации

QUOTES_REGEX = re.compile(r"[«»„“”\"‹›]")
DASHES_REGEX = re.compile(r"[—–‒―−]")
ELLIPSIS_REGEX = re.compile(r"\u2026|\.{3,}")
ZERO_WIDTH = {"\u200B", "\u200C", "\u200D", "\uFEFF"}
STRESS_EQUIVALENTS = {"\u0301", "\u0341", "\u02CA"}
COMMAS_REGEX = re.compile(r"[‚،﹐﹑，､]")

def compute_char_stats_from_file(input_path, stats_path, buffer_size=1024 * 1024):
    counter = defaultdict(int)
    total_chars = 0

    with open(input_path, encoding="utf-8") as f:
        while True:
            chunk = f.read(buffer_size)
            if not chunk:
                break

            for ch in chunk:
                counter[ch] += 1
                total_chars += 1

    with open(stats_path, "w", encoding="utf-8") as out:
        out.write(f"Total characters: {total_chars}\n")
        out.write("char\tcodepoint\tcount\tpercent\n")

        for ch, count in sorted(counter.items(), key=lambda x: -x[1]):
            percent = (count / total_chars * 100) if total_chars else 0
            out.write(
                f"{ch}\tU+{ord(ch):04X}\t{count}\t{percent:.6f}%\n"
            )


# Нормализация Unicode-шумов

def normalize_unicode_noise(text):
    out = []
    for c in text:
        if c in ZERO_WIDTH:
            continue
        if c in STRESS_EQUIVALENTS:
            out.append("\u0301")
        else:
            out.append(c)
    return "".join(out)

# Кавычки

def normalize_quotes_three_types(text):
    """
    Гарантирует, что открывающая и закрывающая кавычка одной пары всегда одного типа.
    Все одиночные кавычки без пары удаляются.
    Поддерживаются три типа: «», "", ''.
    """
    ALL_QUOTES = set('«»"\'')
    QUOTE_PAIRS = [
        ("«", "»"),
        ('"', '"'),
        ("'", "'"),
    ]

    result = []
    stack = []  # хранит индекс и тип открытой кавычки

    pair_index = 0  # следующий тип кавычки для новой пары

    for i, ch in enumerate(text):
        if ch in ALL_QUOTES:
            if not stack:
                # открываем новую пару выбранного типа
                open_q, close_q = QUOTE_PAIRS[pair_index]
                pair_index = (pair_index + 1) % len(QUOTE_PAIRS)
                stack.append((len(result), open_q, close_q))
                result.append(open_q)
            else:
                # закрываем последнюю открывающую кавычку
                idx, open_q, close_q = stack.pop()
                result.append(close_q)
        else:
            result.append(ch)

    # удаляем незакрытые открытые кавычки
    while stack:
        idx, open_q, close_q = stack.pop()
        result[idx] = ""  # удаляем открывающую кавычку

    return "".join(result)


# Нормализация текста (БЕЗ фильтрации)

def normalize_text(text):
    # NFC
    text = unicodedata.normalize("NFC", text)

    # Нормализация запятых
    text = COMMAS_REGEX.sub(",", text)

    # Многоточие
    text = ELLIPSIS_REGEX.sub("...", text)

    # Тире
    text = DASHES_REGEX.sub("-", text)

    # Unicode-шум
    text = normalize_unicode_noise(text)

    # Кавычки
    text = normalize_quotes_three_types(text)

    # Убираем запрещённые комбинации типа -.
    text = re.sub(r'-\s*([.,:;?!])', r'\1', text)

    # Удаляем пустые и вложенные пустые конструкции
    patterns = [
        r'\(\s*\)',
        r'\[\s*\]',
        r'\{\s*\}',
        r'"\s*"',
        r"'\s*'",
        r'«\s*»'
    ]

    changed = True
    while changed:
        changed = False
        for pattern in patterns:
            new_text = re.sub(pattern, '', text)
            if new_text != text:
                changed = True
                text = new_text

    # Финальный trim
    return text.strip()

# Проверка токена

def token_is_valid(token):
    bad_chars = set()
    for ch in token:
        if ch not in ALLOWED_CHARS:
            bad_chars.add(ch)
    return len(bad_chars) == 0, bad_chars

# Основная обработка

def process_file_streaming(
    input_path,
    output_path,
    removed_tokens_path,
    buffer_size=10000
):
    removed = defaultdict(lambda: {"count": 0, "bad_chars": set()})
    buffer = []

    with open(input_path, encoding="utf-8") as fin, \
         open(output_path, "w", encoding="utf-8") as fout:

        for line in fin:
            line = normalize_text(line)
            tokens = line.split()
            kept = []

            for tok in tokens:
                valid, bad_chars = token_is_valid(tok)
                if valid:
                    kept.append(tok)
                else:
                    removed[tok]["count"] += 1
                    removed[tok]["bad_chars"].update(bad_chars)

            if kept:
                buffer.append(" ".join(kept))
                if len(buffer) >= buffer_size:
                    fout.write(" ".join(buffer) + " ")
                    buffer.clear()

        if buffer:
            full_text = " ".join(buffer)  # весь текст после токенизации и фильтрации

            # убираем пробел перед знаками препинания
            full_text = re.sub(r'\s+(?=[.,:;?!]|\.{3})', '', full_text)
            # Убираем пробелы перед закрывающими скобками и после открывающих
            full_text = re.sub(r'\s+([)\]\}])', r'\1', full_text)  # перед закрывающими
            full_text = re.sub(r'([(\[\{])\s+', r'\1', full_text)  # после открывающих

            # Сохраняем все многоточия временным токеном
            TEMP_ELLIPSIS = "__ELLIPSIS__"
            full_text = ELLIPSIS_REGEX.sub(TEMP_ELLIPSIS, full_text)

            # Схлопываем одинаковые знаки (например !!! -> !)
            full_text = re.sub(r'([.,:;?!])\1+', r'\1', full_text)

            # Схлопываем комбинации разных знаков подряд (например .!? -> .)
            # Тут важно исключить TEMP_ELLIPSIS, оно уже не содержит знаков, так что безопасно
            full_text = re.sub(r'([.,:;?!])([.,:;?!])+', r'\1', full_text)

            # Возвращаем многоточия
            full_text = full_text.replace(TEMP_ELLIPSIS, "...")

            # Убираем пробел после открывающей кавычки
            full_text = re.sub(r'([«"\'])\s+', r'\1', full_text)

            # Убираем пробел перед закрывающей кавычкой
            full_text = re.sub(r'\s+([»"\'])', r'\1', full_text)

            fout.write(full_text)

    # Запись удалённых токенов

    with open(removed_tokens_path, "w", encoding="utf-8") as f:
        f.write("token\tbad_chars\tcount\n")
        for tok, info in sorted(
                removed.items(),
                key=lambda x: (-len(x[0]), -x[1]["count"], x[0])
        ):
            bad = "".join(sorted(info["bad_chars"]))
            f.write(f"{tok}\t{bad}\t{info['count']}\n")

# Точка входа

if __name__ == "__main__":

    process_file_streaming(
        input_path="3_Kabard_NoOCR.txt",
        output_path="4_Kabard_NoOCR.txt",
        removed_tokens_path="4_Kabard_NoOCR_removed_tokens.txt"
    )

    compute_char_stats_from_file(
        input_path="4_Kabard_NoOCR.txt",
        stats_path="4_Kabard_NoOCR_char_stats.tsv"
    )


    process_file_streaming(
        input_path="3_Kabard_OCR.txt",
        output_path="4_Kabard_OCR.txt",
        removed_tokens_path="4_Kabard_OCR_removed_tokens.txt"
    )

    compute_char_stats_from_file(
        input_path="4_Kabard_OCR.txt",
        stats_path="4_Kabard_OCR_char_stats.tsv"
    )


    process_file_streaming(
        input_path="3_Adyghe_NoOCR.txt",
        output_path="4_Adyghe_NoOCR.txt",
        removed_tokens_path="4_Adyghe_NoOCR_removed_tokens.txt"
    )

    compute_char_stats_from_file(
        input_path="4_Adyghe_NoOCR.txt",
        stats_path="4_Adyghe_NoOCR_char_stats.tsv"
    )


    process_file_streaming(
        input_path="3_Adyghe_OCR.txt",
        output_path="4_Adyghe_OCR.txt",
        removed_tokens_path="4_Adyghe_OCR_removed_tokens.txt"
    )

    compute_char_stats_from_file(
        input_path="4_Adyghe_OCR.txt",
        stats_path="4_Adyghe_OCR_char_stats.tsv"
    )
