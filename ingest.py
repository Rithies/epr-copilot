"""
ingest.py  —  Phase 2, Step 2: chunk the regulation PDFs.

What this does:
  1. Reads each PDF, page by page.
  2. Splits each page's text into small, overlapping chunks.
  3. Labels every chunk with its source file and page number.

Why labels matter:
  The (source, page) on each chunk is what lets the co-pilot CITE its answer
  later. No label = no citation = a guess. We refuse to guess.

Run it:
  python3 ingest.py --test     # FAQs only, prints a few chunks so you can SEE them
  python3 ingest.py            # all 3 core docs, prints a summary
"""

import sys
from pypdf import PdfReader

# --- settings you can tune later ---
CHUNK_SIZE = 800      # characters per chunk
OVERLAP = 100         # characters that repeat between neighbouring chunks
UPLOADS = "regulations"

# The 3 core docs. A "label" is the friendly name we'll show in citations.
# "pages" is OPTIONAL: (first, last) inclusive, 1-based. If absent, take all pages.
# The EPR Guidelines PDF is bilingual: Hindi pp.1-20, English pp.21-34.
# We keep only the English half so retrieval isn't polluted with Hindi chunks.
CORE_DOCS = [
    {"file": "FAQs.pdf",                     "label": "EPR FAQs"},
    {"file": "PWM_Rules.pdf",                "label": "PWM Rules 2016"},
    {"file": "PWM-Amendment-Rules-2022.pdf", "label": "EPR Guidelines 2022", "pages": (21, 34)},
]


def chunk_text(text, size=CHUNK_SIZE, overlap=OVERLAP):
    """Slice one page's text into overlapping windows.

    We step forward by (size - overlap) each time, so the tail of one
    chunk reappears at the head of the next. That overlap stops a rule
    from being cut cleanly in half across a boundary.
    """
    chunks = []
    start = 0
    step = size - overlap            # how far we move the window each loop
    while start < len(text):
        piece = text[start:start + size]
        # skip near-empty slices (blank pages, page-number-only pages)
        if piece.strip():
            chunks.append(piece)
        start += step
    return chunks


def ingest(docs):
    """Turn a list of docs into a flat list of labelled chunk dicts."""
    all_chunks = []
    for doc in docs:
        path = f"{UPLOADS}/{doc['file']}"
        reader = PdfReader(path)
        doc_chunk_count = 0
        page_range = doc.get("pages")   # None, or (first, last) inclusive
        for page_num, page in enumerate(reader.pages, start=1):  # pages count from 1
            # if a range is set, skip pages outside it
            if page_range and not (page_range[0] <= page_num <= page_range[1]):
                continue
            page_text = page.extract_text() or ""
            for piece in chunk_text(page_text):
                all_chunks.append({
                    "text": piece,
                    "source": doc["label"],   # e.g. "EPR Guidelines 2022"
                    "page": page_num,
                })
                doc_chunk_count += 1
        print(f"  {doc['label']:<22} {len(reader.pages):>3} pages -> {doc_chunk_count:>4} chunks")
    return all_chunks


if __name__ == "__main__":
    test_mode = "--test" in sys.argv

    if test_mode:
        print("TEST MODE: FAQs only\n")
        chunks = ingest([CORE_DOCS[0]])   # just the FAQs
        print(f"\nTotal chunks: {len(chunks)}\n")
        print("=" * 60)
        print("First 3 chunks, so you can see what a 'card' looks like:")
        print("=" * 60)
        for i, c in enumerate(chunks[:3]):
            print(f"\n--- chunk {i}  [{c['source']}, page {c['page']}] ---")
            print(c["text"][:300].strip())
    else:
        print("Ingesting 3 core docs:\n")
        chunks = ingest(CORE_DOCS)
        print(f"\nTotal chunks across all 3 docs: {len(chunks)}")
