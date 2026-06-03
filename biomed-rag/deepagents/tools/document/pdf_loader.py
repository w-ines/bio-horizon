import tempfile
import base64
import io
import os
from typing import List, Optional, Tuple
from collections import Counter

from fastapi import UploadFile
from langchain_community.document_loaders import PyPDFLoader, PyMuPDFLoader
import fitz  # PyMuPDF for rendering
import pytesseract
from PIL import Image
from langchain_core.documents import Document

# Configuration for Vision OCR using OpenRouter
VISION_OCR_ENABLED = os.getenv("VISION_OCR_ENABLED", "true").lower() == "true"
VISION_MODEL = os.getenv("VISION_MODEL", "openai/gpt-4-vision-preview")  # OpenRouter vision model
VISION_BASE_URL = os.getenv("BASE_URL", "https://openrouter.ai/api/v1")
VISION_API_KEY = os.getenv("OPEN_ROUTER_KEY")

# NEW: Aggressive OCR mode - tries Vision first before Tesseract
AGGRESSIVE_VISION_MODE = os.getenv("AGGRESSIVE_VISION_MODE", "true").lower() == "true"

# NEW: Hybrid PDF mode - combines text extraction + OCR for mixed PDFs
# When enabled, forces OCR on pages with insufficient text even if some text was extracted
HYBRID_PDF_MODE = os.getenv("HYBRID_PDF_MODE", "true").lower() == "true"

# Thresholds for detecting insufficient text extraction
MIN_CHARS_PER_PAGE = int(os.getenv("MIN_CHARS_PER_PAGE", "200"))  # Minimum chars expected per page
MIN_UNIQUE_WORDS_RATIO = float(os.getenv("MIN_UNIQUE_WORDS_RATIO", "0.3"))  # Ratio of unique words to total
MAX_REPETITION_RATIO = float(os.getenv("MAX_REPETITION_RATIO", "0.7"))  # Max allowed repetition across pages


