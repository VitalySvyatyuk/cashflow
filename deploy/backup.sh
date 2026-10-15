#!/usr/bin/env bash
# Резервная копия базы и загруженных картинок; хранит последние 7 дней.
set -euo pipefail
DIR=/opt/cashflow/backups
mkdir -p "$DIR"
STAMP=$(date +%Y-%m-%d_%H%M)
cd /opt/cashflow/app
docker compose -p cashflow -f docker-compose.prod.yml --env-file ../.env.prod exec -T postgres \
  sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' | gzip > "$DIR/db_$STAMP.sql.gz"
docker run --rm -v cashflow_media:/media:ro -v "$DIR":/out alpine \
  tar -czf "/out/media_$STAMP.tar.gz" -C /media . 2>/dev/null || true
find "$DIR" -name '*.gz' -mtime +7 -delete
echo "$(date '+%F %T') ok: $(du -sh "$DIR" | cut -f1)"
