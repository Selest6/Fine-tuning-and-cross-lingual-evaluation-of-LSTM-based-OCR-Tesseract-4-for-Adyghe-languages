import os
import xml.etree.ElementTree as ET
import chardet
from collections import Counter

FOLDERS = [
    r"adyghe_ordinary_poetic",
    r"adyghe_parallel"
]

OUTPUT_FILE = "1_Adyghe_OCR.txt"
ENCODING_LOG = "encoding_log.txt"
ERROR_LOG = "errors.log"
MIN_CONFIDENCE = 0.7

def normalize_text(text: str) -> str:
    return " ".join(text.split())

def detect_encoding(path: str, nbytes: int = 20000):
    with open(path, "rb") as f:
        raw = f.read(nbytes)
    result = chardet.detect(raw)
    return result["encoding"], result["confidence"]

def log_encoding(log_f, path, enc, conf):
    log_f.write(f"{path}\t{enc}\t{conf:.3f}\n")

first = True

with open(OUTPUT_FILE, "w", encoding="utf-8") as out, \
     open(ENCODING_LOG, "w", encoding="utf-8") as enc_log, \
     open(ERROR_LOG, "w", encoding="utf-8") as err_log:

    enc_log.write("file\tencoding\tconfidence\n")

    for folder in FOLDERS:
        for root_dir, _, files in os.walk(folder):
            for file in files:
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

# Проверка алфавита
with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
    final_text = f.read()

char_freq = Counter(final_text)
BAD_SYMBOLS = ["�", "\x00", "Ð", "Ñ"]

for sym in BAD_SYMBOLS:
    print(f"{repr(sym)}:", char_freq.get(sym, 0))

print("Unique characters:", len(char_freq))
for c in sorted(char_freq)[:50]:
    print(repr(c), char_freq[c])

