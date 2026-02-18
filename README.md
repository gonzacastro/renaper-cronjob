# RENAPER Tramite Checker

Cron job que monitorea cada hora el estado de un trámite en [mitramite.renaper.gob.ar](https://mitramite.renaper.gob.ar/) y envía un email cuando el estado cambia.

Corre automáticamente en **GitHub Actions** — no necesitás tener tu computadora prendida.

---

## Setup

### 1. Forkeá o cloná este repo en tu cuenta de GitHub

### 2. Configurá los Secrets en GitHub

Ir a: **Settings → Secrets and variables → Actions → New repository secret**

| Secret | Descripción |
|---|---|
| `TRAMITE_ID` | ID del trámite a monitorear (ej: `00743721242`) |
| `GMAIL_USER` | Tu dirección de Gmail (ej: `tucuenta@gmail.com`) |
| `GMAIL_APP_PASSWORD` | App Password de Gmail (ver abajo) |
| `NOTIFY_EMAIL` | Email donde recibir las notificaciones |

#### Cómo generar un App Password de Gmail

1. Ir a [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
2. Seleccionar "Correo" y "Otro (nombre personalizado)"
3. Escribir `renaper-checker` y hacer clic en Generar
4. Copiar la contraseña de 16 caracteres → usarla como `GMAIL_APP_PASSWORD`

> Nota: Necesitás tener la verificación en dos pasos activada en tu cuenta de Gmail.

### 3. Activar GitHub Actions

Una vez que hagas push, el workflow se activa automáticamente. También podés correrlo manualmente:

1. Ir a la pestaña **Actions** en tu repositorio
2. Seleccionar **RENAPER Tramite Check**
3. Hacer clic en **Run workflow**

---

## Cómo funciona

1. Cada hora, GitHub Actions corre `renaper_check.py`
2. El script abre el sitio de RENAPER con Playwright (navegador headless)
3. Ingresa el `TRAMITE_ID` en el formulario y extrae el estado
4. Compara con el estado guardado en cache (`last_state.txt`)
5. Si cambió → envía un email de notificación a `NOTIFY_EMAIL`
6. Guarda el nuevo estado en cache para la próxima comparación

---

## Archivos

```
.github/workflows/renaper-check.yml   # Workflow de GitHub Actions
renaper_check.py                       # Script principal
requirements.txt                       # Dependencias Python
```
