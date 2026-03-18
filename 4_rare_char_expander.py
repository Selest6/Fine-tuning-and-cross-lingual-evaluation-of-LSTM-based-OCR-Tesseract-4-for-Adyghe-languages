import random
import re
import unicodedata
from collections import Counter, defaultdict


# НАСТРОЙКИ

INPUT_FILE = "4_Adyghe_NoOCR.txt"
OUTPUT_FILE = "4_Adyghe_NoOCR_balanced.txt"
STATS_OUTPUT_FILE = "4_Adyghe_NoOCR_balanced_char_stats.tsv"

MIN_PERCENT = 0.003
MIN_LINE_LEN = 3
MAX_LINE_LEN = 10
PUNCT_PROB = 0.3

SPECIAL_SYMBOLS = ['№', '%', '+', '<', '>', '=']
ROMAN_SYMBOLS = ['I', 'V', 'X', 'L', 'C', 'D', 'M']

STRESS = "\u0301"


# ГРАФЕМНЫЙ РАЗБОР (OCR-SAFE)

def normalize_quotes(text):
    # 1. убираем пробел после открывающих кавычек, если дальше не пробел
    text = re.sub(r'([«"\'])(\s+)(\S)', r'\1\3', text)
    # 2. убираем пробел перед закрывающими кавычками, если перед этим не пробел
    text = re.sub(r'(\S)(\s+)([»"\'])', r'\1\3', text)
    # 3. схлопываем двойные пробелы
    text = re.sub(r'\s{2,}', ' ', text)
    return text.strip()


def split_graphemes(text):
    graphemes = []
    i = 0

    while i < len(text):
        ch = text[i]
        j = i + 1

        # собираем ВСЕ подряд combining marks
        while j < len(text) and unicodedata.combining(text[j]) != 0:
            j += 1

        graphemes.append(text[i:j])
        i = j

    return graphemes

def remove_stress(text):
    # приводим к NFD, чтобы точно разложить возможные сочетания
    text = unicodedata.normalize("NFD", text)

    # удаляем все combining marks
    text = "".join(
        ch for ch in text
        if unicodedata.combining(ch) == 0
    )

    # возвращаем обратно в NFC
    return unicodedata.normalize("NFC", text)

def count_units(text):
    return Counter(split_graphemes(text))


# СТАТИСТИКА

def print_stats(counter):
    total = sum(counter.values())

    print(f"Total graphemes: {total}")
    print("unit\tcount\tpercent")

    for unit, count in counter.most_common():
        percent = count / total * 100
        printable = unit.replace("\n", "\\n")
        print(f"{printable}\t{count}\t{percent:.6f}%")


def save_stats_tsv(counter, output_path):
    total = sum(counter.values())

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("unit\tcount\tpercent\n")
        for unit, count in counter.most_common():
            percent = count / total * 100
            printable = unit.replace("\n", "\\n")
            f.write(f"{printable}\t{count}\t{percent:.6f}\n")


# РИМСКИЕ ЧИСЛА

def int_to_roman(num):
    val = [1000,900,500,400,100,90,50,40,10,9,5,4,1]
    syms = ["M","CM","D","CD","C","XC","L","XL","X","IX","V","IV","I"]

    roman = ""
    i = 0
    while num > 0:
        for _ in range(num // val[i]):
            roman += syms[i]
            num -= val[i]
        i += 1
    return roman


def generate_roman_line():
    n = random.randint(1, 3999)
    return int_to_roman(n)


# СПЕЦСИМВОЛЫ

def generate_symbol_line(symbol):

    if symbol == '№':
        return f"№{random.randint(1, 5000)}"

    elif symbol == '%':
        return f"{random.randint(1,100)}%"

    elif symbol == '+':
        a, b = random.randint(1,50), random.randint(1,50)
        return f"{a}+{b}"

    elif symbol == '=':
        a = random.randint(1,50)
        return f"{a}={a}"

    elif symbol == '<':
        a = random.randint(1,50)
        b = a + random.randint(1,10)
        return f"{a}<{b}"

    elif symbol == '>':
        b = random.randint(1,50)
        a = b + random.randint(1,10)
        return f"{a}>{b}"

    return symbol


# WORD-LEVEL RECOMBINATION

def generate_recombined_line(target_unit, words_with_unit, all_words):
    line_length = random.randint(MIN_LINE_LEN, MAX_LINE_LEN)
    target_position = random.randint(0, line_length - 1)

    line_words = []

    for i in range(line_length):
        if i == target_position:
            w = random.choice(words_with_unit)
        else:
            w = random.choice(all_words)
        line_words.append(w)

    line = " ".join(line_words)

    if random.random() < PUNCT_PROB:
        line += random.choice([".", "!", "?", ","])

    return line


# ОСНОВНАЯ ЛОГИКА

def main():

    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        text = f.read()

    text = remove_stress(text)
    text = normalize_quotes(text)

    print("\n=== INPUT FILE STATS ===")

    char_counts = count_units(text)
    print_stats(char_counts)

    total_units = sum(char_counts.values())
    min_count = int(total_units * MIN_PERCENT / 100)

    print(f"\nМинимальный порог: {min_count} графем ({MIN_PERCENT}%)")

    words = re.findall(r"[^\W\d_]+", text, re.UNICODE)
    words = list(set(words))

    unit_to_words = defaultdict(list)
    for w in words:
        units = split_graphemes(w)
        for u in set(units):
            unit_to_words[u].append(w)

    additions = []

    # Балансировка по графемам

    for unit in list(char_counts.keys()):
        if char_counts[unit] >= min_count:
            continue

        print(f"Балансируем '{unit}'")

        while char_counts[unit] < min_count:

            if unit in SPECIAL_SYMBOLS:
                new_line = generate_symbol_line(unit)

            elif unit in ROMAN_SYMBOLS:
                new_line = generate_roman_line()

            elif unit in unit_to_words:
                new_line = generate_recombined_line(
                    unit,
                    unit_to_words[unit],
                    words
                )
            else:
                new_line = unit

            additions.append(new_line)
            char_counts.update(split_graphemes(new_line))

    # Вставка по всему тексту

    # разбиваем текст на слова и пробелы, чтобы сохранить форматирование
    words_with_spaces = re.findall(r'\S+|\s+', text)
    final_words = []

    for w in words_with_spaces:
        final_words.append(w)
        # с вероятностью 20% вставляем новый элемент
        if additions and random.random() < 0.2:
            new_line = additions.pop(0)
            final_words.append(" " + new_line + " ")

    # если остались элементы, вставляем в случайные позиции
    while additions:
        idx = random.randint(0, len(final_words))
        final_words.insert(idx, " " + additions.pop(0) + " ")

    final_text = "".join(final_words)
    final_text = unicodedata.normalize("NFC", final_text)
    # Нормализуем пробелы: больше одного пробела не будет, обрезаем пробелы по краям
    final_text = " ".join(final_text.split())

    # Итоговые статистики

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(final_text)

    print("\n=== OUTPUT FILE STATS ===")

    final_counts = count_units(final_text)
    print_stats(final_counts)
    save_stats_tsv(final_counts, STATS_OUTPUT_FILE)

    print(f"\nTSV сохранён в {STATS_OUTPUT_FILE}")


if __name__ == "__main__":
    main()
