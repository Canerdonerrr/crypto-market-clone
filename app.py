import streamlit as st
import pandas as pd
import requests
from requests.exceptions import RequestException, Timeout, ConnectionError, HTTPError

st.set_page_config(
    page_title="CryptoTerminal Pro",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CUSTOM CSS: Dark Terminal Theme ---
st.markdown("""
<style>
    .stApp {
        background-color: #0e1117;
        color: #e0e0e0;
    }
    [data-testid="stMetric"] {
        background-color: #1a1f2e;
        padding: 15px 20px;
        border-radius: 10px;
        border: 1px solid #2a3142;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    }
    [data-testid="stMetricLabel"] {
        color: #8b9bb4 !important;
        font-size: 0.85rem !important;
    }
    [data-testid="stMetricValue"] {
        color: #00d4aa !important;
        font-weight: 600 !important;
    }
    h1, h2, h3 {
        color: #00d4aa !important;
    }
    .stDataFrame {
        border: 1px solid #2a3142;
        border-radius: 8px;
    }
    .stButton > button {
        background-color: #00d4aa;
        color: #0e1117;
        border: none;
        border-radius: 6px;
        font-weight: 600;
        transition: all 0.2s;
    }
    .stButton > button:hover {
        background-color: #00b894;
        transform: translateY(-1px);
    }
    .stAlert {
        background-color: #1a1f2e;
        border: 1px solid #2a3142;
        border-radius: 8px;
    }
    hr {
        border-color: #2a3142 !important;
    }
    .stTextInput > div > div > input, .stSelectbox > div > div > div {
        background-color: #1a1f2e;
        color: #e0e0e0;
        border: 1px solid #2a3142;
    }
</style>
""", unsafe_allow_html=True)

# --- SESSION STATE ---
if "page" not in st.session_state:
    st.session_state.page = "market"
if "selected_coin_id" not in st.session_state:
    st.session_state.selected_coin_id = "bitcoin"
if "portfolio" not in st.session_state:
    st.session_state.portfolio = []

# --- API FONKSİYONLARI ---
@st.cache_data(ttl=60, show_spinner=False)
def load_global_data():
    try:
        res = requests.get("https://api.coingecko.com/api/v3/global", timeout=12)
        res.raise_for_status()
        return res.json().get("data", {})
    except Exception:
        return None

@st.cache_data(ttl=300, show_spinner=False)
def load_fear_greed():
    try:
        res = requests.get("https://api.alternative.me/fng/", timeout=10)
        res.raise_for_status()
        data = res.json().get("data", [{}])[0]
        return data.get("value"), data.get("value_classification", "Bilinmiyor")
    except Exception:
        return None, "Bilinmiyor"

@st.cache_data(ttl=60, show_spinner=False)
def load_trending_data():
    try:
        res = requests.get("https://api.coingecko.com/api/v3/search/trending", timeout=12)
        res.raise_for_status()
        return res.json().get("coins", [])
    except Exception:
        return []

@st.cache_data(ttl=60, show_spinner=False)
def load_crypto_list(vs_currency="usd", per_page=100):
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": vs_currency,
        "order": "market_cap_desc",
        "per_page": per_page,
        "page": 1,
        "sparkline": "true",
        "price_change_percentage": "1h,24h,7d"
    }
    try:
        res = requests.get(url, params=params, timeout=15)
        res.raise_for_status()
        return res.json()
    except Exception:
        return []

@st.cache_data(ttl=120, show_spinner=False)
def load_coin_detail(coin_id: str):
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
    params = {
        "localization": "false",
        "tickers": "true",
        "market_data": "true",
        "community_data": "false",
        "developer_data": "false"
    }
    try:
        res = requests.get(url, params=params, timeout=12)
        res.raise_for_status()
        return res.json()
    except Exception:
        return None

# --- YARDIMCI FORMATLAYICILAR ---
CURRENCY_SYMBOLS = {"usd": "$", "try": "₺", "eur": "€"}

