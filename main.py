import os
import requests
from bs4 import BeautifulSoup

# --- CONFIGURACIÓN DE SITIOS WEB ---
# Añade o modifica las páginas que quieres scrapear.
# 'nombre': Aparecerá en la notificación.
# 'url': La dirección de la página.
# 'selector': El selector CSS para encontrar los titulares. (Usa "Inspeccionar" en tu navegador para encontrarlo)
SITIOS_WEB = [
    {
        'nombre': 'El País',
        'url': 'https://elpais.com',
        'selector': 'h2.c_t'
    },
    {
        'nombre': 'El Mundo',
        'url': 'https://www.elmundo.es/',
        'selector': 'h2.ue-c-main-headline'
    },
    {
        'nombre': 'BBC News Mundo',
        'url': 'https://www.bbc.com/mundo',
        'selector': 'h3.lx-stream-post__header-text'
    },
    # Puedes añadir más sitios aquí. Ejemplo:
    # {
    #     'nombre': 'The Verge',
    #     'url': 'https://www.theverge.com/',
    #     'selector': 'h2.font-polysans'
    # }
]

def obtener_titulares():
    """
    Extrae los 5 primeros titulares de cada sitio web configurado.
    """
    mensaje_final = "📰 Titulares del día\n\n"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    for sitio in SITIOS_WEB:
        try:
            print(f"Obteniendo titulares de: {sitio['nombre']}...")
            response = requests.get(sitio['url'], headers=headers, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            titulares_html = soup.select(sitio['selector'])
            
            if not titulares_html:
                print(f"  -> No se encontraron titulares para {sitio['nombre']} con el selector '{sitio['selector']}'.")
                continue

            mensaje_final += f"🔵 == {sitio['nombre']} ==\n"
            
            count = 0
            titulares_encontrados = set() # Usamos un set para evitar titulares duplicados
            for titular in titulares_html:
                if count >= 5:
                    break
                texto_limpio = titular.get_text(strip=True)
                if texto_limpio and texto_limpio not in titulares_encontrados:
                    mensaje_final += f"- {texto_limpio}\n"
                    titulares_encontrados.add(texto_limpio)
                    count += 1
            mensaje_final += "\n"

        except requests.RequestException as e:
            print(f"Error al conectar con {sitio['nombre']}: {e}")
            mensaje_final += f"🔴 Error al obtener titulares de {sitio['nombre']}.\n\n"
        except Exception as e:
            print(f"Ocurrió un error inesperado con {sitio['nombre']}: {e}")

    return mensaje_final

def enviar_notificacion(topic_url, mensaje):
    """
    Envía el mensaje de los titulares al topic de ntfy.
    """
    try:
        requests.post(
            topic_url,
            data=mensaje.encode('utf-8'),
            headers={
                "Title": "Resumen de Noticias Diario",
                "Priority": "default",
                "Tags": "newspaper"
            }
        )
        print("¡Notificación enviada con éxito!")
    except Exception as e:
        print(f"Error al enviar la notificación a ntfy: {e}")

if __name__ == "__main__":
    # Esta línea es clave: obtiene la URL de tu topic desde los "Secrets" de GitHub.
    NTFY_TOPIC_URL = os.getenv('NTFY_TOPIC')

    if not NTFY_TOPIC_URL:
        print("Error: La variable de entorno 'NTFY_TOPIC' no está configurada.")
        # Para pruebas locales en tu ordenador, puedes descomentar la siguiente línea:
        # NTFY_TOPIC_URL = "https://ntfy.sh/noticias-para-batju-2025"
        exit(1) # Salimos si no hay URL para evitar errores
    
    titulares = obtener_titulares()
    enviar_notificacion(NTFY_TOPIC_URL, titulares)
