import streamlit as st
import pandas as pd
import requests

# --- SAYFA YAPILANDIRMASI ---
st.set_page_config(
    page_title="Crypto Market Terminal",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- KOYU TEMA (DARK THEME) & ÖZEL CSS STİLLERİ ---
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
        color: #ffffff;
    }
    .stSidebar {
        background-color: #161b22;
    }
    h1, h2, h3 {
        color: #58a6ff !important;
    }
    .metric-card {
        background-color: #21262d;
        border: 1px solid #30363d;
        padding: 15px;
        border-radius: 8px;
        text-align: center;
    }
    </style>
""", unsafe_allow_html=True)

# --- BAŞLIK VE ARAYÜZ ---
st.title("⚡ Pro Crypto Market Terminal")
st.markdown("---")

# --- VERİ ÇEKME FONKSİYONU (COINGECKO API) ---
@st.cache_data(ttl=60)
def fetch_crypto_data():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 50,
        "page": 1,
        "sparkline": "true",
        "price_change_percentage": "24h"
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"API Hatası: {response.status_code}")
            return []
    except Exception as e:
        st.error(f"Bağlantı Hatası: {e}")
        return []

# Verileri yükle
data = fetch_crypto_data()

if data:
    # --- PANDAS DATAFRAME DÖNÜŞÜMÜ ---
    df = pd.DataFrame(data)
    
    # Gerekli sütunları güvenli bir şekilde seç ve düzenle
    display_df = pd.DataFrame({
        "Sıra": df.get("market_cap_rank", pd.Series(range(1, len(df)+1))),
        "Kripto Para": df.get("name", pd.Series([""] * len(df))),
        "Sembol": df.get("symbol", pd.Series([""] * len(df))).str.upper(),
        "Fiyat ($)": df.get("current_price", pd.Series([0.0] * len(df))),
        "24s Değişim (%)": df.get("price_change_percentage_24h", pd.Series([0.0] * len(df))),
        "Piyasa Değeri ($)": df.get("market_cap", pd.Series([0.0] * len(df)))
    })

    # --- KENAR ÇUBUĞU (SIDEBAR) FİLTRELERİ ---
    st.sidebar.header("🔍 Filtreleme ve Ayarlar")
    search_query = st.sidebar.text_input("Kripto Ara (İsim veya Sembol)", "").upper()
    
    max_mcap = int(display_df["Piyasa Değeri ($)"].max()) if not display_df["Piyasa Değeri ($)"].empty else 1000000
    min_market_cap = st.sidebar.slider(
        "Minimum Piyasa Değeri ($)", 
        0, 
        max_mcap, 
        0, 
        step=max(1, max_mcap // 100)
    )

    # Filtreleme Mantığı
    filtered_df = display_df[display_df["Piyasa Değeri ($)"] >= min_market_cap]
    
    if search_query:
        filtered_df = filtered_df[
            filtered_df["Kripto Para"].str.upper().str.contains(search_query, na=False) |
            filtered_df["Sembol"].str.upper().str.contains(search_query, na=False)
        ]

    # --- ÜST ÖZET METRİKLERİ ---
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="metric-card"><h3>Toplam Coin</h3><p><b>{len(display_df)}</b></p></div>', unsafe_allow_html=True)
    with col2:
        total_mcap = display_df["Piyasa Değeri ($)"].sum()
        st.markdown(f'<div class="metric-card"><h3>Toplam Piyasa Değeri</h3><p><b>${total_mcap:,.0f}</b></p></div>', unsafe_allow_html=True)
    with col3:
        avg_change = display_df["24s Değişim (%)"].mean()
        color = "#3fb950" if avg_change >= 0 else "#f85149"
        st.markdown(f'<div class="metric-card"><h3>Ortalama 24s Değişim</h3><p style="color:{color}"><b>{avg_change:.2f}%</b></p></div>', unsafe_allow_html=True)
    with col4:
        st.markdown('<div class="metric-card"><h3>Veri Kaynağı</h3><p><b>CoinGecko API</b></p></div>', unsafe_allow_html=True)

    st.markdown("### 📊 Canlı Piyasa Tablosu")
    
    # --- TABLO GÖSTERİMİ (Pyarrow Gerektirmeyen st.table Alternatifi) ---
    st.table(filtered_df)

else:
    st.warning("Piyasa verileri yüklenemedi. Lütfen internet bağlantınızı veya API limitlerini kontrol edin.")
