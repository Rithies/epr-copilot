"""
embed.py  —  Phase 2, Step 3: embed the chunks into ChromaDB.

What this does:
  1. Gets the 173 labelled chunks from ingest.py (we reuse that work).
  2. Hands their text to ChromaDB, which turns each into a vector locally.
  3. Stores vectors + text + labels in a collection saved to disk.

After this runs once, the vectors live in a folder (chroma_db/) and we
don't need to re-embed every time — we just open the collection and search.
"""

import chromadb
from ingest import ingest, CORE_DOCS

# Where ChromaDB will save the vectors on disk. A plain folder.
DB_DIR = "chroma_db"
COLLECTION_NAME = "epr_regulations"


def build_index():
    # 1. Get the chunks. We call the function we already wrote and trust.
    print("Chunking the 3 core docs...")
    chunks = ingest(CORE_DOCS)
    print(f"Got {len(chunks)} chunks.\n")

    # 2. Open a ChromaDB client that PERSISTS to disk (vs. vanishing in memory).
    client = chromadb.PersistentClient(path=DB_DIR)

    # 3. Start fresh: if a collection with this name exists, delete it first,
    #    so re-running doesn't pile up duplicate copies of the same chunks.
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass  # nothing to delete on the first run; that's fine

    # 4. Create the collection. This is the "table" that holds our vectors.
    collection = client.create_collection(COLLECTION_NAME)

    # 5. ChromaDB's add() wants three parallel lists, all the same length:
    #    - documents: the raw text (Chroma embeds these for us)
    #    - metadatas: the labels we attach to each (source + page) -> citations
    #    - ids:       a unique string id per chunk (Chroma requires it)
    documents = [c["text"] for c in chunks]
    metadatas = [{"source": c["source"], "page": c["page"]} for c in chunks]
    ids = [f"chunk-{i}" for i in range(len(chunks))]

    # 6. Add everything. Behind the scenes Chroma runs the local MiniLM model
    #    on each document, producing a 384-number vector, and stores it.
    print("Embedding + storing in ChromaDB (first run downloads the model)...")
    collection.add(documents=documents, metadatas=metadatas, ids=ids)

    print(f"Done. {collection.count()} chunks embedded and saved to '{DB_DIR}/'.")


if __name__ == "__main__":
    build_index()
