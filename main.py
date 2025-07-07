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

# --- CONFIGURACIÓN DE SITIOS WEB (SELECTORES FINALES Y VALIDADOS) ---
SITIOS_WEB = [
    # AS: La URL de España y un selector preciso para los artículos del contenido principal.
    {'nombre': 'AS', 'url': 'https://as.com/', 'selector': 'main article h2 > a'},
    # Marca y El Mundo: Selector que apunta al H2 dentro del enlace para garantizar que tiene texto.
    {'nombre': 'Marca', 'url': 'https://www.marca.com/', 'selector': 'h2.ue-c-main-headline'},
    # El Diario Montañés: Portada principal y selector que funciona en la página limpia.
    {'nombre': 'El Diario Montañés', 'url': 'https://www.eldiariomontanes.es/', 'selector': 'h2.voc-title a'},
    {'nombre': 'El Mundo', 'url': 'https://www.elmundo.es/', 'selector': 'h2.ue-c-main-headline'}
]

CIUDAD = "Santander"
LATITUD = 43.46
LONGITUD = -3.81

def handle_overlays(driver):
    """
    Función multi-paso que maneja diferentes tipos de banners y pop-ups,
    incluyendo el nuevo de AS y la segunda barrera de El Diario Montañés.
    """
    time.sleep(2) # Pausa inicial
    
    # Lista de XPaths para los diferentes botones de "Aceptar". El orden es importante.
    accept_button_xpaths = [
        "//button[@title='Agree & continue']",                  # Para AS.com (Contentpass)
        "//button[contains(., 'I accept and continue for free')]", # Para Marca
        "//button[contains(., 'Accept and continue')]",            # Para El Mundo
        "//button[contains(., 'Aceptar y continuar')]",           # Para El Diario Montañés (segunda barrera)
    ]
    
    for xpath in accept_button_xpaths:
        try:
            # Primero intentamos en el contenido principal
            button = WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.XPATH, xpath)))
            print(f"  -> [LOG] Banner en página principal encontrado. Pulsando...")
            button.click(); time.sleep(3)
        except TimeoutException:
            # Si no está en la página principal, podría estar en un iFrame
            try:
                iframe = WebDriverWait(driver, 2).until(
                    EC.presence_of_element_located((By.XPATH, "//iframe[contains(@id, 'sp_message_iframe')]"))
                )
                driver.switch_to.frame(iframe)
                print(f"  -> [LOG] iFrame de consentimiento encontrado. Entrando...")
                button = WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.XPATH, xpath)))
                button.click()
                print(f"  -> [LOG] Botón en iFrame pulsado.")
                driver.switch_to.default_content() # Volvemos al contenido principal
                time.sleep(2)
            except TimeoutException:
                driver.switch_to.default_content() # Nos aseguramos de salir del iframe si no encuentra el botón
                continue # Probamos el siguiente xpath
    
    print("  -> [LOG] Búsqueda de banners de consentimiento finalizada.")

def obtener_prevision_tiempo():
    # ... (Sin cambios) ...
    try:
        print(f"Obteniendo previsión del tiempo para {CIUDAD}..."); url_api = f"https://api.open-meteo.com/v1/forecast?latitude={LATITUD}&longitude={LONGITUD}&hourly=temperature_2m,precipitation_probability,precipitation&timezone=Europe/Madrid"
        response = requests.get(url_api, timeout=10); response.raise_for_status(); data = response.json()
        temp = data['hourly']['temperature_2m'][15]; prob_lluvia = data['hourly']['precipitation_probability'][15]; precip = data['hourly']['precipitation'][15]
        return f"☀️ Previsión para {CIUDAD} a las 15:00\n- Temperatura: {temp}°C\n- Prob. de lluvia: {prob_lluvia}%\n- Precipitación: {precip} mm\n\n"
    except Exception as e:
        print(f"Error obteniendo el tiempo: {e}"); return f"🔴 No se pudo obtener la previsión del tiempo.\n\n"

def obtener_titulares():
    mensaje_noticias = "📰 Titulares del día\n\n"
    chrome_options = Options()
    chrome_options.add_argument("--headless"); chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage"); chrome_options.add_argument("--window-size=1920,1200")
    chrome_options.add_argument("--lang=es-ES") # Forzar idioma español
    
    driver = None
    try:
        service = Service()
        driver = webdriver.Chrome(service=service, options=chrome_options)

        for sitio in SITIOS_WEB:
            try:
                print(f"\n--- PROCESANDO: {sitio['nombre']} ---")
                driver.get(sitio['url'])
                
                handle_overlays(driver)

                print("  -> Esperando a que los titulares existan en el HTML...")
                # CAMBIO CLAVE: Esperamos a que los elementos existan, no a que sean visibles.
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, sitio['selector']))
                )
                
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                titulares_html = soup.select(sitio['selector'])
                print(f"  -> ¡ÉXITO! Encontrados {len(titulares_html)} elementos en {sitio['nombre']}.")

                mensaje_noticias += f"🔵 == {sitio['nombre']} ==\n"
                count = 0; titulares_encontrados_set = set()
                for titular_element in titulares_html:
                    if count >= 7: break
                    texto_limpio = titular_element.get_text(strip=True)
                    if len(texto_limpio) > 85: texto_limpio = texto_limpio[:82] + "..."
                    if texto_limpio and texto_limpio not in titulares_encontrados_set:
                        mensaje_noticias += f"- {texto_limpio}\n"
                        titulares_encontrados_set.add(texto_limpio); count += 1
                if count == 0: mensaje_noticias += "- No se encontraron titulares válidos.\n"
                mensaje_noticias += "\n"

            except Exception as e:
                screenshot_file = f"{sitio['nombre'].replace(' ', '_')}-error.png"; driver.save_screenshot(screenshot_file)
                print(f"  -> ERROR en {sitio['nombre']}: {type(e).__name__}. Captura guardada.")
                mensaje_noticias += f"🔴 Error al obtener titulares de {sitio['nombre']}.\n\n"
    finally:
        if driver: driver.quit()
    return mensaje_noticias

def enviar_notificacion(topic_url, mensaje, titulo):
    try:
        requests.post(
            topic_url, data=mensaje.encode('utf-8'),
            headers={"Title": titulo, "Priority": "default", "Tags": "newspaper,partly_cloudy"}
        )
        print("¡Notificación enviada con éxito!")
    except Exception as e: print(f"Error al enviar la notificación a ntfy: {e}")

if __name__ == "__main__":
    NTFY_TOPIC_URL = os.getenv('NTFY_TOPIC')
    if not NTFY_TOPIC_URL: print("Error: La variable de entorno 'NTFY_TOPIC' no está configurada."); exit(1)
    
    prevision_tiempo = obtener_prevision_tiempo()
    titulares = obtener_titulares()
    mensaje_completo = prevision_tiempo + titulares
    titulo_notificacion = f"Resumen del {datetime.now().strftime('%d/%m/%Y')}"
    enviar_notificacion(NTFY_TOPIC_URL, mensaje_completo, titulo_notificacion)
