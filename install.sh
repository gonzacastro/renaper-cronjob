#!/bin/bash
# Setup completo del cron job de RENAPER en macOS.
# Correr una sola vez desde la carpeta del proyecto.

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLIST_NAME="com.gonzalocastro.renaper-check"
PLIST_SRC="$SCRIPT_DIR/$PLIST_NAME.plist"
PLIST_DST="$HOME/Library/LaunchAgents/$PLIST_NAME.plist"

echo "=== Setup RENAPER Tramite Checker ==="
echo "Directorio: $SCRIPT_DIR"

# 1. Crear .env si no existe
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
    echo ""
    echo "⚠️  Se creó .env — editalo con tus datos reales antes de continuar:"
    echo "   $SCRIPT_DIR/.env"
    echo ""
    echo "Campos a completar:"
    echo "  TRAMITE_ID=        (tu número de trámite)"
    echo "  GMAIL_USER=        (tu cuenta de Gmail)"
    echo "  GMAIL_APP_PASSWORD=(App Password de Gmail)"
    echo "  NOTIFY_EMAIL=      (email donde recibir alertas)"
    echo ""
    read -p "Presioná Enter cuando hayas completado el .env..."
fi

# 2. Crear virtualenv e instalar dependencias
echo ""
echo "→ Creando virtualenv..."
python3 -m venv "$SCRIPT_DIR/.venv"

echo "→ Instalando dependencias Python..."
"$SCRIPT_DIR/.venv/bin/pip" install --upgrade pip -q
"$SCRIPT_DIR/.venv/bin/pip" install -r "$SCRIPT_DIR/requirements.txt" -q

echo "→ Instalando Playwright (Chromium)..."
"$SCRIPT_DIR/.venv/bin/playwright" install chromium

# 3. Dar permisos de ejecución al script
chmod +x "$SCRIPT_DIR/run_local.sh"

# 4. Instalar el launchd job
echo ""
echo "→ Instalando launchd job..."
mkdir -p "$HOME/Library/LaunchAgents"
cp "$PLIST_SRC" "$PLIST_DST"

# Descargar si ya estaba cargado
launchctl unload "$PLIST_DST" 2>/dev/null || true
launchctl load "$PLIST_DST"

echo ""
echo "✅ Instalación completa!"
echo ""
echo "El script correrá automáticamente cada hora."
echo ""
echo "Comandos útiles:"
echo "  Ver logs:          tail -f $SCRIPT_DIR/renaper_check.log"
echo "  Correr ahora:      bash $SCRIPT_DIR/run_local.sh"
echo "  Detener el job:    launchctl unload $PLIST_DST"
echo "  Reactivar el job:  launchctl load $PLIST_DST"
echo "  Ver estado:        launchctl list | grep renaper"
