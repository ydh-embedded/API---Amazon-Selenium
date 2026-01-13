#!/usr/bin/env python3
"""
HAUPTPROGRAMM - Amazon Steuer Automatisierung
Orchestriert alle Module

Verwendung:
    python main.py                    # Kompletter Workflow
    python main.py --only-download    # Nur Amazon Download
    python main.py --only-process     # Nur PDF Verarbeitung
    python main.py --check            # Nur Prüfung ohne Betrag
"""

import argparse
import logging
from pathlib import Path
from datetime import datetime
import sys

# Module importieren
from src.config import Config
from src.amazon_downloader import AmazonDownloader
from src.pdf_processor import PDFProcessor
from src.file_manager import FileManager
from src.notification import Notification
from src.logger import setup_logging


class SteuerAutomation:
    """Hauptklasse - orchestriert alle Module"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialisiere mit Konfiguration"""
        try:
            self.config = Config(config_path)
        except FileNotFoundError as e:
            print(f"❌ Fehler: {e}")
            sys.exit(1)
        except ValueError as e:
            print(f"❌ Konfigurationsfehler: {e}")
            sys.exit(1)
        
        # Logger mit Config-Einstellungen initialisieren
        global logger
        logger = setup_logging(self.config.log_dir, self.config.log_level)
        
        self.stats = {
            "amazon_downloads": 0,
            "pdfs_verarbeitet": 0,
            "betraege_erkannt": 0,
            "fehler": 0,
            "ohne_betrag": 0,
            "start_zeit": datetime.now()
        }
        
        logger.info("Steuer-Automatisierung initialisiert")
    
    def schritt_1_amazon_download(self, year: int = None) -> bool:
        """Schritt 1: Amazon Rechnungen herunterladen"""
        logger.info("=" * 60)
        logger.info("SCHRITT 1: Amazon Rechnungen herunterladen")
        logger.info("=" * 60)
        
        try:
            downloader = AmazonDownloader(self.config)
            anzahl = downloader.download_invoices(year)
            
            self.stats["amazon_downloads"] = anzahl
            logger.info(f"✓ {anzahl} Rechnungen heruntergeladen")
            return True
            
        except Exception as e:
            logger.error(f"✗ Amazon Download fehlgeschlagen: {e}")
            self.stats["fehler"] += 1
            return False
    
    def schritt_2_pdfs_verarbeiten(self) -> bool:
        """Schritt 2: PDFs verarbeiten (Betrag extrahieren)"""
        logger.info("=" * 60)
        logger.info("SCHRITT 2: PDFs verarbeiten")
        logger.info("=" * 60)
        
        try:
            processor = PDFProcessor(self.config)
            file_mgr = FileManager(self.config)
            
            # Finde alle Amazon PDFs
            pdfs = file_mgr.finde_neue_pdfs()
            
            if not pdfs:
                logger.warning("Keine neuen PDFs gefunden")
                return True
            
            logger.info(f"Gefunden: {len(pdfs)} PDFs")
            
            # Verarbeite jede PDF
            for pdf_path in pdfs:
                try:
                    # Extrahiere Betrag
                    betrag = processor.extrahiere_betrag(pdf_path)
                    
                    # Verschiebe und benenne um
                    ziel = file_mgr.verarbeite_pdf(pdf_path, betrag)
                    
                    # Statistik
                    self.stats["pdfs_verarbeitet"] += 1
                    if betrag is not None and betrag > 0:
                        self.stats["betraege_erkannt"] += 1
                    else:
                        self.stats["ohne_betrag"] += 1
                    
                    logger.info(f"✓ Verarbeitet: {pdf_path.name} → {ziel.name}")
                    
                except Exception as e:
                    logger.error(f"✗ Fehler bei {pdf_path.name}: {e}")
                    self.stats["fehler"] += 1
            
            return True
            
        except Exception as e:
            logger.error(f"✗ PDF-Verarbeitung fehlgeschlagen: {e}")
            return False
    
    def schritt_3_aufraeumen(self):
        """Schritt 3: Aufräumen (temporäre Dateien)"""
        logger.info("=" * 60)
        logger.info("SCHRITT 3: Aufräumen")
        logger.info("=" * 60)
        
        try:
            file_mgr = FileManager(self.config)
            file_mgr.cleanup()
            logger.info("✓ Aufräumen abgeschlossen")
        except Exception as e:
            logger.warning(f"Aufräumen mit Warnung: {e}")
    
    def schritt_4_benachrichtigung(self):
        """Schritt 4: Benachrichtigung senden"""
        logger.info("=" * 60)
        logger.info("SCHRITT 4: Benachrichtigung")
        logger.info("=" * 60)
        
        try:
            notifier = Notification(self.config)
            notifier.sende_zusammenfassung(self.stats)
            logger.info("✓ Benachrichtigung gesendet")
        except Exception as e:
            logger.warning(f"Benachrichtigung fehlgeschlagen: {e}")
    
    def zeige_zusammenfassung(self):
        """Zeige finale Zusammenfassung"""
        self.stats["end_zeit"] = datetime.now()
        dauer = (self.stats["end_zeit"] - self.stats["start_zeit"]).seconds
        
        logger.info("=" * 60)
        logger.info("ZUSAMMENFASSUNG")
        logger.info("=" * 60)
        logger.info(f"Amazon Downloads:     {self.stats['amazon_downloads']}")
        logger.info(f"PDFs verarbeitet:     {self.stats['pdfs_verarbeitet']}")
        logger.info(f"Beträge erkannt:      {self.stats['betraege_erkannt']}")
        logger.info(f"Ohne Betrag:          {self.stats['ohne_betrag']}")
        logger.info(f"Fehler:               {self.stats['fehler']}")
        logger.info(f"Dauer:                {dauer}s")
        logger.info("=" * 60)
        
        if self.stats['ohne_betrag'] > 0:
            logger.warning(f"{self.stats['ohne_betrag']} Dateien erfordern manuelle Prüfung!")
        
        return self.stats
    
    def ausfuehren(self, nur_download: bool = False, nur_verarbeitung: bool = False):
        """
        Führe komplette Automatisierung aus
        
        Args:
            nur_download: Nur Amazon Download ausführen
            nur_verarbeitung: Nur PDF Verarbeitung ausführen
        """
        logger.info("🚀 Steuer-Automatisierung gestartet")
        
        erfolg = True
        
        # Schritt 1: Amazon Download
        if not nur_verarbeitung:
            if not self.schritt_1_amazon_download():
                erfolg = False
        
        # Schritt 2: PDF Verarbeitung
        if not nur_download:
            if not self.schritt_2_pdfs_verarbeiten():
                erfolg = False
        
        # Schritt 3: Aufräumen
        if not nur_download and not nur_verarbeitung:
            self.schritt_3_aufraeumen()
        
        # Schritt 4: Benachrichtigung
        if not nur_download and not nur_verarbeitung:
            self.schritt_4_benachrichtigung()
        
        # Zusammenfassung
        self.zeige_zusammenfassung()
        
        logger.info("✓ Steuer-Automatisierung abgeschlossen")
        
        return erfolg


