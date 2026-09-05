#!/bin/bash
cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
    echo "[!] Sanal ortam bulunamadı, lütfen kurulum adımlarını izleyin."
    exit 1
fi

source venv/bin/activate

echo "[+] TITAN Pro Sistemi Başlatılıyor..."
exec ./venv/bin/streamlit run app.py --server.port=8502 --server.enableCORS=false --server.enableXsrfProtection=false
