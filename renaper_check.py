import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from playwright.sync_api import sync_playwright

TRAMITE_ID = os.environ["TRAMITE_ID"]
GMAIL_USER = os.environ["GMAIL_USER"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
NOTIFY_EMAIL = os.environ["NOTIFY_EMAIL"]

STATE_FILE = "last_state.txt"
RENAPER_URL = "https://mitramite.renaper.gob.ar/"


def get_current_state() -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(RENAPER_URL, wait_until="networkidle", timeout=30000)

        # Buscar el campo de input para el ID de trámite
        # Intentar varios selectores comunes
        input_selector = (
            "input[type='text'], input[name*='tramite'], input[name*='id'], "
            "input[placeholder*='tramite'], input[placeholder*='Tramite'], "
            "input[placeholder*='ID'], input[id*='tramite'], input[id*='id']"
        )
        page.wait_for_selector(input_selector, timeout=15000)
        page.fill(input_selector, TRAMITE_ID)

        # Enviar el formulario (buscar botón de búsqueda/consultar)
        submit_selector = (
            "button[type='submit'], input[type='submit'], "
            "button:has-text('Consultar'), button:has-text('Buscar'), "
            "button:has-text('Ver estado'), button:has-text('Consulta')"
        )
        page.click(submit_selector)
        page.wait_for_load_state("networkidle", timeout=20000)

        # Extraer el estado del trámite
        # Intentar obtener el texto completo de la página de resultado
        content = page.content()

        # Buscar el estado en elementos comunes
        state_text = None
        state_selectors = [
            ".estado", ".state", "[class*='estado']", "[class*='state']",
            "[class*='status']", "h2", "h3", ".resultado", ".result",
            "[class*='resultado']", "[class*='tramite']",
        ]
        for selector in state_selectors:
            try:
                elements = page.query_selector_all(selector)
                for el in elements:
                    text = el.inner_text().strip()
                    if text and len(text) > 2:
                        state_text = text
                        break
                if state_text:
                    break
            except Exception:
                continue

        # Si no encontramos selector específico, obtener todo el body
        if not state_text:
            state_text = page.inner_text("body").strip()

        browser.close()

        if not state_text:
            raise ValueError("No se pudo extraer el estado del trámite.")

        return state_text


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
    print(f"Consultando estado del trámite {TRAMITE_ID}...")
    current_state = get_current_state()
    print(f"Estado actual encontrado:\n{current_state[:300]}")

    last_state = load_last_state()

    if last_state is None:
        print("Primer run: guardando estado inicial, no se envía notificación.")
        save_state(current_state)
        return

    if current_state.strip() != last_state.strip():
        print("El estado cambió. Enviando notificación por email...")
        send_notification(last_state, current_state)
        save_state(current_state)
    else:
        print("Sin cambios en el estado del trámite.")


if __name__ == "__main__":
    main()
