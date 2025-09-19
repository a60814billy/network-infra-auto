#!/usr/bin/env bash
set -euo pipefail

# === 基本設定 ===
BASE="${DISPATCH_BASE:-http://127.0.0.1:8000}"

# 參數：version vendor module cfg_path
VERSION="${1:-v1}"
VENDOR="${2:-cisco}"
MODULE="${3:-c8k}"

FILENAME="cfg/tndo-c8k-1.cfg"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(realpath "$SCRIPT_DIR/../../..")"
# echo "🏠 專案根目錄：$ROOT_DIR"
CFG_PATH="$ROOT_DIR/$FILENAME"

# === 檢查檔案 ===
if [[ ! -r "$CFG_PATH" ]]; then
  echo "❌ 找不到或無法讀取檔案：$CFG_PATH" >&2
  exit 1
fi

# echo "➡️  送出請求：$BASE/request/$VERSION/$VENDOR/$MODULE"
# echo "📄 上傳檔案：$(realpath "$CFG_PATH")"

# === 送出檔案（multipart/form-data）===
RESP="$(curl -sS -f -X POST "$BASE/request/$VERSION/$VENDOR/$MODULE" \
  -F "file=@${CFG_PATH}")"

# echo
# echo "✅ 伺服器回應："
# echo "$RESP" | jq .
if command -v jq >/dev/null 2>&1; then
  TID="$(echo "$RESP" | jq -r '.id // empty')"
  if [[ -n "${TID:-}" ]]; then
    # echo "🔎 查詢結果："
    echo "curl \"$BASE/result/$TID\" | jq ."
  fi
fi
