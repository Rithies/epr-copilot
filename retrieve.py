# retrieve.py — Phase 2, step 4a: query the vector store
# Goal: type a question, get back the nearest chunks of regulation.

import chromadb

# 1. Open the SAME database embed.py created.
#    PersistentClient = "read the vector store that lives on disk in chroma_db/".
client = chromadb.PersistentClient(path="chroma_db")

# 2. Open the SAME collection we filled (our 173 chunks live here).
#    Because we don't pass an embedding function, Chroma reuses its default
#    (the local MiniLM model) — the exact one embed.py used. Same model is
#    essential: the question must be measured with the same ruler as the chunks.
collection = client.get_collection("epr_regulations")

# 3. The question we want answered.
question = "What are the recycling targets for category I plastic?"

# 4. The search. Chroma embeds the question for us, then finds nearest dots.
#    query_texts takes a LIST of questions, so we pass one in a list.
#    n_results=3 → give back the 3 closest chunks.
results = collection.query(
    query_texts=[question],
    n_results=3,
)

# 5. Unpack the answer. Chroma returns one result-list PER question.
#    We asked one question, so we take index [0] of each.
docs  = results["documents"][0]    # the chunk text
metas = results["metadatas"][0]    # the {source, page} labels we attached
dists = results["distances"][0]    # how far each chunk is (smaller = closer)

# 6. Print them so we can SEE what retrieval found.
print(f"\nQuestion: {question}\n")
for rank, (doc, meta, dist) in enumerate(zip(docs, metas, dists), start=1):
    print(f"--- Match {rank}  (distance {dist:.3f}) ---")
    print(f"Source: {meta['source']}  |  page {meta['page']}")
    print(doc[:300].strip())   # first 300 chars so the output stays readable
    print()