#!/usr/bin/env bash
# Выкладка на сервер: ./deploy/deploy.sh [root@хост]
# Отправляет закоммиченный код (git archive), собирает и перезапускает контейнеры.
set -euo pipefail

SERVER="${1:-root@95.163.229.64}"
DOMAIN="${DOMAIN:-emelyanova-play.online}"
ROOT=/opt/cashflow

cd "$(git rev-parse --show-toplevel)"
if [ -n "$(git status --porcelain)" ]; then
  echo "Есть незакоммиченные изменения — на сервер уйдёт только последний коммит." >&2
fi
echo "Выкладываю $(git log -1 --format='%h %s') на $SERVER"

# Код — в новую папку, потом подменяем: на сервере не остаётся удалённых файлов.
git archive --format=tar HEAD | ssh "$SERVER" "rm -rf $ROOT/app.new && mkdir -p $ROOT/app.new && tar -x -C $ROOT/app.new"

ssh "$SERVER" DOMAIN="$DOMAIN" ROOT="$ROOT" 'bash -s' <<'REMOTE'
set -euo pipefail
cd "$ROOT"

# Первый запуск: настройки со случайными паролями (остаются только на сервере).
if [ ! -f .env.prod ]; then
  umask 077
  sed -e "s|^DJANGO_SECRET_KEY=.*|DJANGO_SECRET_KEY=$(openssl rand -base64 48 | tr -d '\n/+=')|" \
      -e "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$(openssl rand -hex 24)|" \
      -e "s|emelyanova-play.online|$DOMAIN|g" \
      app.new/.env.prod.example > .env.prod
  echo "Создан $ROOT/.env.prod"
fi

rm -rf app.old
[ -d app ] && mv app app.old
mv app.new app
ln -sf ../.env.prod app/.env.prod

cd app
docker compose -p cashflow -f docker-compose.prod.yml --env-file ../.env.prod up -d --build --remove-orphans
docker image prune -f >/dev/null

# Ежедневная резервная копия базы
install -m 755 deploy/backup.sh /usr/local/bin/cashflow-backup
echo "15 4 * * * root /usr/local/bin/cashflow-backup >> /var/log/cashflow-backup.log 2>&1" > /etc/cron.d/cashflow-backup

docker compose -p cashflow -f docker-compose.prod.yml --env-file ../.env.prod ps --format '{{.Service}}: {{.Status}}'
REMOTE
