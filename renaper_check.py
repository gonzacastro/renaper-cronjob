import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import requests
from playwright.sync_api import sync_playwright

TRAMITE_ID = os.environ["TRAMITE_ID"]
GMAIL_USER = os.environ["GMAIL_USER"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
NOTIFY_EMAIL = os.environ["NOTIFY_EMAIL"]

STATE_FILE = "last_state.txt"
RENAPER_URL = "https://mitramite.renaper.gob.ar/"
BUSQUEDA_URL = "https://mitramite.renaper.gob.ar/busqueda.php"
RECAPTCHA_SITEKEY = "6Ld2mMAbAAAAAM9grHC4aJ6pJT1TtvUz04q4Fvjs"


def get_recaptcha_token() -> str:
    """
    Carga la página de RENAPER en Playwright para que el reCAPTCHA v3 de Google
    evalúe el contexto del browser, luego ejecuta grecaptcha.execute() para obtener
    un token válido con action='submit_tramite'.
    """
    print("Obteniendo token reCAPTCHA v3 via Playwright...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="es-AR",
        )
        page = context.new_page()

        # Cargar la página para que reCAPTCHA evalúe el contexto
        page.goto(RENAPER_URL, wait_until="networkidle", timeout=30000)

        # Esperar a que la librería de reCAPTCHA esté lista
        page.wait_for_function("typeof grecaptcha !== 'undefined'", timeout=15000)

        # Ejecutar grecaptcha.execute() con el sitekey y action correctos
        token = page.evaluate(f"""
            () => new Promise((resolve, reject) => {{
                grecaptcha.ready(() => {{
                    grecaptcha.execute('{RECAPTCHA_SITEKEY}', {{action: 'submit_tramite'}})
                        .then(resolve)
                        .catch(reject);
                }});
            }})
        """)

        browser.close()

    if not token:
        raise ValueError("No se pudo obtener el token de reCAPTCHA.")

    print(f"Token obtenido: {token[:30]}...")
    return token


def get_current_state() -> str:
    """
    Obtiene el estado actual del trámite haciendo POST directo a busqueda.php
    con el token reCAPTCHA v3.
    """
    token = get_recaptcha_token()

    print(f"Consultando estado del trámite {TRAMITE_ID}...")
    response = requests.post(
        BUSQUEDA_URL,
        data={
            "tramite": TRAMITE_ID,
            "token": token,
            "action": "submit_tramite",
        },
        headers={
            "Referer": RENAPER_URL,
            "Origin": "https://mitramite.renaper.gob.ar",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        },
        timeout=15,
    )
    response.raise_for_status()

    data = response.json()
    print(f"Respuesta de la API: {data}")

    if data.get("codigo") != 0:
        raise ValueError(f"Error en la API de RENAPER: {data.get('mensaje', 'desconocido')}")

    estado = data["data"]["descripcion_ultimo_estado"]
    fecha = data["data"].get("fecha_toma", "")
    id_estado = data["data"].get("id_ultimo_estado", "")

    resultado = f"{estado} (id={id_estado}, fecha={fecha})"
    print(f"Estado actual: {resultado}")
    return resultado


def load_last_state() -> str | None:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return None


def save_state(state: str) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        f.write(state)


def send_notification(previous: str, current: str) -> None:
    subject = f"[RENAPER] Cambio de estado en trámite {TRAMITE_ID}"
    body = f"""Se detectó un cambio de estado en tu trámite RENAPER.

Número de trámite: {TRAMITE_ID}

Estado anterior:
  {previous}

Estado actual:
  {current}

Consultá más información en: {RENAPER_URL}
"""
    msg = MIMEMultipart()
    msg["From"] = GMAIL_USER
    msg["To"] = NOTIFY_EMAIL
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_USER, NOTIFY_EMAIL, msg.as_string())

    print(f"Email de notificación enviado a {NOTIFY_EMAIL}")


def main():
    current_state = get_current_state()
    last_state = load_last_state()

    if last_state is None:
        print("Primer run: guardando estado inicial, no se envía notificación.")
        save_state(current_state)
        return

    print(f"Estado anterior: {last_state}")

    if current_state.strip() != last_state.strip():
        print("¡El estado CAMBIÓ! Enviando notificación por email...")
        send_notification(last_state, current_state)
        save_state(current_state)
    else:
        print("Sin cambios en el estado del trámite.")


if __name__ == "__main__":
    main()
