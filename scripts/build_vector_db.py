"""
Build ChromaDB vector database from FAQ text file.
Run this script to initialize the RAG knowledge base before running the app.

Uses ChromaDB's built-in local embedding model (all-MiniLM-L6-v2 via ONNX),
so no API key is required.
"""

import sys
from pathlib import Path

# --- COLAB/LINUX FIX ---
try:
    __import__("pysqlite3")
    sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
except ImportError:
    pass
# -----------------------

import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

# Paths
script_dir = Path(__file__).parent
project_root = script_dir.parent
data_dir = project_root / "data"
db_path = data_dir / "chroma_db"
file_path = data_dir / "faq.txt"

# 1. Read and chunk the FAQ
try:
    with open(file_path, "r") as f:
        text = f.read()
except FileNotFoundError:
    print(f"❌ Error: Could not find {file_path}. Make sure it exists!")
    sys.exit(1)

chunks = [chunk.strip() for chunk in text.split("\n\n") if chunk.strip()]

# 2. Setup ChromaDB with local embedding model
chroma_client = chromadb.PersistentClient(path=str(db_path))
collection_name = "ohm_policies"

try:
    chroma_client.delete_collection(name=collection_name)
    print(f"🗑️  Deleted old collection: {collection_name}")
except Exception:
    pass

collection = chroma_client.create_collection(
    name=collection_name,
    embedding_function=DefaultEmbeddingFunction(),
)

# 3. Embed and store
ids = [f"id_{i}" for i in range(len(chunks))]
print(f"🚀 Embedding {len(chunks)} policy sections (local model, no API key needed)...")
collection.add(documents=chunks, ids=ids)

print(f"✅ Success! Knowledge base built at: {db_path}")
