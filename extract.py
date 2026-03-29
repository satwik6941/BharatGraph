import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io
from pathlib import Path

# Path to your PDF
documents_dir = Path("documents")
outputs_dir = Path("extracted_outputs")

outputs_dir.mkdir(exist_ok=True)

# To get the list of the PDF files in the documents folder
pdf_files = list(documents_dir.glob("*.pdf"))

if not pdf_files:
    print("No PDF files found in the documents directory.")
else:
    for pdf in pdf_files:
        print(f"Processing {pdf.name}")

        output_path = outputs_dir / f"{pdf.stem}_output.txt"

        pdf_document = fitz.open(pdf)

        with open(output_path, "w", encoding="utf-8") as f:
            for page_num in range(len(pdf_document)):
                # Get the page
                page = pdf_document[page_num]
                
                # Render page to an image (pixmap)
                pix = page.get_pixmap(dpi=300)  # Higher DPI for better OCR accuracy
                
                # Convert pixmap to PIL Image
                img = Image.open(io.BytesIO(pix.tobytes()))
                
                # Extract text using pytesseract
                text = pytesseract.image_to_string(img, lang='hin')
                f.write(f"--- Page {page_num + 1} ---\n")
                f.write(text)
                f.write("\n\n")
        
        pdf_document.close()
        print(f"  Saved to: {output_path}")

    print(f"\nExtraction complete! {len(pdf_files)} file(s) processed. Check the 'outputs' folder.")