#!/bin/sh
# Respaldo de HumanAIz: base de datos + documentos.
#   ./deploy/backup.sh [directorio_destino]     (por defecto ./backups)
# Ejecútalo desde la raíz del repo, con el stack levantado.
#
# OJO: los respaldos contienen certificados médicos (datos sensibles).
# Guárdalos cifrados y fuera del servidor, y define cuánto tiempo se conservan.
set -eu

DESTINO="${1:-./backups}"
MARCA="$(date +%Y%m%d-%H%M%S)"
mkdir -p "$DESTINO"
umask 077

echo "Base de datos -> $DESTINO/db-$MARCA.dump"
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -Fc "$POSTGRES_DB"'   > "$DESTINO/db-$MARCA.dump"

echo "Documentos    -> $DESTINO/uploads-$MARCA.tar.gz"
docker compose exec -T api tar -C /data -czf - uploads   > "$DESTINO/uploads-$MARCA.tar.gz"

echo "Listo. Para restaurar:"
echo "  docker compose exec -T db sh -c 'pg_restore -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" --clean --if-exists' < db-$MARCA.dump"
echo "  docker compose exec -T api tar -C /data -xzf - < uploads-$MARCA.tar.gz"
