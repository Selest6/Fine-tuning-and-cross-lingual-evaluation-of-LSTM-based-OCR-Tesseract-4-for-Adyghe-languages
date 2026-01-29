import os
import xml.etree.ElementTree as ET
import pandas as pd
import chardet
from collections import Counter

folder_to_meta = {
    "adyghe_ordinary_poetic": ["meta_general.xlsx", "meta_poetic.xlsx"],
    "adyghe_parallel": ["meta_parallel.xlsx"]
}

OUTPUT_FILE = r"1_Adyghe_NoOCR.txt"
ENCODING_LOG = "encoding_log_noocr.txt"
ERROR_LOG = "errors_noocr.log"
MIN_CONFIDENCE = 0.7
BAD_SYMBOLS = ["�", "\x00", "Ð", "Ñ"]


def normalize_text(text: str) -> str:
    return " ".join(text.split())

def detect_encoding(path: str, nbytes: int = 20000):
    with open(path, "rb") as f:
        raw = f.read(nbytes)
    result = chardet.detect(raw)
    return result["encoding"], result["confidence"]

def log_encoding(log_f, path, enc, conf):
    log_f.write(f"{path}\t{enc}\t{conf:.3f}\n")


meta_data = {}
for folder, meta_files in folder_to_meta.items():
    combined_df = pd.DataFrame()
    for meta_file in meta_files:
        try:
            df = pd.read_excel(meta_file)
            if "filename" in df.columns and "type" in df.columns:
                combined_df = pd.concat([combined_df, df[["filename", "type"]]], ignore_index=True)
            else:
                print(f"Файл {meta_file} не содержит нужных колонок 'filename' и 'type'")
        except Exception as e:
            print(f"[Ошибка чтения {meta_file}: {e}]")
    meta_data[folder] = combined_df

print("\nМетаданные")
for folder, df in meta_data.items():
    print(f"Папка {folder}: {len(df)} строк метаданных")
    if df.empty:
        print(f"Нет данных для папки {folder}")
print("\n")


def include_file(folder, filename):
    df = meta_data.get(folder)
    if df is None or df.empty:
        return True  # Если метаданных нет, включаем файл
    match = df[df["filename"].astype(str) == filename]
    if match.empty:
        return True  # Файл не найден в метаданных — включаем
    type_col = match["type"].fillna("").astype(str).str.lower()
    return not type_col.eq("ocr").any()

first = True
with open(OUTPUT_FILE, "w", encoding="utf-8") as out, \
     open(ENCODING_LOG, "w", encoding="utf-8") as enc_log, \
     open(ERROR_LOG, "w", encoding="utf-8") as err_log:

    enc_log.write("file\tencoding\tconfidence\n")

    for folder in folder_to_meta:
        for root_dir, dirs, files in os.walk(folder):
            for file in files:
                if not include_file(folder, file):
                    continue  # Пропускаем OCR-файлы

                file_path = os.path.join(root_dir, file)

                try:
                    # Проверка на пустой файл
                    with open(file_path, "rb") as f:
                        raw = f.read()
                    if len(raw.strip()) == 0:
                        err_log.write(f"{file_path}: empty file\n")
                        continue

                    # TXT файлы
                    if file.lower().endswith(".txt"):
                        enc, conf = detect_encoding(file_path)
                        log_encoding(enc_log, file_path, enc, conf)

                        if enc is None or conf < MIN_CONFIDENCE:
                            raise ValueError(f"Uncertain encoding ({enc}, {conf:.2f})")

                        with open(file_path, "r", encoding=enc) as f:
                            text = normalize_text(f.read())

                        if not first:
                            out.write(" ")
                        first = False
                        out.write(text)

                    # XML файлы
                    elif file.lower().endswith(".xml"):
                        tree = ET.parse(file_path)
                        root = tree.getroot()

                        adyghe_texts = [
                            normalize_text(se.text)
                            for se in root.findall('.//se[@lang="adyghe"]')
                            if se.text and se.text.strip()
                        ]

                        if adyghe_texts:
                            if not first:
                                out.write(" ")
                            first = False
                            out.write(" ".join(adyghe_texts))

                except Exception as e:
                    err_log.write(f"{file_path}: {e}\n")
                    raise

print("Corpus:", os.path.abspath(OUTPUT_FILE))
print("Encoding log:", os.path.abspath(ENCODING_LOG))
print("Error log:", os.path.abspath(ERROR_LOG))

with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
    final_text = f.read()

char_freq = Counter(final_text)
for sym in BAD_SYMBOLS:
    print(f"{repr(sym)}:", char_freq.get(sym, 0))

print("Unique characters:", len(char_freq))
for c in sorted(char_freq)[:50]:
    print(repr(c), char_freq[c])