def _extract_text_with_vision(img: Image.Image, page_index: int = 0) -> Optional[str]:
    """
    Extract text from image using local vision model (LLaVA, etc.) via Ollama.
    This is more accurate than Tesseract for screenshots, styled text, and complex layouts.
    """
    if not VISION_OCR_ENABLED:
        return None
        
    try:
        import httpx
        
        # Convert PIL Image to base64
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
        
        # Call OpenRouter vision model with improved prompt
        headers = {
            "Authorization": f"Bearer {VISION_API_KEY}",
            "Content-Type": "application/json"
        }
        
        response = httpx.post(
            f"{VISION_BASE_URL}/chat/completions",
            headers=headers,
            json={
                "model": VISION_MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    "You are a precise OCR system. Extract ALL visible text from this image.\n\n"
                                    "CRITICAL RULES:\n"
                                    "1. Extract EVERY single word, number, and punctuation mark\n"
                                    "2. Maintain original numbering (1., 2., 3., etc.)\n"
                                    "3. Keep all questions complete - don't truncate or summarize\n"
                                    "4. Include headers, titles, and subtitles\n"
                                    "5. Preserve line breaks between distinct sections\n"
                                    "6. Do NOT add explanations or commentary\n"
                                    "7. Output ONLY the extracted text\n\n"
                                    "Begin extraction:"
                                )
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{img_base64}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 2000
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            text = result["choices"][0]["message"]["content"].strip()
            if text and len(text) > 20:  # Minimum viable text length
                print(f"[Vision OCR] ✅ Page {page_index}: Extracted {len(text)} chars with {VISION_MODEL}")
                return text
            else:
                print(f"[Vision OCR] ⚠️ Page {page_index}: Too short response ({len(text)} chars)")
        else:
            print(f"[Vision OCR] ❌ API error: {response.status_code}")
            
    except ImportError:
        print("[Vision OCR] ⚠️ httpx not installed, skipping vision OCR")
    except httpx.ConnectError:
        print(f"[Vision OCR] ❌ Cannot connect to Ollama at {OLLAMA_BASE_URL}")
    except Exception as e:
        print(f"[Vision OCR] ❌ Error: {e}")
    
    return None


def _is_poor_ocr_result(text: str) -> bool:
    """Check if Tesseract OCR result is likely poor quality."""
    if not text or len(text) < 50:
        return True
    # High ratio of special characters or very short words suggests poor OCR
    words = text.split()
    if len(words) < 5:
        return True
    short_words = sum(1 for w in words if len(w) <= 2)
    if short_words / len(words) > 0.5:  # More than 50% very short words
        return True
    return False


def _analyze_extraction_quality(docs: List[Document]) -> Tuple[bool, str]:
    """
    Analyze if text extraction was sufficient or if OCR is needed.
    
    Returns:
        Tuple of (is_sufficient, reason)
    """
    if not docs:
        return False, "no_documents"
    
    total_chars = sum(len(d.page_content or "") for d in docs)
    avg_chars_per_page = total_chars / len(docs) if docs else 0
    
    # Check 1: Average characters per page
    if avg_chars_per_page < MIN_CHARS_PER_PAGE:
        return False, f"insufficient_text (avg {avg_chars_per_page:.0f} chars/page < {MIN_CHARS_PER_PAGE})"
    
    # Check 2: Content repetition across pages (detects header/footer only extraction)
    all_text = " ".join(d.page_content or "" for d in docs)
    words = all_text.lower().split()
    if words:
        word_counts = Counter(words)
        total_words = len(words)
        unique_words = len(word_counts)
        unique_ratio = unique_words / total_words if total_words > 0 else 0
        
        # If unique word ratio is too low, content is likely repetitive boilerplate
        if unique_ratio < MIN_UNIQUE_WORDS_RATIO:
            return False, f"repetitive_content (unique ratio {unique_ratio:.2f} < {MIN_UNIQUE_WORDS_RATIO})"
    
    # Check 3: Cross-page repetition (same content on multiple pages)
    page_contents = [d.page_content.strip() for d in docs if d.page_content]
    if len(page_contents) > 1:
        content_counts = Counter(page_contents)
        most_common_count = content_counts.most_common(1)[0][1] if content_counts else 0
        repetition_ratio = most_common_count / len(page_contents)
        
        if repetition_ratio > MAX_REPETITION_RATIO:
            return False, f"duplicate_pages ({repetition_ratio:.0%} pages have same content)"
    
    # Check 4: Detect if text looks like metadata/headers only
    combined = all_text.lower()
    metadata_indicators = ["linkedin", "http", "www.", "@", "senior", "engineer", "page"]
    metadata_word_count = sum(combined.count(indicator) for indicator in metadata_indicators)
    total_word_count = len(words)
    
    if total_word_count > 0 and metadata_word_count / total_word_count > 0.3:
        return False, f"metadata_only (high ratio of metadata indicators)"
    
    return True, "sufficient"


def _needs_ocr_enhancement(docs: List[Document]) -> Tuple[bool, str]:
    """
    Determine if documents need OCR enhancement.
    
    Returns:
        Tuple of (needs_ocr, reason)
    """
    is_sufficient, reason = _analyze_extraction_quality(docs)
    if not is_sufficient:
        return True, reason
    return False, "text_extraction_adequate"


def _merge_text_and_ocr(text_docs: List[Document], ocr_docs: List[Document]) -> List[Document]:
    """
    Merge text-extracted documents with OCR results, preferring longer/richer content.
    """
    if not text_docs:
        return ocr_docs
    if not ocr_docs:
        return text_docs
    
    merged = []
    max_pages = max(len(text_docs), len(ocr_docs))
    
    for i in range(max_pages):
        text_doc = text_docs[i] if i < len(text_docs) else None
        ocr_doc = ocr_docs[i] if i < len(ocr_docs) else None
        
        text_content = (text_doc.page_content or "").strip() if text_doc else ""
        ocr_content = (ocr_doc.page_content or "").strip() if ocr_doc else ""
        
        # Choose the richer content, or combine if both have unique info
        if len(ocr_content) > len(text_content) * 1.5:
            # OCR found significantly more content
            chosen_doc = ocr_doc
            method = "ocr_preferred"
        elif len(text_content) > len(ocr_content) * 1.5:
            # Text extraction found significantly more
            chosen_doc = text_doc
            method = "text_preferred"
        elif ocr_content and text_content:
            # Similar lengths - combine unique content
            combined = text_content
            # Add OCR content that isn't already in text content
            ocr_sentences = set(ocr_content.split('. '))
            text_sentences = set(text_content.split('. '))
            new_sentences = ocr_sentences - text_sentences
            if new_sentences:
                combined += "\n\n" + ". ".join(new_sentences)
            chosen_doc = Document(
                page_content=combined,
                metadata={**(text_doc.metadata if text_doc else {}), "merge_method": "combined"}
            )
            method = "combined"
        else:
            chosen_doc = text_doc if text_doc else ocr_doc
            method = "fallback"
        
        if chosen_doc:
            if "merge_method" not in (chosen_doc.metadata or {}):
                chosen_doc.metadata = {**(chosen_doc.metadata or {}), "merge_method": method}
            merged.append(chosen_doc)
    
    return merged


def _clean_ocr_text(text: str) -> str:
    """Clean and normalize OCR text output."""
    import re
    
    # Remove common OCR artifacts
    text = text.replace('|', 'I')  # Common misread
    text = text.replace('0', 'O')  # In some contexts
    
    # Fix spacing issues
    # Pattern 1: Remove spaces within words that have excessive spacing
    text = re.sub(r'(?<=\w)\s+(?=\w(?:\s+\w){2,})', '', text)
    # Pattern 2: Fix remaining single-letter words followed by spaces
    text = re.sub(r'\b(\w)\s+(?=\w\b)', r'\1', text)
    
    # Normalize multiple spaces
    text = re.sub(r'\s+', ' ', text)
    
    # Fix common numbering issues
    text = re.sub(r'(\d+)\s*\.\s+', r'\1. ', text)  # Normalize "1 ." to "1. "
    
    return text.strip()


def _filter_nonempty(docs: List[Document]) -> List[Document]:
    """Filter out empty documents and normalize text"""
    filtered = []
    for d in docs:
        content = (d.page_content or "").strip()
        if content:
            content = _clean_ocr_text(content)
            if len(content) > 20:  # Minimum viable content length
                filtered.append(Document(page_content=content, metadata=d.metadata))
    return filtered


def _run_ocr_on_pdf(tmp_path: str, filename: str) -> List[Document]:
    """Run OCR on all pages of a PDF file."""
    ocr_docs: List[Document] = []
    try:
        doc = fitz.open(tmp_path)
        for page_index in range(len(doc)):
            page = doc.load_page(page_index)
            # DPI increased to 300 for better OCR accuracy
            pix = page.get_pixmap(dpi=300)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            text = ""
            ocr_method = "unknown"
            
            # Try Vision first if in aggressive mode
            if AGGRESSIVE_VISION_MODE:
                print(f"[OCR] Page {page_index}: Trying Vision model first (aggressive mode)...")
                vision_text = _extract_text_with_vision(img, page_index)
                if vision_text and len(vision_text) > 50:
                    text = vision_text
                    ocr_method = "vision"
                    print(f"[OCR] ✅ Page {page_index}: Vision success ({len(text)} chars)")
            
            # Fallback to Tesseract if Vision didn't work or wasn't used
            if not text:
                try:
                    print(f"[OCR] Page {page_index}: Trying Tesseract...")
                    # Use Tesseract with LSTM engine (--oem 1) for better accuracy
                    # PSM 6 = Assume a single uniform block of text
                    text = pytesseract.image_to_string(
                        img, 
                        config='--oem 1 --psm 6'
                    )
                    text = (text or "").strip()
                    ocr_method = "tesseract"
                    
                    # If Tesseract produced poor results, try Vision as backup
                    if _is_poor_ocr_result(text) and not AGGRESSIVE_VISION_MODE:
                        print(f"[OCR] Page {page_index}: Tesseract result poor, trying Vision model...")
                        vision_text = _extract_text_with_vision(img, page_index)
                        if vision_text:
                            text = vision_text
                            ocr_method = "vision"
                            print(f"[OCR] ✅ Page {page_index}: Vision backup success ({len(text)} chars)")
                except Exception as e:
                    print(f"[Tesseract] ⚠️ Page {page_index} failed: {e}")
            
            if text:
                text = _clean_ocr_text(text)
                ocr_docs.append(Document(
                    page_content=text, 
                    metadata={
                        "page": page_index,
                        "ocr_method": ocr_method,
                        "source": filename
                    }
                ))
                print(f"[OCR] Page {page_index}: Final text length = {len(text)} chars")
            else:
                print(f"[OCR] ⚠️ Page {page_index}: No text extracted")
                
    except Exception as e:
        print(f"[OCR] ❌ OCR failed: {e}")
    
    return ocr_docs


def parse_pdf(upload: UploadFile) -> List[Document]:
    """
    Parse PDF with intelligent hybrid mode that combines text extraction + OCR.
    
    The function:
    1. Tries fast text extraction (PyPDFLoader, PyMuPDFLoader)
    2. Analyzes extraction quality (detects insufficient text, repetition, metadata-only)
    3. If HYBRID_PDF_MODE is enabled and extraction is insufficient, runs OCR
    4. Merges text and OCR results, preferring richer content
    """
    filename = upload.filename if hasattr(upload, 'filename') else "unknown"
    
    # Persist UploadFile to a temporary file path because loaders expect a path
    with tempfile.NamedTemporaryFile(delete=True, suffix=".pdf") as tmp:
        upload.file.seek(0)
        tmp.write(upload.file.read())
        tmp.flush()

        # 1) Try PyPDFLoader (fast, pure-python)
        try:
            pypdf_docs = PyPDFLoader(tmp.name).load()
        except Exception as e:
            print(f"[PDF] PyPDFLoader failed, will try PyMuPDFLoader: {e}")
            pypdf_docs = []

        pypdf_docs = _filter_nonempty(pypdf_docs)
        
        # 2) Try PyMuPDFLoader as fallback/alternative
        try:
            pymupdf_docs = PyMuPDFLoader(tmp.name).load()
        except Exception as e:
            print(f"[PDF] PyMuPDFLoader failed: {e}")
            pymupdf_docs = []

        pymupdf_docs = _filter_nonempty(pymupdf_docs)
        
        # Choose the better text extraction result
        text_docs = pypdf_docs if len(pypdf_docs) >= len(pymupdf_docs) else pymupdf_docs
        extraction_method = "PyPDFLoader" if len(pypdf_docs) >= len(pymupdf_docs) else "PyMuPDFLoader"
        
        if text_docs:
            print(f"[PDF] Text extracted with {extraction_method}: {len(text_docs)} pages")
            
            # HYBRID MODE: Analyze if extraction is sufficient
            if HYBRID_PDF_MODE:
                needs_ocr, reason = _needs_ocr_enhancement(text_docs)
                
                if needs_ocr:
                    print(f"[PDF] ⚠️ HYBRID MODE: Insufficient text extraction ({reason})")
                    print(f"[PDF] 🔄 Running OCR to enhance content...")
                    
                    ocr_docs = _run_ocr_on_pdf(tmp.name, filename)
                    ocr_docs = _filter_nonempty(ocr_docs)
                    
                    if ocr_docs:
                        total_ocr_chars = sum(len(d.page_content) for d in ocr_docs)
                        total_text_chars = sum(len(d.page_content) for d in text_docs)
                        
                        print(f"[PDF] 📊 Comparison: Text={total_text_chars} chars, OCR={total_ocr_chars} chars")
                        
                        # Merge results
                        merged_docs = _merge_text_and_ocr(text_docs, ocr_docs)
                        merged_chars = sum(len(d.page_content) for d in merged_docs)
                        
                        print(f"[PDF] ✅ HYBRID result: {len(merged_docs)} pages, {merged_chars} chars (improved by {merged_chars - total_text_chars} chars)")
                        return merged_docs
                    else:
                        print(f"[PDF] ⚠️ OCR produced no results, using text extraction")
                else:
                    print(f"[PDF] ✅ Text extraction sufficient ({reason})")
            
            return text_docs

        # 3) No text found - full OCR fallback
        print("[PDF] No text detected; attempting full OCR...")
        ocr_docs = _run_ocr_on_pdf(tmp.name, filename)
        ocr_docs = _filter_nonempty(ocr_docs)
        
        total_chars = sum(len(d.page_content) for d in ocr_docs)
        print(f"[PDF] OCR complete: {len(ocr_docs)} pages, {total_chars} chars")
        return ocr_docs