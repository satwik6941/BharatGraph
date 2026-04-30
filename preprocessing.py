import re
import unicodedata
from pathlib import Path

# Unicode script ranges
DEVANAGARI_RANGE = 'ऀ-ॿ'   # Hindi + Marathi
TELUGU_RANGE     = 'ఀ-౿'   # Telugu
DEVANAGARI_DIGITS = '०१२३४५६७८९'
ARABIC_DIGITS     = '0123456789'
DIGIT_TRANS = str.maketrans(DEVANAGARI_DIGITS, ARABIC_DIGITS)

HINDI_STOPWORDS = {
    'में', 'से', 'को', 'का', 'की', 'के', 'पर', 'तक', 'ने', 'द्वारा',
    'यह', 'वह', 'इस', 'उस', 'जो', 'कोई', 'कुछ', 'मैं', 'हम', 'तुम',
    'आप', 'वे', 'ये', 'इन', 'उन',
    'है', 'हैं', 'था', 'थी', 'थे', 'थीं', 'हो', 'होता', 'होती', 'होते',
    'हुआ', 'हुई', 'हुए', 'रहा', 'रही', 'रहे', 'सकता', 'सकती', 'सकते',
    'जाता', 'जाती', 'जाते',
    'और', 'या', 'लेकिन', 'परन्तु', 'किन्तु', 'तो', 'भी', 'ही',
    'न', 'नहीं', 'अगर', 'क्योंकि', 'कि', 'जब', 'तब', 'जैसे', 'फिर',
    'अभी', 'कब', 'कहाँ',
    'एक', 'कई', 'सब', 'सभी', 'कम', 'ज्यादा', 'बहुत', 'अधिक',
    'इसलिए', 'इसके', 'उसके', 'अपने', 'अपना', 'अपनी', 'साथ', 'बाद',
    'पहले', 'दूसरे', 'ऐसे', 'वैसे', 'कहा', 'दिया', 'दी', 'लिया',
    'लिए', 'किया', 'करके', 'तथा', 'एवं', 'व',
}


def _script_range(language: str) -> str:
    if language == "telugu":
        return TELUGU_RANGE
    return DEVANAGARI_RANGE  # hindi and marathi both use Devanagari


def normalize_unicode(text: str) -> str:
    return unicodedata.normalize('NFC', text)


def remove_page_markers(text: str) -> str:
    return re.sub(r'-{2,}\s*Page\s*\d+\s*-{2,}', '', text)


def fix_dandas(text: str) -> str:
    return text.replace('|', '।')


def normalize_nuktas(text: str) -> str:
    nukta_map = {'क़': 'क', 'ख़': 'ख', 'ग़': 'ग', 'ज़': 'ज', 'फ़': 'फ'}
    for nukta_char, base_char in nukta_map.items():
        text = text.replace(nukta_char, base_char)
    return text


def normalize_chandrabindu(text: str) -> str:
    return text.replace('ँ', 'ं')


def remove_ocr_noise(text: str, language: str) -> str:
    """Remove lines that are mostly garbage, using the correct script range."""
    script = _script_range(language)
    cleaned_lines = []
    for line in text.split('\n'):
        stripped = line.strip()
        if not stripped:
            continue
        script_letters = len(re.findall(f'[{script}]', stripped))
        total_chars = len(stripped.replace(' ', ''))
        if total_chars == 0:
            continue
        ratio = script_letters / total_chars
        if len(stripped) < 5 and ratio < 0.8:
            continue
        if len(stripped) >= 5 and ratio < 0.6:
            continue
        cleaned_lines.append(stripped)
    return '\n'.join(cleaned_lines)


def remove_isolated_matras(text: str) -> str:
    text = re.sub(r'(?<=\s)[ा-्ॢॣ]+', '', text)
    text = re.sub(r'^[ा-्ॢॣ]+', '', text)
    return text


def clean_punctuation(text: str, language: str) -> str:
    """Keep only characters from the correct script range + shared punctuation."""
    if language == "telugu":
        text = re.sub(r'[^ఀ-౿\s0-9।॥,\.\-()]+', ' ', text)
    else:
        # Devanagari — same as before
        text = re.sub(r'[^ऀ-ॿ\s0-9।॥,\.\-()]+', ' ', text)
    return text


def normalize_whitespace(text: str) -> str:
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def normalize_digits(text: str) -> str:
    return text.translate(DIGIT_TRANS)


def remove_stopwords(text: str) -> str:
    words = text.split()
    return ' '.join(w for w in words if w not in HINDI_STOPWORDS)


def preprocess(text: str, language: str = "hindi", remove_stops: bool = False) -> str:
    """
    Full preprocessing pipeline, language-aware.
    language: 'hindi' | 'marathi' | 'telugu'
    """
    text = normalize_unicode(text)
    text = remove_page_markers(text)
    if language in ("hindi", "marathi"):
        text = fix_dandas(text)
        text = normalize_nuktas(text)
        text = normalize_chandrabindu(text)
        text = remove_isolated_matras(text)
    text = remove_ocr_noise(text, language)
    text = clean_punctuation(text, language)
    text = normalize_digits(text)
    text = normalize_whitespace(text)
    if remove_stops and language == "hindi":
        text = remove_stopwords(text)
    return text


def _filename_to_language(stem: str) -> str:
    stem_lower = stem.lower()
    if "marathi" in stem_lower:
        return "marathi"
    if "telugu" in stem_lower:
        return "telugu"
    return "hindi"


if __name__ == "__main__":
    input_dir = Path("outputs")
    output_dir = Path("cleaned_outputs")
    output_dir.mkdir(exist_ok=True)

    txt_files = list(input_dir.glob("*.txt"))

    if not txt_files:
        print("No text files found in outputs directory.")
    else:
        for file in txt_files:
            language = _filename_to_language(file.stem)
            print(f"Preprocessing {file.name}  [language={language}]")
            with open(file, "r", encoding="utf-8") as f:
                raw_text = f.read()

            cleaned = preprocess(raw_text, language=language, remove_stops=False)

            out_path = output_dir / file.name
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(cleaned)

            print(f"  Saved to: {out_path}")

        print(f"\nDone! {len(txt_files)} file(s) preprocessed.")
