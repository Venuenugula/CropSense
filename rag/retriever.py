from langchain_community.vectorstores import FAISS
from langchain.embeddings.base import Embeddings
from sentence_transformers import SentenceTransformer
import json

FAISS_PATH = "rag/faiss_index"
KB_PATH    = "rag/knowledge_base/diseases.json"

embedder = SentenceTransformer("all-MiniLM-L6-v2")

class LocalEmbeddings(Embeddings):
    def embed_documents(self, texts):
        return embedder.encode(texts, show_progress_bar=False).tolist()
    def embed_query(self, text):
        return embedder.encode([text])[0].tolist()

vectorstore = FAISS.load_local(
    FAISS_PATH,
    LocalEmbeddings(),
    allow_dangerous_deserialization=True
)

with open(KB_PATH) as f:
    KB = json.load(f)

def get_disease_info(disease_key: str) -> dict:
    """Get full structured info for a disease directly from KB."""
    return KB.get(disease_key, {})

def retrieve_treatment(disease_key: str, query: str = None) -> dict:
    """
    Primary: direct KB lookup by disease key.
    Fallback: RAG similarity search if key not found.
    Returns structured disease info dict.
    """
    if disease_key in KB:
        return KB[disease_key]

    # Fallback — similarity search
    q = query or disease_key.replace("___", " ").replace("_", " ")
    docs = vectorstore.similarity_search(q, k=1)
    if docs:
        key = docs[0].metadata.get("disease_key")
        return KB.get(key, {})
    return {}

def format_for_llm(disease_info: dict) -> str:
    """Format disease info as clean text for LLM prompt."""
    if not disease_info:
        return "No information found for this disease."
    return f"""
Disease: {disease_info.get('disease_key', 'Unknown')}
Crop: {disease_info.get('crop', '')}
Severity: {disease_info.get('severity', '')}
Symptoms: {', '.join(disease_info.get('symptoms', []))}
Treatment steps: {' | '.join(disease_info.get('treatment', []))}
Prevention: {' | '.join(disease_info.get('prevention', []))}
Spreads in: {', '.join(disease_info.get('spread_conditions', []))}
""".strip()


if __name__ == "__main__":
    # Test retrieval
    test_disease = "Tomato___Late_blight"
    info = retrieve_treatment(test_disease)
    print(f"Disease: {test_disease}")
    print(f"Telugu name: {info.get('telugu_name')}")
    print(f"Severity: {info.get('severity')}")
    print(f"Treatment: {info.get('treatment')}")
    print("\nFormatted for LLM:")
    print(format_for_llm(info))