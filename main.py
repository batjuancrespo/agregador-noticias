import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# --- CONFIGURACIÓN DE SITIOS WEB (MODO INVESTIGADOR) ---
SITIOS_WEB = [
    # AS: Apuntamos a la portada principal. El objetivo es capturar su HTML.
    {'nombre': 'AS', 'url': 'https://as.com/'},
    # El Diario Montañés: Apuntamos a la portada principal, como pediste.
    {'nombre': 'El Diario Montañés', 'url': 'https://www.eldiariomontanes.es/'},
    # Dejamos Marca y El Mundo para tener una referencia de lo que funciona
    {'nombre': 'Marca', 'url': 'https://www.marca.com/'},
    {'nombre': 'El Mundo', 'url': 'https://www.elmundo.es/'}
]

# (El resto de la configuración y funciones auxiliares no necesitan cambios)
CIUDAD = "Santander"
LATITUD = 43.46
LONGITUD = -3.81

def handle_overlays(driver):
    time.sleep(2)
    cookie_button_xpaths = [
        "//button[contains(., 'Agree & continue')]", "//button[contains(., 'I accept')]",
        "//button[contains(., 'Aceptar')]"
    ]
    for xpath in cookie_button_xpaths:
        try:
            button = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.XPATH, xpath)))
            print(f"  -> [LOG] Banner de consentimiento encontrado. Pulsando...")
            button.click(); time.sleep(3)
        except TimeoutException: continue
    
    try:
        promo_close_button = WebDriverWait(driver, 3).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "div.voc-subscription-wall-container button.art-close"))
        )
        print("  -> [LOG] Banner de promoción encontrado. Cerrando...")
        promo_close_button.click(); time.sleep(2)
    except TimeoutException: pass

def obtener_titulares():
    """
    MODO INVESTIGADOR: El objetivo principal es guardar el HTML de cada página.
    """
    mensaje_noticias = "MODO INVESTIGADOR ACTIVADO\n\n"
    chrome_options = Options()
    chrome_options.add_argument("--headless"); chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage"); chrome_options.add_argument("--window-size=1920,1200")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36")
    
    driver = None
    try:
        service = Service()
        driver = webdriver.Chrome(service=service, options=chrome_options)

        for sitio in SITIOS_WEB:
            try:
                print(f"\n--- INVESTIGANDO: {sitio['nombre']} ---")
                driver.get(sitio['url'])
                handle_overlays(driver) # Limpiamos los banners para obtener el HTML final
                time.sleep(3) # Damos tiempo extra para que todo cargue

                # --- ¡AQUÍ ESTÁ LA MAGIA! GUARDAMOS EL HTML INCONDICIONALMENTE ---
                html_file = f"INVESTIGACION-{sitio['nombre'].replace(' ', '_')}.html"
                with open(html_file, "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                print(f"  -> ¡ÉXITO! Código fuente guardado en '{html_file}'.")
                
                mensaje_noticias += f"🔵 Código de {sitio['nombre']} guardado para análisis.\n"

            except Exception as e:
                print(f"  -> ERROR durante la investigación de {sitio['nombre']}: {type(e).__name__}.")
                mensaje_noticias += f"🔴 Error al capturar el HTML de {sitio['nombre']}.\n"
    finally:
        if driver: driver.quit()
    return mensaje_noticias

def obtener_prevision_tiempo():
    # ... (sin cambios)
    try:
        print(f"Obteniendo previsión del tiempo para {CIUDAD}..."); url_api = f"https://api.open-meteo.com/v1/forecast?latitude={LATITUD}&longitude={LONGITUD}&hourly=temperature_2m,precipitation_probability,precipitation&timezone=Europe/Madrid"
        response = requests.get(url_api, timeout=10); response.raise_for_status(); data = response.json()
        temp = data['hourly']['temperature_2m'][15]; prob_lluvia = data['hourly']['precipitation_probability'][15]; precip = data['hourly']['precipitation'][15]
        return f"☀️ Previsión para {CIUDAD} a las 15:00\n- Temperatura: {temp}°C\n- Prob. de lluvia: {prob_lluvia}%\n- Precipitación: {precip} mm\n\n"
    except Exception as e: print(f"Error obteniendo el tiempo: {e}"); return f"🔴 No se pudo obtener la previsión del tiempo.\n\n"

def enviar_notificacion(topic_url, mensaje, titulo):
    # ... (sin cambios)
    try:
        requests.post(topic_url, data=mensaje.encode('utf-8'), headers={"Title": titulo, "Priority": "default", "Tags": "newspaper,partly_cloudy"})
        print("¡Notificación enviada con éxito!")
    except Exception as e: print(f"Error al enviar la notificación a ntfy: {e}")

if __name__ == "__main__":
    NTFY_TOPIC_URL = os.getenv('NTFY_TOPIC')
    if not NTFY_TOPIC_URL: print("Error: La variable de entorno 'NTFY_TOPIC' no está configurada."); exit(1)
    prevision_tiempo = obtener_prevision_tiempo()
    titulares = obtener_titulares()
    mensaje_completo = prevision_tiempo + titulares
    titulo_notificacion = f"Resultados del Modo Investigador - {datetime.now().strftime('%d/%m/%Y')}"
    enviar_notificacion(NTFY_TOPIC_URL, mensaje_completo, titulo_notificacion)
