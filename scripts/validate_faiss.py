#!/usr/bin/env python3
"""Validate FAISS artifacts (checksums + files). Run from repo root."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.chdir(ROOT)


def main() -> int:
    try:
        from rag.retriever import _verify_faiss_artifacts

        _verify_faiss_artifacts()
    except Exception as e:
        print(f"FAISS validation failed: {e}", file=sys.stderr)
        return 1
    print("FAISS artifacts OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