def format_price(price, cur_symbol="$"):
    if price is None:
        return "—"
    if price < 0.0001:
        return f"{cur_symbol}{price:.8f}"
    if price < 1:
        return f"{cur_symbol}{price:.4f}"
    if price < 100:
        return f"{cur_symbol}{price:,.2f}"
    return f"{cur_symbol}{price:,.0f}"

def format_number(num, cur_symbol="$"):
    if num is None:
        return "—"
    if num >= 1_000_000_000:
        return f"{cur_symbol}{num/1_000_000_000:.2f}B"
    if num >= 1_000_000:
        return f"{cur_symbol}{num/1_000_000:.2f}M"
    return f"{cur_symbol}{num:,.0f}"

def get_best_tradingview_symbol(details: dict, symbol: str) -> str:
    try:
        tickers = details.get("tickers", []) or []
        for t in tickers:
            market = t.get("market", {}).get("name", "").lower()
            target = t.get("target", "").upper()
            base = t.get("base", "").upper()
            if "binance" in market and target == "USDT" and base == symbol.upper():
                return f"BINANCE:{symbol.upper()}USDT"
        for t in tickers:
            target = t.get("target", "").upper()
            base = t.get("base", "").upper()
            if target == "USDT" and base == symbol.upper():
                exchange = t.get("market", {}).get("identifier", "BINANCE").upper()
                return f"{exchange}:{symbol.upper()}USDT"
    except Exception:
        pass
    return f"BINANCE:{symbol.upper()}USDT"

# ==========================================
# ÜST KONTROL BARİ (Para Birimi Seçimi & Sayfa)
# ==========================================
top_col1, top_col2, top_col3 = st.columns([3, 2, 2])
with top_col1:
    st.title("🚀 CryptoTerminal Pro")
with top_col2:
    currency_choice = st.selectbox("💱 Para Birimi", ["usd", "try", "eur"], format_func=lambda x: x.upper(), label_visibility="collapsed")
with top_col3:
    nav_mode = st.radio("Menü", ["Piyasa & Terminal", "Sanal Portföyüm"], horizontal=True, label_visibility="collapsed")

cur_sym = CURRENCY_SYMBOLS.get(currency_choice, "$")
st.markdown("---")

