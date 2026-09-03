import streamlit as st
import pandas as pd
import requests
import plotly.express as px

st.set_page_config(
    page_title="CryptoMarket Pro - CoinMarketCap Klonu",
    page_icon="📈",
    layout="wide"
)

st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
        color: #ffffff;
    }
    </style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=60)
def get_crypto_data():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 50,
        "page": 1,
        "sparkline": "true"
    }
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return pd.DataFrame(response.json())
        else:
            return pd.DataFrame()
    except:
        return pd.DataFrame()

st.title("📊 CryptoMarket Pro (CoinMarketCap Clone)")
st.markdown("Python ve Streamlit altyapısı ile geliştirilmiş canlı kripto para takip paneli.")

df = get_crypto_data()

if not df.empty:
    total_market_cap = df['market_cap'].sum()
    total_volume = df['total_volume'].sum()
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Toplam Piyasa Değeri", f"${total_market_cap:,.0f}")
    col2.metric("24s Toplam Hacim", f"${total_volume:,.0f}")
    col3.metric("Listelenen Varlık", f"{len(df)} Adet")

    st.divider()
    search_query = st.text_input("🔍 Kripto Para Ara:", "")
    if search_query:
        filtered_df = df[df['name'].str.contains(search_query, case=False, na=False) | 
                         df['symbol'].str.contains(search_query, case=False, na=False)]
    else:
        filtered_df = df

    display_df = filtered_df[['market_cap_rank', 'name', 'symbol', 'current_price', 
                              'price_change_percentage_24h', 'total_volume', 'market_cap']].copy()
    display_df.columns = ['Sıra', 'İsim', 'Sembol', 'Fiyat (USD)', '24s Değişim (%)', '24s Hacim', 'Piyasa Değeri']
    
    st.dataframe(
        display_df.style.format({
            'Fiyat (USD)': '${:,.2f}',
            '24s Değişim (%)': '{:.2f}%',
            '24s Hacim': '${:,.0f}',
            'Piyasa Değeri': '${:,.0f}'
        }),
        use_container_width=True,
        height=400
    )
else:
    st.warning("Veriler yüklenemedi.")
