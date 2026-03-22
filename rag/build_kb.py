from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain.embeddings.base import Embeddings
from langchain_core.documents import Document
from sentence_transformers import SentenceTransformer
import json, os, pickle

KB_PATH    = "rag/knowledge_base/diseases.json"
FAISS_PATH = "rag/faiss_index"

print("Loading sentence-transformer model...")
embedder = SentenceTransformer("all-MiniLM-L6-v2")

class LocalEmbeddings(Embeddings):
    def embed_documents(self, texts):
        return embedder.encode(texts, show_progress_bar=True).tolist()
    def embed_query(self, text):
        return embedder.encode([text])[0].tolist()

def build_documents(kb: dict) -> list[Document]:
    docs = []
    for disease_key, info in kb.items():
        content = f"""
Disease: {disease_key}
Telugu name: {info['telugu_name']}
Crop: {info['crop']}
Description: {info['description']}
Symptoms: {', '.join(info['symptoms'])}
Treatment: {' | '.join(info['treatment'])}
Prevention: {' | '.join(info['prevention'])}
Severity: {info['severity']}
Spread conditions: {', '.join(info['spread_conditions']) if info['spread_conditions'] else 'None'}
""".strip()
        docs.append(Document(
            page_content=content,
            metadata={
                "disease_key":   disease_key,
                "crop":          info["crop"],
                "severity":      info["severity"],
                "telugu_name":   info["telugu_name"],
            }
        ))
    return docs

print("Loading knowledge base...")
with open(KB_PATH) as f:
    kb = json.load(f)
print(f"Loaded {len(kb)} disease entries")

print("Building documents...")
docs = build_documents(kb)

print("Building FAISS index...")
embeddings = LocalEmbeddings()
vectorstore = FAISS.from_documents(docs, embeddings)

os.makedirs(FAISS_PATH, exist_ok=True)
vectorstore.save_local(FAISS_PATH)
print(f"FAISS index saved to {FAISS_PATH}")
print("Knowledge base built successfully!")