# ==========================================
# SAYFA A: SANAL PORTFÖY YÖNETİMİ
# ==========================================
if nav_mode == "Sanal Portföyüm":
    st.subheader("💼 Sanal Portföy ve Kâr/Zarar Takibi")
    st.caption("Cüzdanınıza varlık ekleyin, anlık piyasa fiyatlarıyla toplam değerinizi ve kâr/zarar durumunuzu takip edin.")

    with st.form("portfolio_form"):
        p_col1, p_col2, p_col3 = st.columns(3)
        with p_col1:
            add_coin_symbol = st.text_input("Coin Sembolü (Örn: BTC, ETH, SOL)").upper()
        with p_col2:
            add_amount = st.number_input("Adet / Miktar", min_value=0.000001, value=1.0, step=0.1)
        with p_col3:
            add_buy_price = st.number_input(f"Ortalama Alış Fiyatı ({cur_sym})", min_value=0.0, value=100.0, step=1.0)
        
        submitted = st.form_submit_button("➕ Portföye Varlık Ekle")
        if submitted and add_coin_symbol:
            st.session_state.portfolio.append({
                "symbol": add_coin_symbol,
                "amount": add_amount,
                "buy_price": add_buy_price
            })
            st.success(f"{add_coin_symbol} portföye başarıyla eklendi!")

    if st.session_state.portfolio:
        st.markdown("### 📊 Portföy Varlık Özeti")
        live_coins = load_crypto_list(vs_currency=currency_choice, per_page=100)
        price_map = {c['symbol'].upper(): c['current_price'] for c in live_coins}

        p_rows = []
        total_portfolio_value = 0
        total_portfolio_cost = 0

        for idx, item in enumerate(st.session_state.portfolio):
            sym = item['symbol']
            amt = item['amount']
            b_price = item['buy_price']
            curr_price = price_map.get(sym, b_price)

            current_val = amt * curr_price
            cost_val = amt * b_price
            p_l = current_val - cost_val
            p_l_pct = (p_l / cost_val * 100) if cost_val > 0 else 0

            total_portfolio_value += current_val
            total_portfolio_cost += cost_val

            p_rows.append({
                "ID": idx,
                "Sembol": sym,
                "Adet": amt,
                "Alış Fiyatı": format_price(b_price, cur_sym),
                "Anlık Fiyat": format_price(curr_price, cur_sym),
                "Toplam Maliyet": format_number(cost_val, cur_sym),
                "Güncel Değer": format_number(current_val, cur_sym),
                "Kâr / Zarar": f"{format_number(p_l, cur_sym)} (%{p_l_pct:+.2f})"
            })

        st.dataframe(pd.DataFrame(p_rows).drop(columns=["ID"]), hide_index=True, use_container_width=True)

        tot_pl = total_portfolio_value - total_portfolio_cost
        tot_pl_pct = (tot_pl / total_portfolio_cost * 100) if total_portfolio_cost > 0 else 0

        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("Toplam Portföy Değeri", format_number(total_portfolio_value, cur_sym))
        mc2.metric("Toplam Maliyet", format_number(total_portfolio_cost, cur_sym))
        mc3.metric("Net Kâr / Zarar", format_number(tot_pl, cur_sym), f"%{tot_pl_pct:+.2f}")

        if st.button("🗑️ Portföyü Sıfırla / Temizle"):
            st.session_state.portfolio = []
            st.rerun()
    else:
        st.info("Portföyünüzde henüz varlık yok. Yukarıdaki formdan ekleme yapabilirsiniz.")

