import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
import json

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# --- CONFIGURACIÓN DE SITIOS WEB (SELECTORES FINALES Y VERIFICADOS) ---
SITIOS_WEB = [
    # Selector de precisión final para AS
    {'nombre': 'AS', 'url': 'https://as.com/', 'selector': 'main h2.s__tl'},
    # NO SE TOCAN: Lógica y selectores que ya funcionan
    {'nombre': 'Marca', 'url': 'https://www.marca.com/', 'selector': 'a.ue-c-cover-content__link h2.ue-c-cover-content__headline'},
    {'nombre': 'El Diario Montañés', 'url': 'https://www.eldiariomontanes.es/', 'selector': 'h2.v-a-t'},
    {'nombre': 'El Mundo', 'url': 'https://www.elmundo.es/', 'selector': 'a.ue-c-cover-content__link h2.ue-c-cover-content__headline'}
]

CIUDAD = "Santander"
LATITUD = 43.46
LONGITUD = -3.81

def handle_cookie_banner(driver, sitio_nombre):
    time.sleep(3)
    if sitio_nombre == 'AS':
        try:
            iframe = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, "//iframe[contains(@title, 'Contentpass')]")))
            driver.switch_to.frame(iframe)
            agree_button = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Agree & continue')]")))
            agree_button.click()
            driver.switch_to.default_content()
            print("  -> Banner de AS.com gestionado.")
            time.sleep(2)
            return
        except TimeoutException:
            driver.switch_to.default_content()
            print("  -> No se encontró el banner de Contentpass de AS.com.")
    
    other_buttons_xpaths = ["//button[contains(., 'I accept and continue for free')]", "//button[contains(., 'Accept and continue')]", "//button[contains(., 'Aceptar y continuar')]"]
    for xpath in other_buttons_xpaths:
        try:
            button = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.XPATH, xpath)))
            button.click(); time.sleep(3)
            print("  -> Banner de cookies genérico gestionado.")
            return
        except TimeoutException: continue
    print("  -> No se encontró ningún banner conocido.")

def obtener_prevision_tiempo():
    # ... (Sin cambios, ya funciona correctamente) ...
    try:
        print(f"Obteniendo previsión del tiempo para {CIUDAD}...")
        url_api = f"https://api.open-meteo.com/v1/forecast?latitude={LATITUD}&longitude={LONGITUD}&hourly=temperature_2m,precipitation_probability,precipitation&timezone=Europe/Madrid"
        response = requests.get(url_api, timeout=10)
        response.raise_for_status(); data = response.json()
        temp, prob_lluvia, precip = data['hourly']['temperature_2m'][15], data['hourly']['precipitation_probability'][15], data['hourly']['precipitation'][15]
        return f"☀️ Previsión para {CIUDAD} a las 15:00\n- Temperatura: {temp}°C\n- Prob. de lluvia: {prob_lluvia}%\n- Precipitación: {precip} mm\n\n"
    except Exception as e:
        print(f"Error obteniendo el tiempo: {e}")
        return f"🔴 No se pudo obtener la previsión del tiempo para {CIUDAD}.\n\n"

def obtener_titulares():
    mensaje_noticias = "📰 Titulares del día\n\n"
    chrome_options = Options()
    chrome_options.add_argument("--headless"); chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage"); chrome_options.add_argument("--window-size=1920,1200")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36")
    
    driver = None
    try:
        service = Service()
        driver = webdriver.Chrome(service=service, options=chrome_options)

        for sitio in SITIOS_WEB:
            try:
                print(f"\n--- PROCESANDO: {sitio['nombre']} ---")
                driver.get(sitio['url'])
                handle_cookie_banner(driver, sitio['nombre'])
                titulares_obtenidos = []

                if sitio['nombre'] == 'El Diario Montañés':
                    # ... (Lógica JSON-LD - NO SE TOCA) ...
                    print("  -> Usando estrategia JSON-LD...")
                    soup = BeautifulSoup(driver.page_source, 'html.parser')
                    json_scripts = soup.find_all('script', type='application/ld+json')
                    for script in json_scripts:
                        try:
                            data = json.loads(script.string)
                            data_list = data if isinstance(data, list) else [data]
                            for item_data in data_list:
                                if item_data.get('@type') == 'ItemList' and 'itemListElement' in item_data:
                                    for item in item_data.get('itemListElement', []): titulares_obtenidos.append(item['name'])
                                    if titulares_obtenidos: break
                            if titulares_obtenidos: break
                        except: continue

                else: # --- Lógica para AS, Marca y El Mundo ---
                    print("  -> Usando estrategia de selector estándar...")
                    # Espera a que el contenedor principal esté listo
                    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, "main")))
                    print("  -> Contenedor <main> encontrado.")
                    driver.execute_script("window.scrollTo(0, 1000);")
                    time.sleep(2)
                    
                    # Ahora espera por los titulares dentro de ese contenedor
                    WebDriverWait(driver, 15).until(EC.visibility_of_element_located((By.CSS_SELECTOR, sitio['selector'])))
                    soup = BeautifulSoup(driver.page_source, 'html.parser')
                    titulares_html = soup.select(sitio['selector'])
                    for element in titulares_html: titulares_obtenidos.append(element.get_text(strip=True))

                # --- Construcción del mensaje (común para todos) ---
                if titulares_obtenidos:
                    print(f"  -> ¡ÉXITO! Encontrados {len(titulares_obtenidos)} titulares para {sitio['nombre']}.")
                    mensaje_noticias += f"🔵 == {sitio['nombre']} ==\n"
                    count = 0; titulares_set = set()
                    for titular in titulares_obtenidos:
                        if count >= 7: break
                        if len(titular) > 90: titular = titular[:87] + "..."
                        if titular and titular not in titulares_set:
                            mensaje_noticias += f"- {titular}\n"; titulares_set.add(titular); count += 1
                    if count == 0: mensaje_noticias += "- No se encontraron titulares válidos.\n"
                    mensaje_noticias += "\n"
                else:
                    raise ValueError("No se obtuvieron titulares con ninguna estrategia.")

            except Exception as e:
                mensaje_noticias += f"🔴 Error al obtener titulares de {sitio['nombre']}.\n\n"
                print(f"  -> ERROR en {sitio['nombre']}: {type(e).__name__}.")
    finally:
        if driver: driver.quit()
    return mensaje_noticias

def enviar_notificacion(topic_url, mensaje, titulo):
    # ... (Lógica de notificación con botón - NO SE TOCA) ...
    try:
        requests.post(topic_url, data=mensaje.encode('utf-8'),
            headers={
                "Title": titulo, "Priority": "default", "Tags": "newspaper,partly_cloudy",
                "Actions": f"view, Ver Titulares Completos, {topic_url}"
            })
        print("¡Notificación enviada con éxito!")
    except Exception as e: print(f"Error al enviar la notificación a ntfy: {e}")

if __name__ == "__main__":
    # ... (Sin cambios) ...
    NTFY_TOPIC_URL = os.getenv('NTFY_TOPIC')
    if not NTFY_TOPIC_URL: print("Error: La variable de entorno 'NTFY_TOPIC' no está configurada."); exit(1)
    prevision_tiempo = obtener_prevision_tiempo()
    titulares = obtener_titulares()
    mensaje_completo = prevision_tiempo + titulares
    titulo_notificacion = f"Resumen del {datetime.now().strftime('%d/%m/%Y')}"
    enviar_notificacion(NTFY_TOPIC_URL, mensaje_completo, titulo_notificacion)
