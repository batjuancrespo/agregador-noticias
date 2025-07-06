import feedparser
import requests
import os
import textwrap

# --- Configuración ---
FEEDS = {
    "AS": "https://as.com/rss/diarioas/portada.xml",
    "Marca": "https://e00-marca.uecdn.es/rss/portada.xml",
    "El Diario Montañés": "https://www.eldiariomontanes.es/rss/2.0/portada/",
    "El Mundo": "https://www.elmundo.es/rss/portada.xml"
}
ARTICLES_PER_FEED = 5
NTFY_TOPIC = os.getenv("NTFY_TOPIC") # Obtiene el tema desde los secretos de GitHub

def fetch_and_format_news():
    """
    Recopila y formatea las noticias de los feeds RSS.
    """
    full_message = "Resumen de noticias de hoy\n"
    full_message += "=========================\n\n"
    
    for name, url in FEEDS.items():
        try:
            print(f"Obteniendo noticias de: {name}...")
            feed = feedparser.parse(url)
            
            if feed.bozo:
                print(f"Advertencia: Problema al parsear el feed de {name}. Razón: {feed.bozo_exception}")

            full_message += f"🗞️ {name.upper()}\n"
            
            # Limita el número de artículos a procesar
            entries = feed.entries[:ARTICLES_PER_FEED]
            
            if not entries:
                full_message += "- No se encontraron noticias recientes.\n"
            
            for entry in entries:
                title = entry.title.strip()
                link = entry.link
                # Acorta el título si es muy largo para la notificación
                short_title = textwrap.shorten(title, width=80, placeholder="...")
                full_message += f"- [{short_title}]({link})\n"
            
            full_message += "\n" # Espacio entre periódicos
        except Exception as e:
            print(f"Error al procesar el feed de {name}: {e}")
            full_message += f"❌ Error al obtener noticias de {name}.\n\n"
            
    return full_message

def send_notification(message):
    """
    Envía el mensaje de noticias al tema de ntfy.
    """
    if not NTFY_TOPIC:
        print("Error: La variable de entorno NTFY_TOPIC no está configurada.")
        return

    try:
        requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=message.encode('utf-8'),
            headers={
                "Title": "📰 Tu Resumen de Noticias Diario",
                "Tags": "newspaper,news",
                "Markdown": "yes" # Habilita el formato Markdown
            }
        )
        print("¡Notificación enviada con éxito!")
    except Exception as e:
        print(f"Error al enviar la notificación: {e}")

if __name__ == "__main__":
    news_summary = fetch_and_format_news()
    print("\n--- Mensaje a Enviar ---")
    print(news_summary)
    print("------------------------\n")
    send_notification(news_summary)
