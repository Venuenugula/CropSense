#!/usr/bin/env bash
# CropSense bot entrypoint for Render and other PaaS:
# - Downloads ONNX + class_names.json from Hugging Face if missing
# - Optionally downloads FAISS index bundle from the same repo
# - Validates FAISS checksums before starting the bot
#
# Env (optional):
#   HF_MODEL_REPO     default: VenuEnugula/cropsense_diseasedetection
#   HF_REVISION       default: main
#   MODEL_URL         if set, download ONNX from this URL instead of HF repo path
#   SKIP_MODEL_DOWNLOAD  if non-empty, skip ONNX/class_names download when files exist
#   DOWNLOAD_FAISS_FROM_HF  default 1; set 0 to skip HF FAISS download (use committed artifacts)
#   HF_TOKEN          Hugging Face token for private/gated files (Authorization: Bearer)
#   WEBHOOK_URL / PORT / TELEGRAM_BOT_TOKEN — passed through to bot

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

HF_MODEL_REPO="${HF_MODEL_REPO:-VenuEnugula/cropsense_diseasedetection}"
HF_REVISION="${HF_REVISION:-main}"
BASE="https://huggingface.co/${HF_MODEL_REPO}/resolve/${HF_REVISION}"
DOWNLOAD_FAISS_FROM_HF="${DOWNLOAD_FAISS_FROM_HF:-1}"

# Safe download: returns 0 on success, 1 on failure (does not trigger set -e exit).
curl_get() {
  local url="$1"
  local dest="$2"
  if [[ -n "${HF_TOKEN:-}" ]]; then
    if curl -fL --retry 3 --retry-delay 2 \
      -H "Authorization: Bearer ${HF_TOKEN}" \
      -o "$dest" "$url"; then
      return 0
    fi
  else
    if curl -fL --retry 3 --retry-delay 2 -o "$dest" "$url"; then
      return 0
    fi
  fi
  return 1
}

mkdir -p model rag/faiss_index

echo "[start_bot] Repo root: $ROOT"
echo "[start_bot] Env check: PORT=${PORT:-unset}, WEBHOOK_URL=${WEBHOOK_URL:-unset}, TOKEN_SET=$([[ -n "${TELEGRAM_BOT_TOKEN:-}" ]] && echo yes || echo no)"

# Render Web Services must bind to a port; without WEBHOOK_URL the bot falls back to polling.
if [[ -n "${RENDER:-}" && -z "${WEBHOOK_URL:-}" ]]; then
  echo "[start_bot] ERROR: WEBHOOK_URL is required on Render Web Service."
  echo "Set WEBHOOK_URL to https://<your-service>.onrender.com (no trailing slash)."
  exit 1
fi

# --- ONNX model ---
ONNX_DEST="model/crop_disease.onnx"
ONNX_DATA_DEST="model/crop_disease.onnx.data"
if [[ -n "${SKIP_MODEL_DOWNLOAD:-}" && -f "$ONNX_DEST" ]]; then
  echo "[start_bot] SKIP_MODEL_DOWNLOAD set and $ONNX_DEST exists — skipping ONNX download"
elif [[ -n "${MODEL_URL:-}" ]]; then
  echo "[start_bot] Downloading ONNX from MODEL_URL"
  curl_get "$MODEL_URL" "$ONNX_DEST" || { echo "[start_bot] ERROR: ONNX download failed"; exit 1; }
else
  if [[ ! -f "$ONNX_DEST" ]]; then
    echo "[start_bot] Downloading ONNX from Hugging Face: ${BASE}/crop_disease.onnx"
    curl_get "${BASE}/crop_disease.onnx" "$ONNX_DEST" || { echo "[start_bot] ERROR: ONNX download failed"; exit 1; }
  else
    echo "[start_bot] $ONNX_DEST already present"
  fi
fi

# Optional companion file for ONNX models saved with external data tensors.
if [[ ! -f "$ONNX_DATA_DEST" ]]; then
  echo "[start_bot] Trying ONNX external data: ${BASE}/crop_disease.onnx.data"
  if curl_get "${BASE}/crop_disease.onnx.data" "$ONNX_DATA_DEST"; then
    echo "[start_bot] Downloaded $ONNX_DATA_DEST"
  else
    rm -f "$ONNX_DATA_DEST" 2>/dev/null || true
    echo "[start_bot] ONNX external data file not found on HF (continuing)"
  fi
fi

# If ONNX references external tensors, the .onnx.data file is mandatory.
if python3 - <<'PY'
import sys
try:
    import onnx
    m = onnx.load("model/crop_disease.onnx", load_external_data=False)
    needs = any(getattr(t, "external_data", None) for t in m.graph.initializer)
    sys.exit(0 if needs else 1)
except Exception:
    # If we cannot inspect, don't hard-fail here; runtime will validate.
    sys.exit(1)
PY
then
  if [[ ! -f "$ONNX_DATA_DEST" ]]; then
    echo "[start_bot] ERROR: model/crop_disease.onnx requires external data file model/crop_disease.onnx.data"
    echo "Upload crop_disease.onnx.data to https://huggingface.co/${HF_MODEL_REPO} (same path as ONNX), or commit it in model/"
    exit 1
  fi
fi

# --- class_names.json (same repo) ---
JSON_DEST="model/class_names.json"
if [[ -z "${SKIP_MODEL_DOWNLOAD:-}" || ! -f "$JSON_DEST" ]]; then
  if [[ ! -f "$JSON_DEST" ]]; then
    echo "[start_bot] Downloading class_names.json from Hugging Face"
    if ! curl_get "${BASE}/class_names.json" "$JSON_DEST"; then
      echo "[start_bot] WARN: could not download class_names.json from HF; ensure it exists in repo or under model/"
    fi
  fi
fi

# --- FAISS artifacts (optional HF path: rag/faiss_index/*) ---
if [[ "$DOWNLOAD_FAISS_FROM_HF" == "1" ]]; then
  for f in index.faiss metadata.json checksums.json; do
    dest="rag/faiss_index/$f"
    if [[ ! -f "$dest" ]]; then
      url="${BASE}/rag/faiss_index/${f}"
      echo "[start_bot] Trying FAISS file: $url"
      if curl_get "$url" "$dest"; then
        echo "[start_bot] Downloaded $dest"
      else
        echo "[start_bot] WARN: $f not found at HF path — commit artifacts or run: python rag/build_kb.py"
        rm -f "$dest" 2>/dev/null || true
      fi
    fi
  done
fi

echo "[start_bot] Validating FAISS artifacts..."
if ! python3 -u scripts/validate_faiss.py; then
  echo "[start_bot] ERROR: FAISS validation failed."
  echo "  Fix: upload rag/faiss_index/{index.faiss,metadata.json,checksums.json} to"
  echo "       https://huggingface.co/${HF_MODEL_REPO} under rag/faiss_index/"
  echo "  Or:  run locally: python rag/build_kb.py && commit the rag/faiss_index/ folder"
  exit 1
fi

echo "[start_bot] Starting bot..."
exec python3 -m bot.bot
