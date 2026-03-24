#!/usr/bin/env python3
"""Validate FAISS artifacts quickly using stdlib only."""
import hashlib
import json
import os
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAISS_PATH = os.path.join(ROOT, "rag", "faiss_index")
CHECKSUMS = os.path.join(FAISS_PATH, "checksums.json")


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    if not os.path.exists(CHECKSUMS):
        print(f"FAISS validation failed: missing {CHECKSUMS}", file=sys.stderr)
        return 1

    try:
        with open(CHECKSUMS, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    except Exception as e:
        print(f"FAISS validation failed: invalid checksums.json ({e})", file=sys.stderr)
        return 1

    files = manifest.get("files", {})
    required = ["index.faiss", "metadata.json"]
    for name in required:
        expected = files.get(name)
        if not expected:
            print(f"FAISS validation failed: checksum entry missing for {name}", file=sys.stderr)
            return 1
        path = os.path.join(FAISS_PATH, name)
        if not os.path.exists(path):
            print(f"FAISS validation failed: missing {path}", file=sys.stderr)
            return 1
        actual = sha256_file(path)
        if actual != expected:
            print(f"FAISS validation failed: checksum mismatch for {name}", file=sys.stderr)
            return 1

    print("FAISS artifacts OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
