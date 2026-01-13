#!/bin/bash
# Schnell-Setup für modulare Struktur - VERBESSERTE VERSION
# Führe dieses Skript in deinem files/ Ordner aus

set -e

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Modulare Struktur - Quick Setup v2       ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}"
echo

# Prüfe ob wir im richtigen Ordner sind
if [ ! -f "main.py" ]; then
    echo -e "${YELLOW}⚠ main.py nicht gefunden!${NC}"
    echo "Führe dieses Skript im files/ Ordner aus:"
    echo "  cd ~/Dokumente/vsCode/API\ -\ Amazon\ Selenium/v7/files"
    echo "  bash setup.sh"
    exit 1
fi

echo -e "${GREEN}✓ main.py gefunden${NC}"
echo

# Prüfe Python-Version
echo -e "${BLUE}Prüfe Python-Version...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 nicht gefunden!${NC}"
    echo "Installiere Python 3.8+:"
    echo "  Ubuntu/Debian: sudo apt-get install python3"
    echo "  macOS: brew install python3"
    exit 1
fi

python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}✓ Python $python_version gefunden${NC}"

# Prüfe Python-Mindestversion (3.8)
required_major=3
required_minor=8
current_major=$(echo $python_version | cut -d. -f1)
current_minor=$(echo $python_version | cut -d. -f2)

if [ "$current_major" -lt "$required_major" ] || \
   ([ "$current_major" -eq "$required_major" ] && [ "$current_minor" -lt "$required_minor" ]); then
    echo -e "${RED}❌ Python $required_major.$required_minor+ erforderlich!${NC}"
    exit 1
fi

echo

# Erstelle src/ falls nicht vorhanden
mkdir -p src
echo -e "${GREEN}✓ src/ Ordner erstellt${NC}"

# Verschiebe falsch platzierte Dateien
if [ -f "config.py" ]; then
    mv config.py src/
    echo -e "${GREEN}✓ config.py nach src/ verschoben${NC}"
fi

if [ -f "pdf_processor.py" ]; then
    mv pdf_processor.py src/
    echo -e "${GREEN}✓ pdf_processor.py nach src/ verschoben${NC}"
fi

# Entferne falschen Unterordner
if [ -d "src/config" ]; then
    rm -rf src/config
    echo -e "${GREEN}✓ Falscher src/config/ Ordner entfernt${NC}"
fi

echo

# Prüfe welche Module fehlen
echo -e "${BLUE}Prüfe Module in src/...${NC}"

REQUIRED_MODULES=(
    "__init__.py"
    "config.py"
    "logger.py"
    "amazon_downloader.py"
    "pdf_processor.py"
    "file_manager.py"
    "notification.py"
)

MISSING=0

for module in "${REQUIRED_MODULES[@]}"; do
    if [ -f "src/$module" ]; then
        echo -e "  ${GREEN}✓${NC} $module"
    else
        echo -e "  ${YELLOW}✗${NC} $module ${YELLOW}FEHLT${NC}"
        MISSING=$((MISSING + 1))
    fi
done

echo

# Prüfe Konfigurationsdateien
echo -e "${BLUE}Prüfe Konfigurationsdateien...${NC}"

if [ -f "config.yaml" ]; then
    echo -e "  ${GREEN}✓${NC} config.yaml"
else
    echo -e "  ${YELLOW}✗${NC} config.yaml ${YELLOW}FEHLT${NC}"
    MISSING=$((MISSING + 1))
fi

if [ -f "config.yaml.example" ]; then
    echo -e "  ${GREEN}✓${NC} config.yaml.example"
else
    echo -e "  ${YELLOW}✗${NC} config.yaml.example ${YELLOW}FEHLT${NC}"
fi

echo

# Prüfe requirements.txt
if [ -f "requirements.txt" ]; then
    echo -e "${BLUE}Installiere Python-Abhängigkeiten...${NC}"
    
    if python3 -m pip install -r requirements.txt > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Abhängigkeiten installiert${NC}"
    else
        echo -e "${YELLOW}⚠ Fehler beim Installieren von Abhängigkeiten${NC}"
        echo "  Versuche manuell: pip install -r requirements.txt"
    fi
else
    echo -e "${YELLOW}⚠ requirements.txt nicht gefunden${NC}"
    echo "  Installiere manuell: pip install pyyaml pdfplumber requests"
fi

echo

# Prüfe erforderliche Python-Module
echo -e "${BLUE}Prüfe Python-Module...${NC}"

python3 << 'EOF'
import sys

modules = ['yaml', 'pdfplumber', 'requests']
missing = []

for module in modules:
    try:
        __import__(module)
        print(f"  ✓ {module}")
    except ImportError:
        print(f"  ✗ {module} FEHLT")
        missing.append(module)

if missing:
    print(f"\nInstalliere fehlende Module:")
    print(f"  pip install {' '.join(missing)}")
    sys.exit(1)
EOF

echo

# Zusammenfassung
if [ $MISSING -eq 0 ]; then
    echo -e "${GREEN}╔════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  ✓ Setup erfolgreich!                     ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════╝${NC}"
    echo
    echo "Nächste Schritte:"
    echo "  1. cp config.yaml.example config.yaml"
    echo "  2. nano config.yaml  # Anpassen"
    echo "  3. python3 main.py --help"
    echo
else
    echo -e "${YELLOW}╔════════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║  ⚠ $MISSING Module/Dateien fehlen!        ║${NC}"
    echo -e "${YELLOW}╚════════════════════════════════════════════╝${NC}"
    echo
    echo "Lade die fehlenden Module herunter und kopiere sie nach src/"
    echo
    echo "Falls alle Module in Downloads sind:"
    echo "  cp ~/Downloads/src/* src/"
    exit 1
fi

# Zeige finale Struktur
echo
echo -e "${BLUE}Aktuelle Struktur:${NC}"
if command -v tree &> /dev/null; then
    tree -L 2 -I 'venv|__pycache__|*.pyc' || ls -la
else
    ls -la
fi
