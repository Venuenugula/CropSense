import hashlib
import json
import os
from typing import Any

import faiss
from sentence_transformers import SentenceTransformer

FAISS_PATH = "rag/faiss_index"
KB_PATH = "rag/knowledge_base/diseases.json"
FAISS_INDEX_FILE = os.path.join(FAISS_PATH, "index.faiss")
FAISS_META_FILE = os.path.join(FAISS_PATH, "metadata.json")
FAISS_CHECKSUM_FILE = os.path.join(FAISS_PATH, "checksums.json")

embedder = None
_faiss_index = None
_faiss_metadata = None


def _get_embedder() -> SentenceTransformer:
    global embedder
    if embedder is None:
        embedder = SentenceTransformer("all-MiniLM-L6-v2")
    return embedder


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _verify_faiss_artifacts() -> None:
    """Fail closed if FAISS artifacts are missing or tampered."""
    if not os.path.exists(FAISS_CHECKSUM_FILE):
        raise FileNotFoundError(
            f"Missing checksum manifest: {FAISS_CHECKSUM_FILE}. "
            "Rebuild KB with rag/build_kb.py"
        )

    with open(FAISS_CHECKSUM_FILE, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    files = manifest.get("files", {})
    required = ["index.faiss", "metadata.json"]
    for name in required:
        expected = files.get(name)
        if not expected:
            raise ValueError(f"Checksum entry missing for {name}")
        artifact_path = os.path.join(FAISS_PATH, name)
        if not os.path.exists(artifact_path):
            raise FileNotFoundError(f"Missing FAISS artifact: {artifact_path}")
        actual = _sha256_file(artifact_path)
        if actual != expected:
            raise ValueError(f"Checksum mismatch for {name}")


def _load_faiss_if_needed() -> None:
    global _faiss_index, _faiss_metadata
    if _faiss_index is not None and _faiss_metadata is not None:
        return

    _verify_faiss_artifacts()
    _faiss_index = faiss.read_index(FAISS_INDEX_FILE)
    with open(FAISS_META_FILE, "r", encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
    _faiss_metadata = data.get("records", [])

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
    try:
        _load_faiss_if_needed()
        q_vec = _get_embedder().encode([q], show_progress_bar=False)
        q_vec = q_vec.astype("float32")
        _, indices = _faiss_index.search(q_vec, k=1)
        if len(indices) and indices[0][0] >= 0:
            rec = _faiss_metadata[indices[0][0]]
            key = rec.get("disease_key")
            return KB.get(key, {})
    except Exception as e:
        # Keep direct-key retrieval resilient even if FAISS artifacts are absent.
        print(f"FAISS fallback unavailable: {e}")
    return {}

def format_for_llm(disease_info: dict) -> str:
    """Format disease info as clean text for LLM prompt."""
    if not disease_info:
        return "No information found for this disease."
    return f"""
Disease: {disease_info.get('telugu_name', '')} ({disease_info.get('crop', '')})
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