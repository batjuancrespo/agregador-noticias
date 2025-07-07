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

# --- CONFIGURACIÓN DE SITIOS WEB (SELECTORES DE PRECISIÓN QUIRÚRGICA v2) ---
SITIOS_WEB = [
    # AS: Buscamos h2 > a dentro de un artículo con la clase .s-art, que a su vez está en el <main>
    {'nombre': 'AS', 'url': 'https://as.com/', 'selector': 'main article.s-art h2 > a'},
    # Marca y El Mundo: Apuntamos al H2, que es donde está el texto garantizado.
    {'nombre': 'Marca', 'url': 'https://www.marca.com/', 'selector': 'a.ue-c-cover-content__link h2.ue-c-cover-content__headline'},
    {'nombre': 'El Diario Montañés', 'url': 'https://www.eldiariomontanes.es/santander/', 'selector': 'article.voc-story h2.voc-title a'},
    {'nombre': 'El Mundo', 'url': 'https://www.elmundo.es/', 'selector': 'a.ue-c-cover-content__link h2.ue-c-cover-content__headline'}
]

CIUDAD = "Santander"
LATITUD = 43.46
LONGITUD = -3.81

def handle_cookie_banner(driver):
    time.sleep(2)
    accept_button_xpaths = [
        "//button[contains(., 'I accept and continue for free')]",
        "//button[contains(., 'Accept and continue')]",
        "//button[contains(., 'Aceptar y continuar')]",
        "//button[contains(., 'Aceptar')]"
    ]
    for xpath in accept_button_xpaths:
        try:
            button = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.XPATH, xpath)))
            print(f"  -> [LOG] Botón de cookies encontrado. Pulsando...")
            button.click()
            time.sleep(3)
            return
        except TimeoutException:
            continue
    print("  -> [LOG] No se encontró banner de cookies.")

def obtener_prevision_tiempo():
    # ... (esta función ya funciona bien, no se necesita modificar) ...
    try:
        print(f"Obteniendo previsión del tiempo para {CIUDAD}...")
        url_api = f"https://api.open-meteo.com/v1/forecast?latitude={LATITUD}&longitude={LONGITUD}&hourly=temperature_2m,precipitation_probability,precipitation&timezone=Europe/Madrid"
        response = requests.get(url_api, timeout=10)
        response.raise_for_status()
        data = response.json()
        temp = data['hourly']['temperature_2m'][15]
        prob_lluvia = data['hourly']['precipitation_probability'][15]
        precip = data['hourly']['precipitation'][15]
        return f"☀️ Previsión para {CIUDAD} a las 15:00\n- Temperatura: {temp}°C\n- Prob. de lluvia: {prob_lluvia}%\n- Precipitación: {precip} mm\n\n"
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
                print(f"\n--- PROCESANDO: {sitio['nombre']} ---")
                driver.get(sitio['url'])
                handle_cookie_banner(driver)
                print("  -> [LOG] Haciendo scroll para activar contenido perezoso...")
                driver.execute_script("window.scrollTo(0, 800);")
                time.sleep(2)

                WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.CSS_SELECTOR, sitio['selector'])))
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                titulares_html = soup.select(sitio['selector'])
                print(f"  -> [LOG] ¡ÉXITO! Encontrados {len(titulares_html)} elementos en {sitio['nombre']}.")

                mensaje_noticias += f"🔵 == {sitio['nombre']} ==\n"
                count = 0
                titulares_encontrados_set = set()
                
                # --- BUCLE CON DEPURACIÓN INTERNA ---
                for i, titular_element in enumerate(titulares_html):
                    if count >= 10: break
                    try:
                        texto_limpio = titular_element.get_text(strip=True)
                        # Comprobación de que no sea un titular repetido o vacío
                        if texto_limpio and texto_limpio not in titulares_encontrados_set:
                            mensaje_noticias += f"- {texto_limpio}\n"
                            titulares_encontrados_set.add(texto_limpio)
                            count += 1
                            print(f"    [+] Agregado titular {count}: {texto_limpio[:60]}...")
                    except Exception as e_inner:
                        print(f"    [!] Error procesando el elemento {i}: {e_inner}")
                
                if count == 0:
                    mensaje_noticias += "- No se encontraron titulares válidos para mostrar.\n"
                mensaje_noticias += "\n"
                print(f"  -> [LOG] FIN de {sitio['nombre']}. Total titulares agregados: {count}")


            except TimeoutException:
                screenshot_file = f"{sitio['nombre'].replace(' ', '_')}-error.png"
                driver.save_screenshot(screenshot_file)
                print(f"  -> [ERROR] Timeout esperando la visibilidad del selector '{sitio['selector']}'. Captura guardada.")
                mensaje_noticias += f"🔴 Error al obtener titulares de {sitio['nombre']} (Timeout).\n\n"
            except Exception as e:
                print(f"[ERROR] Error inesperado en {sitio['nombre']}: {e}")
                mensaje_noticias += f"🔴 Error inesperado en {sitio['nombre']}.\n\n"
            
            # --- LOG DE CONSTRUCCIÓN DEL MENSAJE ---
            print(f"--- ESTADO DEL MENSAJE TRAS {sitio['nombre'].upper()} ---")
            print(mensaje_noticias)
            print("-------------------------------------------------")


    finally:
        if driver:
            driver.quit()
    return mensaje_noticias

def enviar_notificacion(topic_url, mensaje, titulo):
    print("\n--- MENSAJE FINAL A ENVIAR ---")
    print(mensaje)
    print("----------------------------")
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