def main():
    """Hauptfunktion - CLI Interface"""
    parser = argparse.ArgumentParser(
        description="Amazon Steuer Automatisierung - Modulare Version",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
  python main.py                     # Kompletter Workflow
  python main.py --year 2026         # Nur 2026
  python main.py --only-download     # Nur Download
  python main.py --only-process      # Nur Verarbeitung
  python main.py --check             # Nur Prüfung ohne Betrag
        """
    )
    
    parser.add_argument(
        '--year',
        type=int,
        help='Nur Rechnungen aus diesem Jahr (z.B. 2026)'
    )
    
    parser.add_argument(
        '--only-download',
        action='store_true',
        help='Nur Amazon Download ausführen'
    )
    
    parser.add_argument(
        '--only-process',
        action='store_true',
        help='Nur PDF Verarbeitung ausführen'
    )
    
    parser.add_argument(
        '--check',
        action='store_true',
        help='Nur Dateien ohne Betrag prüfen'
    )
    
    parser.add_argument(
        '--config',
        default='config.yaml',
        help='Pfad zur Konfigurationsdatei'
    )
    
    args = parser.parse_args()
    
    # Nur Prüfung
    if args.check:
        from src.file_manager import FileManager
        config = Config(args.config)
        logger = setup_logging(config.log_dir, config.log_level)
        file_mgr = FileManager(config)
        file_mgr.zeige_dateien_ohne_betrag()
        return
    
    # Hauptausführung
    try:
        app = SteuerAutomation(args.config)
        
        erfolg = app.ausfuehren(
            nur_download=args.only_download,
            nur_verarbeitung=args.only_process
        )
        
        sys.exit(0 if erfolg else 1)
        
    except KeyboardInterrupt:
        logger.info("\n⚠ Abbruch durch Benutzer")
        sys.exit(1)
    except Exception as e:
        logger.error(f"✗ Kritischer Fehler: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
