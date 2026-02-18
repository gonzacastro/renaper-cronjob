#!/bin/bash
# Wrapper que carga las variables del .env y corre el script Python.
# Usado por launchd para ejecutar el cron job cada hora.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"
LOG_FILE="$SCRIPT_DIR/renaper_check.log"

# Cargar variables de entorno desde .env
if [ ! -f "$ENV_FILE" ]; then
    echo "$(date): ERROR: No se encontró .env en $SCRIPT_DIR" >> "$LOG_FILE"
    exit 1
fi

set -a
source "$ENV_FILE"
set +a

# Correr el script Python y loggear output
echo "$(date): Iniciando chequeo..." >> "$LOG_FILE"
"$SCRIPT_DIR/.venv/bin/python" "$SCRIPT_DIR/renaper_check.py" >> "$LOG_FILE" 2>&1
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo "$(date): Script terminó con error (código $EXIT_CODE)" >> "$LOG_FILE"
else
    echo "$(date): Script terminó OK" >> "$LOG_FILE"
fi

# Rotar log si supera 1MB
if [ -f "$LOG_FILE" ] && [ $(wc -c < "$LOG_FILE") -gt 1048576 ]; then
    mv "$LOG_FILE" "${LOG_FILE}.bak"
fi
