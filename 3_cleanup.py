import re
import random
from collections import defaultdict
import unicodedata

random.seed(42)

adyghe_uppercase = "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯVXLCDM"
adyghe_lowercase = "абвгдеёжзийклмнопрстуфхцчшщъыьэюяI"
letters = set(adyghe_uppercase + adyghe_lowercase)
digits = set("0123456789")

punctuation = {
    ".", ",", ":", ";", "?", "!", "-",
    "«", "»", "(", ")", "[", "]",
    "/", "\\", "*", "'", '"',
    "_", "°", "%", "№", "+", "=", "|"
}

stress = {"\u0301"}

ALLOWED_CHARS = letters | digits | punctuation | stress

COMBINING_BREVE = "\u0306"
COMBINING_DIAERESIS = "\u0308"

ALLOWED_COMBINATIONS = {
    ("и", COMBINING_BREVE),
    ("И", COMBINING_BREVE),
    ("е", COMBINING_DIAERESIS),
    ("Е", COMBINING_DIAERESIS),
}

QUOTES_REGEX = re.compile(r"[«»„“”\"‹›]")
APOSTROPHES_REGEX = re.compile(r"[’'‘ʼʻʽʾʿ]")
DASHES_REGEX = re.compile(r"[—–‒―−]")
ELLIPSIS_REGEX = re.compile(r"\u2026|\.{3,}")

ZERO_WIDTH = {"\u200B", "\u200C", "\u200D", "\uFEFF"}
STRESS_EQUIVALENTS = {"\u0301", "\u0341", "\u02CA"}

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
            out.write(f"{ch}\tU+{ord(ch):04X}\t{count}\t{percent:.6f}%\n")

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

def shuffle_quotes(text):
    matches = list(QUOTES_REGEX.finditer(text))
    if not matches:
        return text
    random.shuffle(matches)
    repl = {}
    for i, m in enumerate(matches):
        if i < len(matches) // 2:
            repl[m.start()] = "«"
        else:
            repl[m.start()] = "»"
    out = []
    last = 0
    for m in sorted(matches, key=lambda m: m.start()):
        out.append(text[last:m.start()])
        out.append(repl[m.start()])
        last = m.end()
    out.append(text[last:])
    return "".join(out)

def normalize_text(text):
    text = re.sub(r"[\n\t\r\u00A0]+", " ", text)
    text = ELLIPSIS_REGEX.sub("...", text)
    text = DASHES_REGEX.sub("-", text)
    text = APOSTROPHES_REGEX.sub("'", text)
    text = normalize_unicode_noise(text)
    text = shuffle_quotes(text)
    text = re.sub(r"\s+([.,:;?!])", r"\1", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()

def token_is_valid(token):
    i = 0
    n = len(token)
    bad_chars = set()
    while i < n:
        ch = token[i]
        if i + 1 < n and unicodedata.combining(token[i + 1]):
            pair = (ch, token[i + 1])
            if pair not in ALLOWED_COMBINATIONS:
                bad_chars.add(ch + token[i + 1])
            i += 2
            continue
        if unicodedata.combining(ch):
            bad_chars.add(ch)
            i += 1
            continue
        if ch not in ALLOWED_CHARS:
            bad_chars.add(ch)
            i += 1
            continue
        i += 1
    return len(bad_chars) == 0, bad_chars

def process_file_streaming(input_path, output_path, removed_tokens_path, buffer_size=10000):
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
            fout.write(" ".join(buffer))

    with open(removed_tokens_path, "w", encoding="utf-8") as f:
        f.write("token\tbad_chars\tcount\n")
        for tok, info in sorted(
                removed.items(),
                key=lambda x: (-len(x[0]), -x[1]["count"], x[0])
        ):
            bad = "".join(sorted(info["bad_chars"]))
            f.write(f"{tok}\t{bad}\t{info['count']}\n")

if __name__ == "__main__":
    process_file_streaming(
        input_path="2_Adyghe_OCR.txt",
        output_path="3_Adyghe_OCR.txt",
        removed_tokens_path="3_Adyghe_OCR_removed_tokens.txt"
    )

    compute_char_stats_from_file(
        input_path="3_Adyghe_OCR.txt",
        stats_path="3_Adyghe_OCR_char_stats.tsv"
    )
