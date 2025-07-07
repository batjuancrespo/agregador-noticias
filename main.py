import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time

# --- Importaciones de Selenium ---
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# --- CONFIGURACIÓN DE SITIOS WEB ---
SITIOS_WEB = [
    {'nombre': 'AS', 'url': 'https://as.com/', 'selector': 'h2.s__tl'},
    {'nombre': 'Marca', 'url': 'https://www.marca.com/', 'selector': 'h2.ue-c-main-headline'},
    {'nombre': 'El Diario Montañés', 'url': 'https://www.eldiariomontanes.es/santander/', 'selector': 'h2.voc-title a'},
    {'nombre': 'El Mundo', 'url': 'https://www.elmundo.es/', 'selector': 'h2.ue-c-main-headline'}
]

# --- CONFIGURACIÓN DEL TIEMPO ---
CIUDAD = "Santander"
LATITUD = 43.46
LONGITUD = -3.81

def handle_cookie_banner(driver):
    """
    Función súper robusta que busca y pulsa el botón de aceptar cookies
    usando el texto exacto de los botones de las capturas de pantalla.
    """
    time.sleep(2) # Pausa inicial
    
    # Lista de XPaths para los diferentes botones de "Aceptar"
    # El orden es de más específico a más general
    accept_button_xpaths = [
        "//button[contains(., 'I accept and continue for free')]", # Para MARCA
        "//button[contains(., 'Accept and continue')]",            # Para El Mundo
        "//button[contains(., 'Aceptar y continuar')]",           # Para El Diario Montañés
        "//button[contains(., 'Aceptar')]"                        # Un genérico de respaldo
    ]
    
    for xpath in accept_button_xpaths:
        try:
            # Esperamos un máximo de 3 segundos por cada tipo de botón
            button = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            print(f"  -> Botón de cookies encontrado con el texto: '{button.text}'. Pulsando...")
            button.click()
            time.sleep(2) # Damos tiempo a que la página reaccione y desaparezca el banner
            return # Si lo encontramos y pulsamos, salimos de la función
        except TimeoutException:
            # Si no se encuentra este botón, no hacemos nada y probamos el siguiente
            continue
            
    print("  -> No se encontró ningún banner de cookies conocido o ya estaba aceptado.")


def obtener_prevision_tiempo():
    try:
        print(f"Obteniendo previsión del tiempo para {CIUDAD}...")
        url_api = f"https://api.open-meteo.com/v1/forecast?latitude={LATITUD}&longitude={LONGITUD}&hourly=temperature_2m&timezone=Europe/Madrid"
        response = requests.get(url_api, timeout=10)
        response.raise_for_status()
        data = response.json()
        temperatura_15h = data['hourly']['temperature_2m'][15]
        return f"☀️ Previsión para {CIUDAD} a las 15:00\n- Temperatura: {temperatura_15h}°C\n\n"
    except Exception as e:
        print(f"Error obteniendo el tiempo: {e}")
        return f"🔴 No se pudo obtener la previsión del tiempo para {CIUDAD}.\n\n"

def obtener_titulares():
    mensaje_noticias = "📰 Titulares del día\n\n"
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36")
    
    driver = None
    try:
        service = Service()
        driver = webdriver.Chrome(service=service, options=chrome_options)

        for sitio in SITIOS_WEB:
            try:
                print(f"Obteniendo titulares de: {sitio['nombre']} con Selenium...")
                driver.get(sitio['url'])

                handle_cookie_banner(driver)

                # Aumentamos la espera principal por si la página tarda en refrescar tras aceptar cookies
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, sitio['selector']))
                )
                
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                titulares_html = soup.select(sitio['selector'])
                print(f"  -> ¡ÉXITO! Encontrados {len(titulares_html)} elementos en {sitio['nombre']}.")

                mensaje_noticias += f"🔵 == {sitio['nombre']} ==\n"
                count = 0
                titulares_encontrados = set()
                for titular in titulares_html:
                    if count >= 5: break
                    texto_limpio = titular.get_text(strip=True)
                    if texto_limpio and texto_limpio not in titulares_encontrados:
                        mensaje_noticias += f"- {texto_limpio}\n"
                        titulares_encontrados.add(texto_limpio)
                        count += 1
                mensaje_noticias += "\n"

            except TimeoutException:
                screenshot_file = f"{sitio['nombre'].replace(' ', '_')}-error.png"
                driver.save_screenshot(screenshot_file)
                print(f"  -> ERROR: Timeout esperando el selector '{sitio['selector']}'.")
                print(f"  -> Se ha guardado una captura de pantalla en '{screenshot_file}'.")
                mensaje_noticias += f"🔴 Error al obtener titulares de {sitio['nombre']} (Timeout).\n\n"
            except Exception as e:
                print(f"Error inesperado durante el scraping de {sitio['nombre']}: {e}")
                mensaje_noticias += f"🔴 Error inesperado en {sitio['nombre']}.\n\n"
    finally:
        if driver:
            driver.quit()
    return mensaje_noticias

def enviar_notificacion(topic_url, mensaje, titulo):
    try:
        requests.post(
            topic_url,
            data=mensaje.encode('utf-8'),
            headers={"Title": titulo, "Priority": "default", "Tags": "newspaper,partly_cloudy"}
        )
        print("¡Notificación enviada con éxito!")
    except Exception as e:
        print(f"Error al enviar la notificación a ntfy: {e}")

if __name__ == "__main__":
    NTFY_TOPIC_URL = os.getenv('NTFY_TOPIC')
    if not NTFY_TOPIC_URL:
        print("Error: La variable de entorno 'NTFY_TOPIC' no está configurada.")
        exit(1)
    
    prevision_tiempo = obtener_prevision_tiempo()
    titulares = obtener_titulares()
    mensaje_completo = prevision_tiempo + titulares
    titulo_notificacion = f"Resumen del {datetime.now().strftime('%d/%m/%Y')}"
    enviar_notificacion(NTFY_TOPIC_URL, mensaje_completo, titulo_notificacion)
