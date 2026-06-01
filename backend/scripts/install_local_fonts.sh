#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: backend/scripts/install_local_fonts.sh /path/to/font-files" >&2
  exit 2
fi

SOURCE_DIR="$1"
TARGET_DIR="${HOME}/.local/share/fonts/waraq"

if [[ ! -d "$SOURCE_DIR" ]]; then
  echo "Font source directory does not exist: $SOURCE_DIR" >&2
  exit 2
fi

mkdir -p "$TARGET_DIR"

shopt -s nullglob
fonts=(
  "$SOURCE_DIR"/*.ttf
  "$SOURCE_DIR"/*.TTF
  "$SOURCE_DIR"/*.otf
  "$SOURCE_DIR"/*.OTF
  "$SOURCE_DIR"/*.ttc
  "$SOURCE_DIR"/*.TTC
)

if [[ ${#fonts[@]} -eq 0 ]]; then
  echo "No .ttf, .otf, or .ttc font files found in: $SOURCE_DIR" >&2
  exit 2
fi

cp -f "${fonts[@]}" "$TARGET_DIR"/
fc-cache -f "$TARGET_DIR"

echo "Installed ${#fonts[@]} font file(s) into $TARGET_DIR"
echo
echo "Current matches:"
fc-match "KFGQPC Uthmanic Script HAFS"
fc-match "Traditional Naskh"
fc-match "Noto Sans Arabic"
fc-match "Calibri"
