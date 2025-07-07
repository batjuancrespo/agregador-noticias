import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# --- CONFIGURACIÓN DE SITIOS WEB ---
# He revisado y ajustado los selectores. Estos deberían ser más robustos.
SITIOS_WEB = [
    {
        'nombre': 'AS',
        'url': 'https://as.com/',
        'selector': 'h2.s__tl' # Este funciona, lo mantenemos
    },
    {
        'nombre': 'Marca',
        'url': 'https://www.marca.com/',
        'selector': 'h2.ue-c-main-headline' # Este es el selector principal, lo mantenemos para el diagnóstico
    },
    {
        'nombre': 'El Diario Montañés',
        'url': 'https://www.eldiariomontanes.es/santander/', # He cambiado a la sección de Santander, suele ser más estable
        'selector': 'h2.voc-title a' # Un selector más general pero efectivo para esta web
    },
    {
        'nombre': 'El Mundo',
        'url': 'https://www.elmundo.es/',
        'selector': 'h2.ue-c-main-headline' # Mismo selector que Marca, suelen compartir estructura
    }
]

# --- CONFIGURACIÓN DEL TIEMPO ---
CIUDAD = "Santander"
LATITUD = 43.46
LONGITUD = -3.81

def obtener_prevision_tiempo():
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
    mensaje_noticias = "📰 Titulares del día\n\n"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'
    }

    for sitio in SITIOS_WEB:
        try:
            print(f"Obteniendo titulares de: {sitio['nombre']}...")
            response = requests.get(sitio['url'], headers=headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            titulares_html = soup.select(sitio['selector'])
            
            # --- LÍNEA DE DIAGNÓSTICO CLAVE ---
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
        except requests.RequestException as e:
            print(f"Error al conectar con {sitio['nombre']}: {e}")
            mensaje_noticias += f"🔴 Error al obtener titulares de {sitio['nombre']}.\n\n"
    return mensaje_noticias

def enviar_notificacion(topic_url, mensaje, titulo):
    try:
        requests.post(
            topic_url,
            data=mensaje.encode('utf-8'),
            headers={
                "Title": titulo,
                "Priority": "default",
                "Tags": "newspaper,partly_cloudy"
            }
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
