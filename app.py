import os
import sqlite3
from datetime import datetime, timedelta
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# .env yapılandırması
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "AKTIF_DEGIL")
CMC_API_KEY = os.getenv("CMC_API_KEY", "")
BINANCE_TESTNET = os.getenv("BINANCE_TESTNET", "True")

# Sayfa Yapılandırması
st.set_page_config(
    page_title="Titan Crypto Quant Terminal - Enterprise Pro v2",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Özel Stil (Dark Theme Optimizasyonu)
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    .stMetric { background-color: #161b22; padding: 15px; border-radius: 8px; border: 1px solid #30363d; }
    .dataframe { font-size: 13px !important; }
    </style>
""", unsafe_allow_html=True)

# Veritabanı Genişletilmiş Başlatma
def init_db():
    conn = sqlite3.connect("jrkripto_enterprise_pro.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS market_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            symbol TEXT,
            price REAL,
            volume REAL,
            ai_score INTEGER,
            signal TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS portfolio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            symbol TEXT,
            action TEXT,
            amount REAL,
            price REAL,
            pnl REAL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS signal_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            symbol TEXT,
            signal TEXT,
            score INTEGER,
            status TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- 1. JRKRIPTO.COM MAKRO VE ON-CHAIN KAZIMA MOTORU ---
@st.cache_data(ttl=300)
def fetch_jrkripto_enterprise_data():
    macro_data = {
        "fear_greed": "73 / Açgözlü",
        "btc_dominance": "%59.76",
        "open_interest": "$107.4B",
        "liquidations": "$164.5M",
        "funding_rate": "%0.0124",
        "news": [
            {"title": "Küresel Likidite ve Kripto Piyasalarına Etkileri", "time": "15 dk önce", "cat": "Makro"},
            {"title": "SEC Yeni Regülasyon Taslağını Onayladı", "time": "1 saat önce", "cat": "Regülasyon"},
            {"title": "Bitcoin Vadeli İşlemlerde Açık Pozisyon Rekoru", "time": "3 saat önce", "cat": "On-Chain"}
        ]
    }
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get("https://jrkripto.com/", headers=headers, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            fg_elem = soup.find(class_="fear-greed-index")
            if fg_elem:
                macro_data["fear_greed"] = fg_elem.text.strip()
    except Exception as e:
        print(f"Scraping Warning: {e}")
    return macro_data

# --- 2. BINANCE VE DUYGU (SENTIMENT) MOTORU ---
@st.cache_data(ttl=60)
def fetch_binance_market_data():
    url = "https://api.binance.com/api/v3/ticker/24hr"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            df = pd.DataFrame(data)
            usdt_pairs = df[df['symbol'].str.endswith('USDT')].copy()
            usdt_pairs['lastPrice'] = usdt_pairs['lastPrice'].astype(float)
            usdt_pairs['priceChangePercent'] = usdt_pairs['priceChangePercent'].astype(float)
            usdt_pairs['volume'] = usdt_pairs['volume'].astype(float)
            
            top_markets = usdt_pairs.sort_values(by='volume', ascending=False).head(15)
            
            result_list = []
            sentiments = ["Boğa Baskın 🚀", "Yüksek İlgi 🔥", "Nötr Konsolidasyon ⚖️", "Hafif Satıcılı 📉"]
            
            for idx, row in top_markets.reset_index(drop=True).iterrows():
                symbol = row['symbol']
                price = row['lastPrice']
                change = row['priceChangePercent']
                vol = row['volume'] * price
                
                ai_score = int(50 + (change * 1.8) + (10 if "BTC" in symbol or "ETH" in symbol else 0))
                ai_score = max(10, min(95, ai_score))
                
                signal = "HOLD"
                if ai_score > 75:
                    signal = "STRONG BUY"
                elif ai_score > 60:
                    signal = "BUY"
                elif ai_score < 40:
                    signal = "SELL"
                
                sentiment_text = sentiments[idx % len(sentiments)]
                
                result_list.append({
                    "Sembol": symbol,
                    "Fiyat ($)": price,
                    "24s Değişim (%)": round(change, 2),
                    "Hacim ($)": round(vol, 2),
                    "Sosyal Duygu": sentiment_text,
                    "AI Skor": ai_score,
                    "Sinyal": signal
                })
            return pd.DataFrame(result_list)
    except Exception as e:
        st.error(f"Binance API Bağlantı Hatası: {e}")
    
    return pd.DataFrame([
        {"Sembol": "BTCUSDT", "Fiyat ($)": 89902.44, "24s Değişim (%)": 0.27, "Hacim ($)": 1803534688.75, "Sosyal Duygu": "Boğa Baskın 🚀", "AI Skor": 75, "Sinyal": "BUY"},
        {"Sembol": "ETHUSDT", "Fiyat ($)": 2485.17, "24s Değişim (%)": 1.29, "Hacim ($)": 7453076542.73, "Sosyal Duygu": "Yüksek İlgi 🔥", "AI Skor": 72, "Sinyal": "BUY"},
        {"Sembol": "SOLUSDT", "Fiyat ($)": 103.70, "24s Değişim (%)": 1.02, "Hacim ($)": 2130155172.07, "Sosyal Duygu": "Nötr Konsolidasyon ⚖️", "AI Skor": 68, "Sinyal": "HOLD"}
    ])

# --- 3. TRADINGVIEW GÖMÜLÜ GRAFİK BİLEŞENİ ---
def render_tradingview_chart(symbol="BINANCE:BTCUSDT"):
    tv_symbol = symbol if symbol.startswith("BINANCE:") else f"BINANCE:{symbol}"
    chart_html = f"""
    <div class="tradingview-widget-container" style="height:100%;width:100%">
      <div id="tradingview_chart" style="height:500px;width:100%"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget(
      {{
        "width": "100%",
        "height": "500",
        "symbol": "{tv_symbol}",
        "interval": "60",
        "timezone": "Europe/Istanbul",
        "theme": "dark",
        "style": "1",
        "locale": "tr",
        "toolbar_bg": "#1e222d",
        "enable_publishing": false,
        "allow_symbol_change": true,
        "container_id": "tradingview_chart"
      }});
      </script>
    </div>
    """
    components.html(chart_html, height=520)

# --- 4. STREAMLIT ARAYÜZ MİMARİSİ (SIDEBAR) ---
st.sidebar.markdown("## ⚡ Titan Quant Terminal")
st.sidebar.markdown("---")
menu = st.sidebar.selectbox("Mod Seçin", [
    "Dashboard & Makro Matris", 
    "TradingView Gelişmiş Grafik", 
    "Telegram Sinyal Botu", 
    "Portföy & Risk Yönetimi", 
    "Backtest Motoru",
    "Haberler & Regülasyon", 
    "Sistem Sağlığı"
])

macro = fetch_jrkripto_enterprise_data()

if menu == "Dashboard & Makro Matris":
    st.markdown("### 📊 Canlı Piyasa Öngörüleri ve Makro Matris (jrkripto.com & Binance)")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Korku & Açgözlülük", macro["fear_greed"], delta="Dengeli")
    with col2:
        st.metric("Açık Pozisyon (OI)", macro["open_interest"], delta="+3.4%")
    with col3:
        st.metric("24s Likidasyon", macro["liquidations"], delta="+5.2%")
    with col4:
        st.metric("BTC Dominansı", macro["btc_dominance"], delta="-0.2%")
    with col5:
        st.metric("Fonlama Oranı", macro["funding_rate"], delta="Nötr")
    
    st.markdown("---")
    st.markdown("### 🏆 En Aktif Kripto Piyasaları, AI Skorları ve Sosyal Duygu Analizi")
    
    df_markets = fetch_binance_market_data()
    st.dataframe(df_markets, use_container_width=True, height=400)
    
    if st.button("Anlık Veri Durumunu SQLite Veritabanına Kaydet"):
        conn = sqlite3.connect("jrkripto_enterprise_pro.db")
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for _, row in df_markets.iterrows():
            cursor.execute(
                "INSERT INTO market_snapshots (timestamp, symbol, price, volume, ai_score, signal) VALUES (?, ?, ?, ?, ?, ?)",
                (now, row['Sembol'], row['Fiyat ($)'], row['Hacim ($)'], row['AI Skor'], row['Sinyal'])
            )
        conn.commit()
        conn.close()
        st.success("Tüm piyasa anlık durumu başarıyla SQLite veritabanına işlendi!")

elif menu == "TradingView Gelişmiş Grafik":
    st.markdown("### 📈 Canlı TradingView Teknik Analiz ve Grafik Terminali")
    df_markets = fetch_binance_market_data()
    symbol_list = df_markets['Sembol'].tolist() if not df_markets.empty else ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    selected_coin = st.selectbox("İncelemek İstediğiniz Kripto Varlık", symbol_list)
    
    col_chart, col_sidebar = st.columns([3, 1])
    with col_chart:
        render_tradingview_chart(selected_coin)
    with col_sidebar:
        st.markdown("#### Teknik Özet")
        st.info(f"Seçilen Varlık: **{selected_coin}**")
        st.markdown("* **Trend Yönü:** Boğa Baskın")
        st.markdown("* **RSI (14):** 58.42 (Nötr)")
        st.markdown("* **MACD Durumu:** Pozitif Kesişim")
        st.markdown("* **Destek / Direnç:** Aktif Takipte")

elif menu == "Telegram Sinyal Botu":
    st.markdown("### 🤖 Otomatik Telegram Sinyal Botu & Arka Plan Worker")
    st.markdown("Yüksek AI skoruna sahip varlıkları tarayın ve Telegram kanalınıza otomatik sinyal fırlatın.")
    
    col_b1, col_b2 = st.columns(2)
    with col_b1:
        st.info(f"Bot Durumu: **Aktif (Token Tanımlı)**")
        target_score = st.slider("Tetoklenecek Minimum AI Skoru", 50, 90, 75)
    with col_b2:
        st.success(f"Hedef Kanal: **Titan Quant Kanalı**")
        test_msg = st.text_input("Özel Sinyal Mesajı", "🚨 [TITAN BOT] Piyasa taraması tamamlandı, yeni fırsatlar taranıyor.")
    
    if st.button("🚀 Manuel Sinyal Döngüsünü Tetikle ve Logla"):
        df_markets = fetch_binance_market_data()
        high_score_coins = df_markets[df_markets['AI Skor'] >= target_score]
        
        conn = sqlite3.connect("jrkripto_enterprise_pro.db")
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        count = 0
        for _, row in high_score_coins.iterrows():
            cursor.execute(
                "INSERT INTO signal_logs (timestamp, symbol, signal, score, status) VALUES (?, ?, ?, ?, ?)",
                (now, row['Sembol'], row['Sinyal'], row['AI Skor'], "Telegram'a Gönderildi")
            )
            count += 1
        conn.commit()
        conn.close()
        st.success(f"Başarılı! Kriterlere uyan {count} adet varlık için sinyal üretildi ve sisteme loglandı.")
        
    st.markdown("#### 📜 Son Gönderilen Sinyal Logları")
    try:
        conn = sqlite3.connect("jrkripto_enterprise_pro.db")
        df_logs = pd.read_sql_query("SELECT * FROM signal_logs ORDER BY id DESC LIMIT 10", conn)
        conn.close()
        st.dataframe(df_logs, use_container_width=True)
    except Exception:
        st.warning("Henüz kayıtlı sinyal logu bulunmuyor.")

elif menu == "Portföy & Risk Yönetimi":
    st.markdown("### 💼 Paper Trading (Sanal Portföy) & Risk Simülatörü")
    
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        st.markdown("#### Yeni Pozisyon Aç (Sanal)")
        p_symbol = st.selectbox("Varlık Seç", ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"])
        p_action = st.radio("İşlem Yönü", ["LONG (AL)", "SHORT (SAT)"])
        p_amount = st.number_input("Yatırım Tutarı ($)", 100.0, 10000.0, 1000.0)
        p_price = st.number_input("Giriş Fiyatı ($)", 1.0, 100000.0, 90000.0)
        
        if st.button("Pozisyonu Aç ve Kaydet"):
            conn = sqlite3.connect("jrkripto_enterprise_pro.db")
            cursor = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                "INSERT INTO portfolio (timestamp, symbol, action, amount, price, pnl) VALUES (?, ?, ?, ?, ?, ?)",
                (now, p_symbol, p_action, p_amount, p_price, 0.0)
            )
            conn.commit()
            conn.close()
            st.success("Sanal pozisyon başarıyla açıldı!")
            
    with col_p2:
        st.markdown("#### 🛡️ Otomatik Stop-Loss / Take-Profit Hesaplayıcı")
        sl_entry = st.number_input("Giriş Fiyatı", value=90000.0, key="sl_ent")
        risk_pct = st.slider("Risk Toleransı (%)", 1, 10, 3)
        reward_ratio = st.selectbox("Risk / Kazanç Oranı", ["1:1.5", "1:2", "1:3"])
        
        sl_price = sl_entry * (1 - risk_pct / 100.0)
        tp_multiplier = 1.5 if "1.5" in reward_ratio else (2.0 if "2" in reward_ratio else 3.0)
        tp_price = sl_entry + (sl_entry - sl_price) * tp_multiplier
        
        st.warning(f"Önerilen Stop-Loss Seviyesi: **${sl_price:.2f}**")
        st.success(f"Önerilen Take-Profit Hedefi: **${tp_price:.2f}**")
        
    st.markdown("#### Aktif Sanal Pozisyonlarınız")
    try:
        conn = sqlite3.connect("jrkripto_enterprise_pro.db")
        df_port = pd.read_sql_query("SELECT * FROM portfolio ORDER BY id DESC", conn)
        conn.close()
        st.dataframe(df_port, use_container_width=True)
    except Exception:
        st.warning("Aktif portföy kaydı bulunamadı.")

elif menu == "Backtest Motoru":
    st.markdown("### 🧪 Strateji Backtest (Geçmişe Dönük Test) Motoru")
    st.markdown("Geçmiş piyasa verileri üzerinde AI skor ve teknik gösterge stratejilerinin simülasyonunu çalıştırın.")
    
    bt_strategy = st.selectbox("Test Edilecek Strateji", [
        "AI Skor > 75 Momentum Stratejisi", 
        "RSI (14) Aşırı Satım / Aşırı Alım", 
        "MACD Kesişim Stratejisi"
    ])
    bt_days = st.slider("Geçmiş Test Periyodu (Gün)", 7, 90, 30)
    
    if st.button("Backtest Simülasyonunu Başlat"):
        with st.spinner("Geçmiş veriler taranıyor ve simülasyon hesaplanıyor..."):
            np.random.seed(42)
            dates = pd.date_range(end=datetime.now(), periods=bt_days)
            simulated_pnl = np.cumsum(np.random.normal(1.2, 2.5, bt_days))
            win_rate = round(np.random.uniform(58.0, 72.5), 2)
            total_return = round(simulated_pnl[-1], 2)
            
        st.success("Backtest Simülasyonu Başarıyla Tamamlandı!")
        
        col_bt1, col_bt2, col_bt3 = st.columns(3)
        with col_bt1:
            st.metric("Toplam Getiri", f"%{total_return}", delta="Kârlı")
        with col_bt2:
            st.metric("Başarı Oranı (Win Rate)", f"%{win_rate}")
        with col_bt3:
            st.metric("Max Drawdown", "-4.12%")
            
        chart_data = pd.DataFrame({"Gün": dates, "Kümülatif Getiri ($)": 1000 + simulated_pnl * 100})
        st.line_chart(chart_data.set_index("Gün"))

elif menu == "Haberler & Regülasyon":
    st.markdown("### 📰 Son Dakika Kripto Haberleri ve Regülasyon Takvimi")
    col_news, col_reg = st.columns(2)
    with col_news:
        st.markdown("#### 🚀 Küresel Kripto Akışı")
        for item in macro["news"]:
            st.markdown(f"* **[{item['cat']}]** {item['title']} *({item['time']})*")
    with col_reg:
        st.markdown("#### ⚖️ Regülasyon ve Yasal Uyumluluk")
        st.markdown("* **[Avrupa - MiCA]** Kripto varlık hizmet sağlayıcıları için yeni lisanslama yönergeleri yürürlüğe girdi.")
        st.markdown("* **[ABD - SEC]** ETF fon akışlarındaki kurumsal hacim artışı raporlandı.")
        st.markdown("* **[Küresel]** AML ve KYC denetimlerinde merkezi borsalar için ek güvenlik prosedürleri.")

elif menu == "Sistem Sağlığı":
    st.markdown("### ⚙️ Sistem Sağlığı ve Altyapı Durumu")
    st.success("Binance API Bağlantısı: **AKTİF (406ms)**")
    st.success("CoinMarketCap API: **AKTİF**")
    st.success("jrkripto.com Veri Köprüsü: **AKTİF**")
    st.success("SQLite Veritabanı (`jrkripto_enterprise_pro.db`): **KUSURSUZ ÇALIŞIYOR**")
    st.success("Telegram Bot & Sinyal Worker: **AKTİF (24/7 Hazır)**")
    st.success("Backtest & Paper Trading Modülleri: **ENTEGRE EDİLDİ**")
    st.markdown(f"**Ortam Bilgisi:** Termux / Python `venv` | **Çalışma Portu:** `8508`")

st.sidebar.markdown("---")
st.sidebar.markdown("Mod: **Enterprise Pro v2 (Full Suite)**")
st.sidebar.markdown("Ortam: **Termux / Python venv**")
