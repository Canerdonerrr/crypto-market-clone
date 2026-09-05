import os
import sqlite3
import time
import hmac
import hashlib
from datetime import datetime
import streamlit as st
import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()
BINANCE_TESTNET_KEY = os.getenv("BINANCE_TESTNET_KEY", "")
BINANCE_TESTNET_SECRET = os.getenv("BINANCE_TESTNET_SECRET", "")

st.set_page_config(page_title="Titan Crypto Quant Terminal v3.1", page_icon="⚡", layout="wide")

def init_db():
    conn = sqlite3.connect("jrkripto_enterprise_v3.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS live_orders (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, symbol TEXT, order_type TEXT, side TEXT, price REAL, amount REAL, status TEXT)''')
    conn.commit()
    conn.close()

init_db()

def send_binance_testnet_order(symbol, side, order_type, quantity, price):
    if not BINANCE_TESTNET_KEY or not BINANCE_TESTNET_SECRET:
        return False, "API Anahtarları Eksik!"
    url = "https://testnet.binance.vision/api/v3/order"
    timestamp = int(time.time() * 1000)
    params = {
        "symbol": symbol,
        "side": side,
        "type": order_type,
        "timeInForce": "GTC" if order_type == "LIMIT" else None,
        "quantity": quantity,
        "price": price if order_type == "LIMIT" else None,
        "timestamp": timestamp
    }
    params = {k: v for k, v in params.items() if v is not None}
    query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
    signature = hmac.new(BINANCE_TESTNET_SECRET.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
    params["signature"] = signature
    headers = {"X-MBX-APIKEY": BINANCE_TESTNET_KEY}
    try:
        response = requests.post(url, params=params, headers=headers, timeout=10)
        if response.status_code == 200:
            return True, response.json()
        else:
            return False, response.json().get("msg", "API Hatası")
    except Exception as e:
        return False, str(e)

st.sidebar.markdown("## ⚡ Titan Quant Terminal v3.1")
st.sidebar.markdown("---")
menu = st.sidebar.selectbox("Mod Seçin", ["Binance Testnet Emir Yürütme", "Sistem Sağlığı"])

if menu == "Binance Testnet Emir Yürütme":
    st.markdown("### 🌐 Binance Testnet Canlı Emir Yürütme Paneli")
    t_symbol = st.selectbox("İşlem Çifti", ["BTCUSDT", "ETHUSDT", "SOLUSDT"])
    t_side = st.selectbox("İşlem Yönü", ["BUY", "SELL"])
    t_type = st.selectbox("Emir Tipi", ["LIMIT", "MARKET"])
    t_price = st.number_input("Limit Fiyat ($)", value=91200.0)
    t_qty = st.number_input("Miktar", value=0.002, step=0.001)
    
    use_live_api = st.checkbox("Gerçek Binance Testnet API'sine Gönder", value=True)
    
    if st.button("🚀 Emri Binance Testnet'e İlet"):
        status_msg = ""
        if use_live_api:
            success, res = send_binance_testnet_order(t_symbol, t_side, t_type, t_qty, t_price)
            if success:
                status_msg = f"BAŞARILI (Testnet ID: {res.get('orderId')})"
            else:
                status_msg = f"HATA: {res}"
        else:
            status_msg = "BAŞARILI (Simülasyon)"
            
        conn = sqlite3.connect("jrkripto_enterprise_v3.db")
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("INSERT INTO live_orders (timestamp, symbol, order_type, side, price, amount, status) VALUES (?, ?, ?, ?, ?, ?, ?)", (now, t_symbol, t_type, t_side, t_price, t_qty, status_msg))
        conn.commit()
        conn.close()
        
        if "BAŞARILI" in status_msg:
            st.success(status_msg)
        else:
            st.error(status_msg)
            
    st.markdown("#### 📋 Emir Geçmişi")
    try:
        conn = sqlite3.connect("jrkripto_enterprise_v3.db")
        df_orders = pd.read_sql_query("SELECT * FROM live_orders ORDER BY id DESC", conn)
        conn.close()
        st.dataframe(df_orders, use_container_width=True)
    except:
        st.warning("Kayıt yok.")
elif menu == "Sistem Sağlığı":
    st.success("Testnet API Köprüsü Aktif")
