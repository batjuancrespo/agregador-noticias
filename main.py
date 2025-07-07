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

# --- CONFIGURACIÓN DE SITIOS WEB ---
# Usamos los selectores que sabemos que son correctos una vez que la página carga
SITIOS_WEB = [
    {
        'nombre': 'AS',
        'url': 'https://as.com/',
        'selector': 'h2.s__tl'
    },
    {
        'nombre': 'Marca',
        'url': 'https://www.marca.com/',
        'selector': 'h2.ue-c-main-headline'
    },
    {
        'nombre': 'El Diario Montañés',
        'url': 'https://www.eldiariomontanes.es/santander/',
        'selector': 'h2.voc-title a'
    },
    {
        'nombre': 'El Mundo',
        'url': 'https://www.elmundo.es/',
        'selector': 'h2.ue-c-main-headline'
    }
]

# --- CONFIGURACIÓN DEL TIEMPO ---
CIUDAD = "Santander"
LATITUD = 43.46
LONGITUD = -3.81

def obtener_prevision_tiempo():
    # Esta función no cambia, sigue usando requests
    try:
        print(f"Obteniendo previsión del tiempo para {CIUDAD}...")
        url_api = f"https://api.open-meteo.com/v1/forecast?latitude={LATITUD}&longitude={LONGITUD}&hourly=temperature_2m&timezone=Europe/Madrid"
        response = requests.get(url_api, timeout=10)
        response.raise_for_status()
        data = response.json()
        temperatura_15h = data['hourly']['temperature_2m'][15]
        mensaje_tiempo = f"☀️ Previsión para {CIUDAD} a las 15:00\n"
        mensaje_tiempo += f"- Temperatura: {temperatura_15h}°C\n\n"
        return mensaje_tiempo
    except Exception as e:
        print(f"Error obteniendo el tiempo: {e}")
        return f"🔴 No se pudo obtener la previsión del tiempo para {CIUDAD}.\n\n"

def obtener_titulares():
    """
    Función REESCRITA para usar Selenium y simular un navegador real.
    """
    mensaje_noticias = "📰 Titulares del día\n\n"
    
    # --- Configuración de Opciones de Chrome para Selenium ---
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Ejecutar sin abrir una ventana de navegador visible
    chrome_options.add_argument("--no-sandbox") # Requerido para ejecutar como root (común en CI/CD)
    chrome_options.add_argument("--disable-dev-shm-usage") # Evita problemas en entornos con memoria limitada
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36")

    # Inicializamos el driver de Chrome
    driver = None
    try:
        # Usamos Service() para una mejor gestión del driver
        service = Service()
        driver = webdriver.Chrome(service=service, options=chrome_options)

        for sitio in SITIOS_WEB:
            try:
                print(f"Obteniendo titulares de: {sitio['nombre']} con Selenium...")
                driver.get(sitio['url'])

                # Esperamos un máximo de 10 segundos a que el contenido principal aparezca
                # Usamos el selector CSS para la espera, es una buena señal de que la página cargó
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, sitio['selector']))
                )
                
                # Pequeña pausa adicional por si acaso
                time.sleep(2) 

                # Una vez cargada la página, obtenemos el HTML y lo pasamos a BeautifulSoup
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                
                titulares_html = soup.select(sitio['selector'])
                print(f"  -> Encontrados {len(titulares_html)} elementos con el selector '{sitio['selector']}'.")

                if not titulares_html:
                    mensaje_noticias += f"⚪️ -- {sitio['nombre']}: No se encontraron titulares hoy --\n\n"
                    continue

                mensaje_noticias += f"🔵 == {sitio['nombre']} ==\n"
                count = 0
                titulares_encontrados = set()
                for titular in titulares_html:
                    if count >= 5:
                        break
                    texto_limpio = titular.get_text(strip=True)
                    if texto_limpio and texto_limpio not in titulares_encontrados:
                        mensaje_noticias += f"- {texto_limpio}\n"
                        titulares_encontrados.add(texto_limpio)
                        count += 1
                mensaje_noticias += "\n"

            except Exception as e:
                print(f"Error durante el scraping de {sitio['nombre']}: {e}")
                mensaje_noticias += f"🔴 Error al obtener titulares de {sitio['nombre']}.\n\n"
    finally:
        # Es MUY importante cerrar el navegador al final para liberar recursos
        if driver:
            driver.quit()
    
    return mensaje_noticias

def enviar_notificacion(topic_url, mensaje, titulo):
    # Esta función no cambia
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
