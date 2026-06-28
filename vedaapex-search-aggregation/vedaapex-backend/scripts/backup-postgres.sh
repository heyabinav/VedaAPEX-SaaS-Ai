#!/usr/bin/env sh
set -eu

: "${DATABASE_URL:?DATABASE_URL is required}"

if ! command -v pg_dump >/dev/null 2>&1; then
  echo "pg_dump is required and was not found in PATH." >&2
  exit 1
fi

OUTPUT_DIR="${1:-./backups}"
mkdir -p "$OUTPUT_DIR"

TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_FILE="$OUTPUT_DIR/vedaapex-$TIMESTAMP.dump"

pg_dump --format=custom --file "$BACKUP_FILE" "$DATABASE_URL"

echo "Backup created at $BACKUP_FILE"
