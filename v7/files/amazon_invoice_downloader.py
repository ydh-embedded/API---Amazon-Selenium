#!/usr/bin/env python3
"""
Amazon Invoice Downloader
Automatisierter Download von Amazon-Rechnungen mit Brave Browser
Erstellt für: Danny (yDh-embedded)
"""

import os
import sys
import time
import argparse
import yaml
from pathlib import Path
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

class AmazonInvoiceDownloader:
    def __init__(self, config_path):
        """Initialisiere den Downloader mit Konfiguration"""
        self.config = self.load_config(config_path)
        self.driver = None
        self.download_dir = Path(self.config['download']['directory']).expanduser()
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
    def load_config(self, config_path):
        """Lade YAML-Konfiguration"""
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def setup_driver(self):
        """Konfiguriere Selenium mit Brave Browser"""
        options = webdriver.ChromeOptions()
        
        # Brave Binary Pfad
        brave_path = self.config['browser']['brave_path']
        if not Path(brave_path).exists():
            raise FileNotFoundError(f"Brave nicht gefunden: {brave_path}")
        
        options.binary_location = brave_path
        
        # Brave Profil verwenden (mit gespeicherten Login-Daten)
        if self.config['browser']['use_profile']:
            profile_path = Path(self.config['browser']['profile_path']).expanduser()
            options.add_argument(f"--user-data-dir={profile_path}")
            options.add_argument(f"--profile-directory={self.config['browser']['profile_name']}")
        
        # Download-Einstellungen
        prefs = {
            "download.default_directory": str(self.download_dir.absolute()),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
            "plugins.always_open_pdf_externally": True
        }
        options.add_experimental_option("prefs", prefs)
        
        # Optional: Headless Mode
        if self.config['browser'].get('headless', False):
            options.add_argument('--headless=new')
        
        # Chrome Service (nutzt system chromedriver)
        # self.driver = webdriver.Chrome(options=options) alte Variante
        # ✅ NEU (mit webdriver-manager)
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.chrome.service import Service

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        # self.driver.set_page_load_timeout(30)
        # ✅ BESSER (mit Timeout)
        self.driver.set_page_load_timeout(60)       # Seite lädt max 30 Sekunden
        self.driver.implicitly_wait(30)             # Elemente suchen max 10 Sekunden
        
        print("✓ Browser gestartet")
    
    def login_check(self):
        """Prüfe ob bereits eingeloggt, sonst warte auf manuellen Login"""
        self.driver.get("https://www.amazon.de/gp/your-account/order-history")
        
        try:
            # Warte auf Login-Seite oder Order-Seite
            WebDriverWait(self.driver, 10).until(
                lambda d: "order-history" in d.current_url or "ap/signin" in d.current_url
            )
            
            if "ap/signin" in self.driver.current_url:
                print("\n⚠ Bitte manuell bei Amazon einloggen...")
                print("Drücke ENTER wenn du eingeloggt bist...")
                input()
                
                # Warte bis Order-History geladen ist
                WebDriverWait(self.driver, 60).until(
                    EC.url_contains("order-history")
                )
                print("✓ Login erfolgreich")
            else:
                print("✓ Bereits eingeloggt")
                
        except TimeoutException:
            print("❌ Timeout beim Login")
            raise
    
    def get_orders(self, year=None):
        """Hole Liste aller Bestellungen"""
        orders = []
        
        # Filtere nach Jahr falls angegeben
        if year:
            filter_url = f"https://www.amazon.de/gp/your-account/order-history?orderFilter=year-{year}"
            self.driver.get(filter_url)
        else:
            self.driver.get("https://www.amazon.de/gp/your-account/order-history")
        
        time.sleep(2)
        
        page = 1
        while True:
            print(f"\n📄 Verarbeite Seite {page}...")
            
            try:
                # Finde alle Bestellkarten
                order_cards = self.driver.find_elements(By.CSS_SELECTOR, ".order-card, .order")
                
                for card in order_cards:
                    try:
                        # Order-ID extrahieren
                        order_id_element = card.find_element(By.XPATH, ".//span[contains(text(), 'Bestellung aufgegeben')]/../..//span[contains(text(), 'Bestellnummer:')]")
                        order_id = order_id_element.text.replace("Bestellnummer:", "").strip()
                        
                        # Rechnung-Link finden
                        try:
                            invoice_link = card.find_element(By.XPATH, ".//a[contains(@href, 'invoice')]")
                            invoice_url = invoice_link.get_attribute('href')
                            
                            orders.append({
                                'id': order_id,
                                'invoice_url': invoice_url
                            })
                            print(f"  ✓ Gefunden: {order_id}")
                            
                        except NoSuchElementException:
                            # Keine Rechnung verfügbar (z.B. Marketplace-Seller)
                            pass
                            
                    except Exception as e:
                        print(f"  ⚠ Fehler beim Verarbeiten einer Bestellung: {e}")
                        continue
                
                # Prüfe ob "Nächste Seite" existiert
                try:
                    next_button = self.driver.find_element(By.CSS_SELECTOR, ".a-pagination .a-last:not(.a-disabled)")
                    next_button.click()
                    time.sleep(2)
                    page += 1
                except NoSuchElementException:
                    print("\n✓ Alle Seiten verarbeitet")
                    break
                    
            except Exception as e:
                print(f"❌ Fehler beim Laden der Seite: {e}")
                break
        
        return orders
    
    def download_invoice(self, order):
        """Lade einzelne Rechnung herunter"""
        try:
            self.driver.get(order['invoice_url'])
            time.sleep(2)
            
            # Warte auf PDF-Download oder PDF-Anzeige
            # Amazon zeigt manchmal PDFs direkt an oder lädt sie herunter
            
            filename = f"Amazon_Rechnung_{order['id']}.pdf"
            expected_file = self.download_dir / filename
            
            # Warte kurz auf Download
            time.sleep(3)
            
            # Suche nach heruntergeladener Datei
            downloads = list(self.download_dir.glob("*.pdf"))
            if downloads:
                # Neueste PDF umbenennen
                latest_pdf = max(downloads, key=lambda p: p.stat().st_mtime)
                if not expected_file.exists():
                    latest_pdf.rename(expected_file)
                return True
            
            return False
            
        except Exception as e:
            print(f"  ❌ Fehler beim Download {order['id']}: {e}")
            return False
    
    def download_all(self, year=None):
        """Hauptfunktion: Alle Rechnungen herunterladen"""
        try:
            self.setup_driver()
            self.login_check()
            
            print(f"\n🔍 Suche Bestellungen{f' für {year}' if year else ''}...")
            orders = self.get_orders(year)
            
            if not orders:
                print("\n⚠ Keine Bestellungen mit Rechnungen gefunden")
                return
            
            print(f"\n✓ {len(orders)} Bestellungen mit Rechnungen gefunden")
            print(f"\n📥 Starte Download nach: {self.download_dir}")
            
            successful = 0
            failed = 0
            
            for i, order in enumerate(orders, 1):
                print(f"\n[{i}/{len(orders)}] {order['id']}")
                
                # Prüfe ob bereits vorhanden
                filename = f"Amazon_Rechnung_{order['id']}.pdf"
                if (self.download_dir / filename).exists():
                    print(f"  ⏭ Bereits vorhanden")
                    successful += 1
                    continue
                
                if self.download_invoice(order):
                    print(f"  ✓ Heruntergeladen")
                    successful += 1
                else:
                    print(f"  ❌ Fehlgeschlagen")
                    failed += 1
                
                # Pause zwischen Downloads
                if i < len(orders):
                    time.sleep(self.config['download'].get('delay_seconds', 2))
            
            print(f"\n{'='*50}")
            print(f"✓ Erfolgreich: {successful}")
            print(f"❌ Fehlgeschlagen: {failed}")
            print(f"📁 Speicherort: {self.download_dir}")
            print(f"{'='*50}")
            
        except KeyboardInterrupt:
            print("\n\n⚠ Abbruch durch Benutzer")
        except Exception as e:
            print(f"\n❌ Fehler: {e}")
            raise
        finally:
            if self.driver:
                self.driver.quit()
                print("\n✓ Browser geschlossen")

def main():
    parser = argparse.ArgumentParser(
        description='Amazon Invoice Downloader - Automatisierter Rechnungsdownload',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--year',
        type=int,
        help='Nur Bestellungen aus diesem Jahr herunterladen (z.B. 2024)'
    )
    
    parser.add_argument(
        '--download-all',
        action='store_true',
        help='Alle verfügbaren Rechnungen herunterladen'
    )
    
    parser.add_argument(
        '--config',
        default=Path(__file__).parent / 'config.yaml',
        help='Pfad zur Konfigurationsdatei (Standard: config.yaml)'
    )
    
    args = parser.parse_args()
    
    if not args.download_all and not args.year:
        parser.print_help()
        sys.exit(1)
    
    # Banner
    print("\n" + "="*50)
    print("Amazon Invoice Downloader")
    print("="*50)
    
    # Initialisiere und starte
    downloader = AmazonInvoiceDownloader(args.config)
    downloader.download_all(year=args.year)

if __name__ == "__main__":
    main()