# ==========================================
# SAYFA B: ANA PİYASA & DETAY TERMİNALİ
# ==========================================
else:
    if st.session_state.page == "market":
        # --- Üst Metrikler ---
        global_data = load_global_data()
        fng_val, fng_class = load_fear_greed()

        if global_data:
            btc_dom = global_data.get("market_cap_percentage", {}).get("btc", 0)
            total_mcap = global_data.get("total_market_cap", {}).get(currency_choice, 0)
            total_vol = global_data.get("total_volume", {}).get(currency_choice, 0)
            mcap_change = global_data.get("market_cap_change_percentage_24h_usd", 0)

            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("🌍 Küresel Piyasa Değeri", format_number(total_mcap, cur_sym), f"{mcap_change:+.2f}%" if mcap_change else None)
            c2.metric("📊 24s Toplam Hacim", format_number(total_vol, cur_sym))
            c3.metric("👑 BTC Dominansı", f"%{btc_dom:.2f}")
            c4.metric("🧠 Korku & Açgözlülük", f"{fng_val}" if fng_val else "—", fng_class if fng_val else None)
            c5.metric("🪙 Aktif Kripto", f"{global_data.get('active_cryptocurrencies', 0):,}")

        st.markdown("---")

        # --- Trend Kartları ---
        trending_coins = load_trending_data()
        if trending_coins:
            st.subheader("🔥 Anlık Trend Olan Varlıklar")
            t_cols = st.columns(min(5, len(trending_coins)))
            for idx, item in enumerate(trending_coins[:5]):
                coin = item.get("item", {})
                with t_cols[idx]:
                    st.info(f"**{coin.get('name', '—')}**\n\n`{coin.get('symbol', '').upper()}`\n\nSıra: #{coin.get('market_cap_rank', 'N/A')}")
            st.markdown("---")

        # --- Piyasa Tablosu ---
        coins_data = load_crypto_list(vs_currency=currency_choice, per_page=100)
        if coins_data:
            search_query = st.text_input("🔍 Hızlı Ara (isim veya sembol)", placeholder="Örn: bitcoin, eth, sol...", label_visibility="collapsed")

            rows = []
            for coin in coins_data:
                name = coin.get("name", "")
                symbol = coin.get("symbol", "").upper()
                if search_query:
                    q = search_query.lower()
                    if q not in name.lower() and q not in symbol.lower():
                        continue

                spark = coin.get("sparkline_in_7d", {}).get("price", [])
                if spark and len(spark) > 8:
                    step = len(spark) // 8
                    spark = spark[::step][:8]

                rows.append({
                    "Sıra": coin.get("market_cap_rank"),
                    "Varlık": name,
                    "Sembol": symbol,
                    "Fiyat": coin.get("current_price"),
                    "1s %": coin.get("price_change_percentage_1h_in_currency"),
                    "24s %": coin.get("price_change_percentage_24h"),
                    "7g %": coin.get("price_change_percentage_7d_in_currency"),
                    "Piyasa Değeri": coin.get("market_cap"),
                    "Hacim (24s)": coin.get("total_volume"),
                    "7g Sparkline": spark if spark else None,
                    "_id": coin.get("id"),
                })

            if not rows:
                st.warning("Arama sonucu bulunamadı.")
            else:
                df = pd.DataFrame(rows)
                column_config = {
                    "Sıra": st.column_config.NumberColumn("Sıra", width="small", format="%d"),
                    "Varlık": st.column_config.TextColumn("Varlık", width="medium"),
                    "Sembol": st.column_config.TextColumn("Sembol", width="small"),
                    "Fiyat": st.column_config.NumberColumn(f"Fiyat ({cur_sym})", format=f"{cur_sym}%.4f", width="small"),
                    "1s %": st.column_config.NumberColumn("1s %", format="%.2f%%", width="small"),
                    "24s %": st.column_config.NumberColumn("24s %", format="%.2f%%", width="small"),
                    "7g %": st.column_config.NumberColumn("7g %", format="%.2f%%", width="small"),
                    "Piyasa Değeri": st.column_config.NumberColumn("Piyasa Değeri", format=f"{cur_sym}%.0f", width="medium"),
                    "Hacim (24s)": st.column_config.NumberColumn("Hacim 24s", format=f"{cur_sym}%.0f", width="medium"),
                    "7g Sparkline": st.column_config.LineChartColumn("7 Günlük Trend", width="medium"),
                    "_id": None,
                }

                st.markdown("### 📋 Piyasa Varlık Tablosu")
                st.caption("Bir satıra tıklayarak detay sayfasına gidebilirsiniz • 100 varlık listeleniyor")

                selection = st.dataframe(
                    df,
                    column_config=column_config,
                    hide_index=True,
                    use_container_width=True,
                    height=520,
                    on_select="rerun",
                    selection_mode="single-row",
                    key="market_table"
                )

                if selection and selection.selection and selection.selection.rows:
                    selected_idx = selection.selection.rows[0]
                    selected_id = df.iloc[selected_idx]["_id"]
                    st.session_state.selected_coin_id = selected_id
                    st.session_state.page = "detail"
                    st.rerun()
        else:
            st.error("Piyasa verileri yüklenemedi. Lütfen daha sonra tekrar deneyin.")

    # ==========================================
    # SAYFA DETAY + TRADINGVIEW
    # ==========================================
    elif st.session_state.page == "detail":
        if st.button("⬅️ Ana Piyasa Terminaline Dön"):
            st.session_state.page = "market"
            st.rerun()

        details = load_coin_detail(st.session_state.selected_coin_id)
        if details:
            market_data = details.get("market_data", {}) or {}
            coin_name = details.get("name", "—")
            coin_symbol = details.get("symbol", "").upper()
            image_url = details.get("image", {}).get("small")

            header_cols = st.columns([0.08, 0.92])
            if image_url:
                header_cols[0].image(image_url, width=48)
            header_cols[1].title(f"{coin_name} ({coin_symbol})")

            current_price = market_data.get("current_price", {}).get(currency_choice)
            rank = market_data.get("market_cap_rank")
            high_24 = market_data.get("high_24h", {}).get(currency_choice)
            low_24 = market_data.get("low_24h", {}).get(currency_choice)
            change_24 = market_data.get("price_change_percentage_24h")

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Anlık Fiyat", format_price(current_price, cur_sym), f"{change_24:+.2f}%" if change_24 is not None else None)
            c2.metric("Piyasa Sıralaması", f"#{rank}" if rank else "—")
            c3.metric("24s En Yüksek / Düşük", f"{format_price(high_24, cur_sym)} / {format_price(low_24, cur_sym)}")
            c4.metric("24s Değişim", f"%{change_24:.2f}" if change_24 is not None else "—")

            st.markdown("---")

            col_d1, col_d2, col_d3 = st.columns(3)
            with col_d1:
                st.markdown("### 📊 Arz & Değerleme")
                mcap = market_data.get("market_cap", {}).get(currency_choice)
                fdv = market_data.get("fully_diluted_valuation", {}).get(currency_choice)
                circ = market_data.get("circulating_supply")
                max_s = market_data.get("max_supply")
                
                st.markdown(f"- **Piyasa Değeri:** `{format_number(mcap, cur_sym)}`")
                st.markdown(f"- **FDV:** `{format_number(fdv, cur_sym)}`")
                st.markdown(f"- **Dolaşımdaki Arz:** `{circ:,.0f} {coin_symbol}`" if circ else "- **Dolaşımdaki Arz:** —")
                st.markdown(f"- **Maksimum Arz:** `{max_s:,.0f}`" if max_s else "- **Maksimum Arz:** `Sınırsız`")

            with col_d2:
                st.markdown("### 🏆 Tarihsel Rekorlar")
                ath = market_data.get("ath", {}).get(currency_choice)
                ath_change = market_data.get("ath_change_percentage", {}).get(currency_choice)
                atl = market_data.get("atl", {}).get(currency_choice)
                
                st.markdown(f"- **ATH:** `{format_price(ath, cur_sym)}`")
                if ath_change is not None:
                    st.markdown(f"- **ATH'den Değişim:** `%{ath_change:.1f}`")
                st.markdown(f"- **ATL:** `{format_price(atl, cur_sym)}`")

            with col_d3:
                st.markdown("### 📈 Performans")
                ch_7d = market_data.get("price_change_percentage_7d")
                ch_30d = market_data.get("price_change_percentage_30d")
                ch_1y = market_data.get("price_change_percentage_1y")

                st.markdown(f"- **7 Günlük:** `%{ch_7d:.2f}`" if ch_7d is not None else "- **7 Günlük:** —")
                st.markdown(f"- **30 Günlük:** `%{ch_30d:.2f}`" if ch_30d is not None else "- **30 Günlük:** —")
                st.markdown(f"- **1 Yıllık:** `%{ch_1y:.2f}`" if ch_1y is not None else "- **1 Yıllık:** —")

            st.markdown("---")
            st.markdown(f"### 📉 {coin_symbol} Profesyonel Canlı Grafik")
            tv_symbol = get_best_tradingview_symbol(details, coin_symbol)

            tradingview_html = f"""
            <div class="tradingview-widget-container" style="height:560px;width:100%;border-radius:8px;overflow:hidden;">
              <div id="tradingview_chart" style="height:100%;width:100%"></div>
              <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
              <script type="text/javascript">
              new TradingView.widget({{
                "autosize": true,
                "symbol": "{tv_symbol}",
                "interval": "D",
                "timezone": "Europe/Istanbul",
                "theme": "dark",
                "style": "1",
                "locale": "tr",
                "toolbar_bg": "#1a1f2e",
                "enable_publishing": false,
                "allow_symbol_change": true,
                "container_id": "tradingview_chart"
              }});
              </script>
            </div>
            """
            st.components.v1.html(tradingview_html, height=570)
        else:
            st.error("Detay bilgileri yüklenemedi.")
