import re
import unicodedata
from pathlib import Path

# Devanagari Unicode ranges
DEVANAGARI_RANGE = '\u0900-\u097F'
DEVANAGARI_DIGITS = '०१२३४५६७८९'
ARABIC_DIGITS = '0123456789'

# Hindi stopwords
HINDI_STOPWORDS = {
    # Postpositions
    'में', 'से', 'को', 'का', 'की', 'के', 'पर', 'तक', 'ने', 'द्वारा',
    # Pronouns
    'यह', 'वह', 'इस', 'उस', 'जो', 'कोई', 'कुछ', 'मैं', 'हम', 'तुम',
    'आप', 'वे', 'ये', 'इन', 'उन',
    # Auxiliary verbs
    'है', 'हैं', 'था', 'थी', 'थे', 'थीं', 'हो', 'होता', 'होती', 'होते',
    'हुआ', 'हुई', 'हुए', 'रहा', 'रही', 'रहे', 'सकता', 'सकती', 'सकते',
    'जाता', 'जाती', 'जाते',
    # Conjunctions and particles
    'और', 'या', 'लेकिन', 'परन्तु', 'किन्तु', 'तो', 'भी', 'ही',
    'न', 'नहीं', 'अगर', 'क्योंकि', 'कि', 'जब', 'तब', 'जैसे', 'फिर',
    'अभी', 'कब', 'कहाँ',
    # Determiners
    'एक', 'कई', 'सब', 'सभी', 'कम', 'ज्यादा', 'बहुत', 'अधिक',
    # Others
    'इसलिए', 'इसके', 'उसके', 'अपने', 'अपना', 'अपनी', 'साथ', 'बाद',
    'पहले', 'दूसरे', 'ऐसे', 'वैसे', 'कहा', 'दिया', 'दी', 'लिया',
    'लिए', 'किया', 'करके', 'तथा', 'एवं', 'व',
}

# Devanagari digit translation table
DIGIT_TRANS = str.maketrans(DEVANAGARI_DIGITS, ARABIC_DIGITS)


def normalize_unicode(text: str) -> str:
    """NFC normalization to merge decomposed characters."""
    return unicodedata.normalize('NFC', text)


def remove_page_markers(text: str) -> str:
    """Remove --- Page N --- markers inserted during OCR extraction."""
    return re.sub(r'-{2,}\s*Page\s*\d+\s*-{2,}', '', text)


def fix_dandas(text: str) -> str:
    """Replace misrecognized pipe | with Devanagari danda ।"""
    return text.replace('|', '।')


def normalize_nuktas(text: str) -> str:
    """Normalize nukta-bearing characters to base forms (except ड़ ढ़)."""
    nukta_map = {
        'क़': 'क', 'ख़': 'ख', 'ग़': 'ग', 'ज़': 'ज', 'फ़': 'फ',
    }
    for nukta_char, base_char in nukta_map.items():
        text = text.replace(nukta_char, base_char)
    return text


def normalize_chandrabindu(text: str) -> str:
    """Normalize chandrabindu (ँ) to anusvara (ं)."""
    return text.replace('\u0901', '\u0902')


def remove_ocr_noise(text: str) -> str:
    """Remove lines that are mostly garbage (isolated chars, stray digits, symbols)."""
    cleaned_lines = []
    for line in text.split('\n'):
        stripped = line.strip()
        if not stripped:
            continue
        # Count meaningful Devanagari characters (letters, not just digits/marks)
        devanagari_letters = len(re.findall(f'[{DEVANAGARI_RANGE}]', stripped))
        total_chars = len(stripped.replace(' ', ''))
        if total_chars == 0:
            continue
        # Keep the line only if it has enough Devanagari content
        # Short lines need higher ratio, long lines can tolerate some noise
        ratio = devanagari_letters / total_chars
        if len(stripped) < 5 and ratio < 0.8:
            continue
        if len(stripped) >= 5 and ratio < 0.4:
            continue
        cleaned_lines.append(stripped)
    return '\n'.join(cleaned_lines)


def remove_isolated_matras(text: str) -> str:
    """Remove vowel signs (matras) that appear without a preceding consonant."""
    # Matras: \u093E-\u094D, \u0962-\u0963
    # They should only appear after a consonant (\u0915-\u0939)
    # Remove matras that appear at the start of a word or after a space
    text = re.sub(r'(?<=\s)[\u093E-\u094D\u0962\u0963]+', '', text)
    text = re.sub(r'^[\u093E-\u094D\u0962\u0963]+', '', text)
    return text


def clean_punctuation(text: str) -> str:
    """Remove stray punctuation and symbols, keep Devanagari text and dandas."""
    # Keep: Devanagari chars, spaces, dandas, digits, basic punctuation for readability
    text = re.sub(r'[^\u0900-\u097F\s0-9।॥,\.\-()]+', ' ', text)
    return text


def normalize_whitespace(text: str) -> str:
    """Collapse multiple spaces/blank lines."""
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def normalize_digits(text: str) -> str:
    """Convert Devanagari digits to Arabic digits."""
    return text.translate(DIGIT_TRANS)


def remove_stopwords(text: str) -> str:
    """Remove Hindi stopwords from text."""
    words = text.split()
    filtered = [w for w in words if w not in HINDI_STOPWORDS]
    return ' '.join(filtered)


def preprocess(text: str, remove_stops: bool = False) -> str:
    """
    Full preprocessing pipeline for Hindi OCR text.

    Args:
        text: Raw OCR text
        remove_stops: Whether to remove stopwords.
                      Set False if feeding to an LLM (it needs context words).
                      Set True if doing keyword-based NLP.
    """
    text = normalize_unicode(text)
    text = remove_page_markers(text)
    text = fix_dandas(text)
    text = normalize_nuktas(text)
    text = normalize_chandrabindu(text)
    text = remove_isolated_matras(text)
    text = remove_ocr_noise(text)
    text = clean_punctuation(text)
    text = normalize_digits(text)
    text = normalize_whitespace(text)
    if remove_stops:
        text = remove_stopwords(text)
    return text


if __name__ == "__main__":
    input_dir = Path("outputs")
    output_dir = Path("cleaned_outputs")
    output_dir.mkdir(exist_ok=True)

    txt_files = list(input_dir.glob("*.txt"))

    if not txt_files:
        print("No text files found in outputs directory.")
    else:
        for file in txt_files:
            print(f"Preprocessing {file.name}...")
            with open(file, "r", encoding="utf-8") as f:
                raw_text = f.read()

            # remove_stops=False because we'll feed this to an LLM for KG extraction
            cleaned = preprocess(raw_text, remove_stops=False)

            out_path = output_dir / file.name
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(cleaned)

            print(f"  Saved to: {out_path}")

        print(f"\nDone! {len(txt_files)} file(s) preprocessed.")