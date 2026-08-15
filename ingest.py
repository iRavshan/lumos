"""
Script to ingest all markdown documents into ChromaDB.
Uses Google Gemini embedding API (google.genai).

Usage:
    cd src
    python ingest.py
"""
import os
import re
import sys
import glob

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

from google import genai
from dotenv import load_dotenv
import chromadb

load_dotenv()

# ── Config ───────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(BASE_DIR, 'documents')
CHROMA_DIR = os.path.join(BASE_DIR, 'chroma_db')

GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY', '')
client = genai.Client(api_key=GOOGLE_API_KEY)


def get_embedding(text: str) -> list[float]:
    """Get embedding from Google Gemini API."""
    result = client.models.embed_content(
        model="models/gemini-embedding-001",
        contents=text,
    )
    return result.embeddings[0].values


import time
def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Get embeddings for a batch of texts."""
    embeddings = []
    # Gemini free tier limits to 100 inputs per minute total, even in batches.
    batch_size = 90
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        
        success = False
        while not success:
            try:
                result = client.models.embed_content(
                    model="models/gemini-embedding-001",
                    contents=batch,
                )
                for emb in result.embeddings:
                    embeddings.append(emb.values)
                print(f"   -> {min(i + batch_size, len(texts))}/{len(texts)} chunk embedding tayyor")
                success = True
                
                # If there are more chunks left, we MUST sleep for a minute to reset the quota
                if i + batch_size < len(texts):
                    print("   -> Kvota limitini kutish (65 soniya)...")
                    time.sleep(65)
                    
            except Exception as e:
                print(f"Xato (API limiti): {e}")
                print("   -> 65 soniya kutib, qayta urinib ko'riladi...")
                time.sleep(65)

    return embeddings


def split_into_chunks(text: str, max_chars: int = 800) -> list[str]:
    """
    Split a markdown document into semantically meaningful chunks.
    """
    sections = re.split(r'\n(?=#{1,3}\s)', text)

    chunks = []
    for section in sections:
        section = section.strip()
        if not section:
            continue

        if len(section) <= max_chars:
            chunks.append(section)
        else:
            paragraphs = re.split(r'\n(?=\d+\.)', section)
            current_chunk = ""
            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue
                if len(current_chunk) + len(para) + 1 <= max_chars:
                    current_chunk = (current_chunk + "\n" + para).strip()
                else:
                    if current_chunk:
                        chunks.append(current_chunk)
                    if len(para) > max_chars:
                        sentences = re.split(r'(?<=[.;])\s+', para)
                        sub_chunk = ""
                        for sent in sentences:
                            if len(sub_chunk) + len(sent) + 1 <= max_chars:
                                sub_chunk = (sub_chunk + " " + sent).strip()
                            else:
                                if sub_chunk:
                                    chunks.append(sub_chunk)
                                sub_chunk = sent
                        if sub_chunk:
                            current_chunk = sub_chunk
                        else:
                            current_chunk = ""
                    else:
                        current_chunk = para
            if current_chunk:
                chunks.append(current_chunk)

    return chunks


def ingest():
    if not GOOGLE_API_KEY:
        print("[XATO] GOOGLE_API_KEY .env faylda topilmadi!")
        return

    print(f"[1/4] ChromaDB yaratish: {CHROMA_DIR}")
    chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)

    try:
        chroma_client.delete_collection("grant_docs")
        print("   -> Eski kolleksiya o'chirildi")
    except Exception:
        pass

    collection = chroma_client.create_collection(
        name="grant_docs",
        metadata={"hnsw:space": "cosine"},
    )

    md_files = glob.glob(os.path.join(DOCS_DIR, '*.md'))
    if not md_files:
        print("[XATO] Hujjatlar topilmadi (.md fayllar)")
        return
        
    all_chunks = []
    all_metadatas = []
    
    print(f"[2/4] Hujjatlarni o'qish va chunklarga bo'lish...")
    for file_path in md_files:
        filename = os.path.basename(file_path)
        print(f"   -> O'qilyapti: {filename}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
            
        chunks = split_into_chunks(text)
        print(f"      {len(chunks)} ta chunk yaratildi")
        
        for i, chunk in enumerate(chunks):
            all_chunks.append(chunk)
            all_metadatas.append({"source": filename, "chunk_index": i})

    print(f"[3/4] Jami {len(all_chunks)} ta chunk uchun Gemini orqali embeddinglarni hisoblash...")
    all_embeddings = get_embeddings_batch(all_chunks)

    print("[4/4] ChromaDB ga saqlash...")
    ids = [f"chunk_{i}" for i in range(len(all_chunks))]
    
    collection.add(
        ids=ids,
        documents=all_chunks,
        embeddings=all_embeddings,
        metadatas=all_metadatas,
    )

    print(f"[TAYYOR] {len(all_chunks)} ta chunk ChromaDB ga muvaffaqiyatli saqlandi.")

    # Quick test
    test_query = "Talabalar o'qishini ko'chirish qanday amalga oshiriladi?"
    test_embedding = get_embedding(test_query)
    results = collection.query(query_embeddings=[test_embedding], n_results=2)
    print(f"\n[TEST] So'rov: '{test_query}'")
    for i, doc in enumerate(results['documents'][0]):
        print(f"   Natija {i+1}: {doc[:150]}...")


if __name__ == '__main__':
    ingest()
