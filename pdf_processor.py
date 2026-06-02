import pdfplumber


def extract_text_from_pdf(file_path: str) -> str:
    all_text = []
    try:
        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                text = page.extract_text()
                if text:
                    all_text.append(f"\n--- Page {i} ---\n{text}")
        return "\n".join(all_text).strip()
    except Exception as e:
        raise RuntimeError(f"PDF extraction failed: {e}") from e


def get_page_count(file_path: str) -> int:
    try:
        with pdfplumber.open(file_path) as pdf:
            return len(pdf.pages)
    except Exception:
        return 0
