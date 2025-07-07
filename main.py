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

# --- CONFIGURACIÓN DE SITIOS WEB (SELECTORES FINALES Y ROBUSTOS) ---
SITIOS_WEB = [
    # AS: La portada de España, selector preciso para los titulares principales.
    {'nombre': 'AS', 'url': 'https://as.com/', 'selector': 'article.s-art h2 > a'},
    {'nombre': 'Marca', 'url': 'https://www.marca.com/', 'selector': 'h2.ue-c-main-headline'},
    # El Diario Montañés: Portada principal, que es más estable.
    {'nombre': 'El Diario Montañés', 'url': 'https://www.eldiariomontanes.es/', 'selector': 'h2.voc-title a'},
    {'nombre': 'El Mundo', 'url': 'https://www.elmundo.es/', 'selector': 'h2.ue-c-main-headline'}
]

CIUDAD = "Santander"
LATITUD = 43.46
LONGITUD = -3.81

def handle_overlays(driver):
    """
    Función multi-paso que maneja diferentes tipos de banners y pop-ups,
    incluyendo los que están dentro de iframes.
    """
    time.sleep(3) # Pausa inicial para que aparezcan los banners

    # --- Nivel 1: Banners de Cookies en iFrames (AS, Marca, El Mundo) ---
    try:
        # Intenta encontrar el iframe de Sourcepoint (usado por muchos)
        iframe = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, "//iframe[contains(@id, 'sp_message_iframe')]"))
        )
        driver.switch_to.frame(iframe)
        print("  -> [LOG] iFrame de consentimiento encontrado. Entrando...")
        # Una vez dentro, busca un botón genérico de aceptar
        WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(@title, 'Accept') or contains(@title, 'Agree')]"))
        ).click()
        print("  -> [LOG] Botón 'Accept' en iFrame pulsado.")
        # MUY IMPORTANTE: Volver al contenido principal
        driver.switch_to.default_content()
        time.sleep(2)
        return # Si hemos manejado este iframe, probablemente sea suficiente.
    except TimeoutException:
        print("  -> [LOG] No se encontró el iFrame de cookies de Sourcepoint.")
        driver.switch_to.default_content() # Asegurarse de volver al contexto principal

    # --- Nivel 2: Banners de cookies en la página principal (El Diario Montañés) ---
    try:
        dm_accept_button = WebDriverWait(driver, 
