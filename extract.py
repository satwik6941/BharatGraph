import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io
from pathlib import Path

# Tesseract language codes for each language keyword in filename
# filename must contain one of: _hindi, _marathi, _telugu (or no keyword = hindi default)
LANG_MAP = {
    "marathi": "mar",
    "telugu":  "tel",
    "hindi":   "hin",
}


def detect_lang_code(stem: str) -> str:
    """Return Tesseract lang code based on filename keywords."""
    stem_lower = stem.lower()
    for keyword, code in LANG_MAP.items():
        if keyword in stem_lower:
            return code
    return "hin"  # default


documents_dir = Path("documents")
outputs_dir = Path("extracted_outputs")
outputs_dir.mkdir(exist_ok=True)

pdf_files = list(documents_dir.glob("*.pdf"))

if not pdf_files:
    print("No PDF files found in the documents directory.")
else:
    for pdf in pdf_files:
        lang_code = detect_lang_code(pdf.stem)
        print(f"Processing {pdf.name}  [lang={lang_code}]")

        output_path = outputs_dir / f"{pdf.stem}_output.txt"

        pdf_document = fitz.open(pdf)

        with open(output_path, "w", encoding="utf-8") as f:
            for page_num in range(len(pdf_document)):
                page = pdf_document[page_num]
                pix = page.get_pixmap(dpi=300)
                img = Image.open(io.BytesIO(pix.tobytes()))
                text = pytesseract.image_to_string(img, lang=lang_code)
                f.write(f"--- Page {page_num + 1} ---\n")
                f.write(text)
                f.write("\n\n")

        pdf_document.close()
        print(f"  Saved to: {output_path}")

    print(f"\nExtraction complete! {len(pdf_files)} file(s) processed.")