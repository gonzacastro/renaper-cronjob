# RENAPER Tramite Checker

Cron job que monitorea cada hora el estado de un trámite en [mitramite.renaper.gob.ar](https://mitramite.renaper.gob.ar/) y envía un email cuando el estado cambia.

Funciona desde tu propia Mac con **launchd** — sin depender de servicios cloud.

---

## Cómo funciona

1. Cada hora, `launchd` corre `run_local.sh`
2. El script abre Chromium (headless) para obtener un token reCAPTCHA v3 válido
3. Hace un POST directo a la API interna de RENAPER (`busqueda.php`) con el token
4. Compara el estado con el guardado en `last_state.txt`
5. Si cambió → envía un email a `NOTIFY_EMAIL`

---

## Instalación (una sola vez)

```bash
cd /Users/gonzalocastro/Documents/proyectos/cronjobs
bash install.sh
```

El script instala automáticamente:
- Virtualenv con Python y dependencias
- Playwright + Chromium
- El launchd job (cron de macOS)

### Prerequisito: App Password de Gmail

1. Ir a [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
2. Crear uno llamado `renaper-checker`
3. Copiar la contraseña de 16 caracteres → `GMAIL_APP_PASSWORD` en el `.env`

> Necesitás tener verificación en dos pasos activa en Gmail.

---

## Archivos

```
install.sh                              # Setup inicial (correr una vez)
run_local.sh                           # Wrapper que carga .env y corre el script
renaper_check.py                       # Script principal
requirements.txt                       # Dependencias Python
com.gonzalocastro.renaper-check.plist  # Configuración de launchd
.env.example                           # Plantilla de variables de entorno
.env                                   # Tus credenciales (no commiteado)
```

---

## Comandos útiles

```bash
# Ver los logs en tiempo real
tail -f renaper_check.log

# Correr el script manualmente ahora
bash run_local.sh

# Ver si el job está activo
launchctl list | grep renaper

# Detener el job
launchctl unload ~/Library/LaunchAgents/com.gonzalocastro.renaper-check.plist

# Reactivar el job
launchctl load ~/Library/LaunchAgents/com.gonzalocastro.renaper-check.plist
```
