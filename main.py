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
    {'nombre': 'AS', 'url': 'https://as.com/', 'selector': 'main article.s-art h2 > a'},
    {'nombre': 'Marca', 'url': 'https://www.marca.com/', 'selector': 'a.ue-c-cover-content__link h2.ue-c-cover-content__headline'},
    {'nombre': 'El Diario Montañés', 'url': 'https://www.eldiariomontanes.es/santander/', 'selector': 'h2.v-a-t'},
    {'nombre': 'El Mundo', 'url': 'https://www.elmundo.es/', 'selector': 'a.ue-c-cover-content__link h2.ue-c-cover-content__headline'}
]

CIUDAD = "Santander"
LATITUD = 43.46
LONGITUD = -3.81

def handle_cookie_banner(driver, sitio_nombre):
    time.sleep(3) # Pausa para que carguen los banners

    # Estrategia para AS.COM (banner de "Agree & continue")
    if sitio_nombre == 'AS':
        try:
            agree_button_as = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Agree & continue')]"))
            )
            print("  -> Banner de AS.com encontrado. Pulsando 'Agree & continue'...")
            agree_button_as.click()
            time.sleep(3)
            return
        except TimeoutException:
            print("  -> No se encontró el banner específico de AS.com.")

    # Estrategia general para los demás (funciona para Marca, El Mundo, El Diario)
    accept_button_xpaths = [
        "//button[contains(., 'I accept and continue for free')]",
        "//button[contains(., 'Accept and continue')]",
        "//button[contains(., 'Aceptar y continuar')]"
    ]
    for xpath in accept_button_xpaths:
        try:
            button = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.XPATH, xpath)))
            print(f"  -> Botón de cookies encontrado. Pulsando...")
            button.click()
            time.sleep(3)
            return
        except TimeoutException:
            continue
    print("  -> No se encontró ningún banner de cookies conocido o ya estaba aceptado.")


def obtener_prevision_tiempo():
    try:
        print(f"Obteniendo previsión del tiempo para {CIUDAD}...")
        url_api = f"https://api.open-meteo.com/v1/forecast?latitude={LATITUD}&longitude={LONGITUD}&hourly=temperature_2m,precipitation_probability,precipitation&timezone=Europe/Madrid"
        response = requests.get(url_api, timeout=10)
        response.raise_for_status()
        data = response.json()
        temp_list = data['hourly']['temperature_2m']
        prob_lluvia_list = data['hourly']['precipitation_probability']
        precip_list = data['hourly']['precipitation']
        
        # Corrección del error en la previsión del tiempo
        temp = temp_list[15] if len(temp_list) > 15 else "N/A"
        prob_lluvia = prob_lluvia_list[15] if len(prob_lluvia_list) > 15 else "N/A"
        precip = precip_list[15] if len(precip_list) > 15 else "N/A"

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

                # Estrategia JSON para El Diario Montañés
                if sitio['nombre'] == 'El Diario Montañés':
                    soup = BeautifulSoup(driver.page_source, 'html.parser')
                    json_ld_scripts = soup.find_all('script', type='application/ld+json')
                    titulares_encontrados = []
                    for script in json_ld_scripts:
                        try:
                            data = json.loads(script.string)
                            if isinstance(data, list): data_list = data
                            else: data_list = [data]
                            for item_data in data_list:
                                if item_data.get('@type') == 'ItemList' and 'itemListElement' in item_data:
                                    print("  -> ¡ÉXITO! Encontrado ItemList en JSON-LD.")
                                    for item in item_data['itemListElement']:
                                        titulares_encontrados.append(item['name'])
                                    break
                            if titulares_encontrados: break
                        except (json.JSONDecodeError, AttributeError): continue
                    
                    if not titulares_encontrados: raise ValueError("No se encontró el JSON-LD de tipo ItemList.")
                    
                    mensaje_noticias += f"🔵 == {sitio['nombre']} ==\n"
                    for i, titular in enumerate(titulares_encontrados):
                        if i >= 7: break
                        if len(titular) > 85: titular = titular[:82] + "..."
                        mensaje_noticias += f"- {titular}\n"
                    mensaje_noticias += "\n"
                
                # Estrategia estándar para los demás
                else:
                    print("  -> Haciendo scroll para activar contenido...")
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
                    time.sleep(2)
                    WebDriverWait(driver, 25).until(EC.visibility_of_element_located((By.CSS_SELECTOR, sitio['selector'])))
                    
                    soup = BeautifulSoup(driver.page_source, 'html.parser')
                    titulares_html = soup.select(sitio['selector'])
                    print(f"  -> Encontrados {len(titulares_html)} elementos en {sitio['nombre']}.")

                    mensaje_noticias += f"🔵 == {sitio['nombre']} ==\n"
                    count = 0; titulares_encontrados_set = set()
                    for titular_element in titulares_html:
                        if count >= 7: break
                        texto_limpio = titular_element.get_text(strip=True)
                        if len(texto_limpio) > 85: texto_limpio = texto_limpio[:82] + "..."
                        if texto_limpio and texto_limpio not in titulares_encontrados_set:
                            mensaje_noticias += f"- {texto_limpio}\n"; titulares_encontrados_set.add(texto_limpio); count += 1
                    if count == 0: mensaje_noticias += "- No se encontraron titulares válidos.\n"
                    mensaje_noticias += "\n"

            except Exception as e:
                screenshot_file = f"{sitio['nombre'].replace(' ', '_')}-error.png"
                driver.save_screenshot(screenshot_file)
                print(f"  -> ERROR en {sitio['nombre']}: {type(e).__name__}. Captura guardada.")
                mensaje_noticias += f"🔴 Error al obtener titulares de {sitio['nombre']}.\n\n"
    finally:
        if driver: driver.quit()
    return mensaje_noticias

def enviar_notificacion(topic_url, mensaje, titulo):
    try:
        requests.post(topic_url, data=mensaje.encode('utf-8'), headers={"Title": titulo, "Priority": "default", "Tags": "newspaper,partly_cloudy"})
        print("¡Notificación enviada con éxito!")
    except Exception as e: print(f"Error al enviar la notificación a ntfy: {e}")

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
