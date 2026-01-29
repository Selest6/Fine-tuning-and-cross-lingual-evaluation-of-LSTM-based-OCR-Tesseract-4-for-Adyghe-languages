import re

replacements = {
    "гц": "щ",
    "щг": "щт",
    "ьI": "ы",
    "ьш": "ым",
    "щI": "шI",
    "Ю": "Iо",
    "IД": "Щ",
    "кГ": "кI",
    "цГ": "цI",
    "пгь": "шъ",
    "гь": "гъ",
    "щъ": "шъ",
    "ГI": "П",
    "гI": "тI",
    "IЦ": "Щ",
    "кь": "къ",
    "пг": "ш",
    "III": "Ш",
    "шь": "шъ",
    "ге": "те",
    "зз": "зэ",
    "дI": "цI",
    "кIп": "кIи",
    "гх": "тх",
    "зьг": "зы",
    "еэ": "сэ",
    "ль": "лъ",
    "ъI": "ы",
    "чь": "чъ",
    "гк": "тк",
    "еи": "си",
    "ии": "ин",
    "фн": "фи",
    "дн": "ди",
    "шты": "щты",
    "фз": "фэ"
}

def correct_text(input_file, output_file):
    with open(input_file, "r", encoding="utf-8") as f:
        text = f.read()

    for wrong, correct in replacements.items():
        text = text.replace(wrong, correct)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(text)

    print(f"Исправленный файл сохранен как: {output_file}")

input_filename = "Adyghe_OCR.txt"
output_filename = "Adyghe_OCRFixed.txt"

correct_text(input_filename, output_filename)