class OcrAdapter:
    """Optional OCR boundary for crash reports and evidence documents."""

    def extract_text(self, document_bytes: bytes) -> str:
        if not document_bytes:
            return ""
        raise RuntimeError("OCR provider is not configured for this MVP deployment")
