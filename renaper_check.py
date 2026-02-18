import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

TRAMITE_ID = os.environ["TRAMITE_ID"]
GMAIL_USER = os.environ["GMAIL_USER"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
NOTIFY_EMAIL = os.environ["NOTIFY_EMAIL"]

STATE_FILE = "last_state.txt"
SCREENSHOT_FILE = "debug_screenshot.png"
RENAPER_URL = "https://mitramite.renaper.gob.ar/"

# Etapas conocidas del trámite RENAPER
KNOWN_STAGES = ["Inicio", "Verificación", "Verificacion", "Producción", "Produccion",
                "Embalaje", "Correo", "Retiro"]


def get_current_state() -> tuple[str, str]:
    """
    Returns (estado_texto, html_resultado) where estado_texto is the extracted
    state and html_resultado is the full HTML of the result section for comparison.
    """
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

        print(f"Navegando a {RENAPER_URL}...")
        page.goto(RENAPER_URL, wait_until="networkidle", timeout=30000)

        # Esperar y encontrar el input del ID de trámite
        print("Buscando campo de ID de trámite...")
        input_selectors = [
            "input[placeholder*='ID' i]",
            "input[placeholder*='tramite' i]",
            "input[placeholder*='trámite' i]",
            "input[type='text']",
            "input[type='number']",
            "input:not([type='hidden'])",
        ]

        input_el = None
        for sel in input_selectors:
            try:
                page.wait_for_selector(sel, timeout=5000)
                input_el = page.query_selector(sel)
                if input_el:
                    print(f"Input encontrado con selector: {sel}")
                    break
            except PlaywrightTimeout:
                continue

        if not input_el:
            page.screenshot(path=SCREENSHOT_FILE)
            raise ValueError("No se encontró el campo de input para el ID de trámite.")

        # Limpiar y llenar el input
        input_el.click()
        input_el.fill("")
        input_el.type(TRAMITE_ID, delay=50)
        print(f"ID {TRAMITE_ID} ingresado.")

        # Buscar y clickear el botón de consulta
        print("Buscando botón CONSULTAR...")
        submit_selectors = [
            "button:has-text('CONSULTAR')",
            "button:has-text('Consultar')",
            "button:has-text('consultar')",
            "button:has-text('Buscar')",
            "button:has-text('BUSCAR')",
            "input[type='submit']",
            "button[type='submit']",
        ]

        submitted = False
        for sel in submit_selectors:
            try:
                btn = page.query_selector(sel)
                if btn:
                    btn.click()
                    print(f"Botón clickeado con selector: {sel}")
                    submitted = True
                    break
            except Exception:
                continue

        if not submitted:
            # Intentar con Enter en el input
            input_el.press("Enter")
            print("Submit via Enter.")

        # Esperar a que aparezca el resultado con alguna etapa conocida
        print("Esperando resultado...")
        result_appeared = False
        for stage in KNOWN_STAGES:
            try:
                page.wait_for_selector(
                    f"text={stage}", timeout=10000, state="visible"
                )
                print(f"Resultado encontrado (etapa visible: {stage})")
                result_appeared = True
                break
            except PlaywrightTimeout:
                continue

        # Esperar un poco más si no apareció aún
        if not result_appeared:
            page.wait_for_load_state("networkidle", timeout=15000)
            print("networkidle alcanzado, extrayendo estado de todas formas...")

        # Tomar screenshot para debug
        page.screenshot(path=SCREENSHOT_FILE, full_page=True)
        print(f"Screenshot guardado en {SCREENSHOT_FILE}")

        # Intentar extraer el estado activo
        # Buscar elementos con clase "activo", "active", "current", "selected"
        # o que tengan aria-current, o cualquier elemento con texto de etapa conocida
        estado_texto = None
        active_selectors = [
            ".activo", ".active", ".current", ".selected",
            "[class*='activo']", "[class*='active']", "[class*='current']",
            "[aria-current]", "[class*='estado']", "[class*='stage']",
            "[class*='step']", "[class*='paso']",
        ]

        for sel in active_selectors:
            try:
                elements = page.query_selector_all(sel)
                for el in elements:
                    txt = el.inner_text().strip()
                    if any(stage.lower() in txt.lower() for stage in KNOWN_STAGES):
                        estado_texto = txt
                        print(f"Estado activo encontrado ({sel}): {txt}")
                        break
                if estado_texto:
                    break
            except Exception:
                continue

        # Si no encontramos el estado activo, buscar todos los elementos con texto de etapas
        if not estado_texto:
            print("No se encontró elemento 'activo'. Extrayendo todas las etapas visibles...")
            all_stages_found = []
            for stage in KNOWN_STAGES:
                try:
                    elements = page.query_selector_all(f"text={stage}")
                    for el in elements:
                        txt = el.inner_text().strip()
                        if txt and txt not in all_stages_found:
                            all_stages_found.append(txt)
                except Exception:
                    continue
            if all_stages_found:
                estado_texto = " | ".join(all_stages_found)
                print(f"Etapas encontradas: {estado_texto}")

        # Fallback: obtener el HTML de toda la página para comparación
        full_html = page.content()

        # Si todavía no tenemos estado, usar el body text como fallback
        if not estado_texto:
            print("ADVERTENCIA: No se identificaron etapas. Usando body text como fallback.")
            body_text = page.inner_text("body").strip()
            # Filtrar solo las líneas que contengan etapas conocidas
            relevant_lines = [
                line.strip() for line in body_text.split("\n")
                if any(stage.lower() in line.lower() for stage in KNOWN_STAGES)
            ]
            estado_texto = "\n".join(relevant_lines) if relevant_lines else body_text[:500]

        browser.close()
        return estado_texto, full_html


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
    current_state, _ = get_current_state()
    print(f"\nEstado actual extraído:\n{current_state}\n")

    last_state = load_last_state()

    if last_state is None:
        print("Primer run: guardando estado inicial, no se envía notificación.")
        save_state(current_state)
        return

    print(f"Estado anterior:\n{last_state}\n")

    if current_state.strip() != last_state.strip():
        print("El estado CAMBIÓ. Enviando notificación por email...")
        send_notification(last_state, current_state)
        save_state(current_state)
    else:
        print("Sin cambios en el estado del trámite.")


if __name__ == "__main__":
    main()
