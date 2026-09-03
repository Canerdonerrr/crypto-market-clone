import asyncio
import logging
import random
import sqlite3
import sys
import time
import pandas as pd
import requests
from git import Repo, GitCommandError
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Konsol ve Log Yapılandırması
console = Console()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("CryptoBot")

USER_AGENTS = [
    "Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15"
]

class CryptoMarketBot:
    """CoinMarketCap verilerini çeken, analiz eden ve GitHub'a senkronize eden ana sınıf."""
    def __init__(self, limit=20, db_path="crypto_data.db", csv_path="crypto_snapshot.csv"):
        self.limit = limit
        self.api_url = f"https://api.coinmarketcap.com/data-api/v3/cryptocurrency/listing?start=1&limit={self.limit}&convert=USD"
        self.db_path = db_path
        self.csv_path = csv_path
        self._init_db()
        self._init_git()

    def _init_db(self):
        """SQLite veritabanı tablosunu hazırlar."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS crypto_market (
                    timestamp TEXT,
                    rank INTEGER,
                    name TEXT,
                    symbol TEXT,
                    price REAL,
                    percent_change_1h REAL,
                    percent_change_24h REAL,
                    percent_change_7d REAL,
                    market_cap REAL,
                    volume_24h REAL
                )
            ''')
            conn.commit()

    def _init_git(self):
        """Git deposunu bağlar."""
        try:
            self.repo = Repo(".")
        except Exception:
            self.repo = None
            logger.warning("Git deposu algılanamadı.")

    def fetch_data(self) -> list:
        """CMC API üzerinden canlı verileri çeker."""
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://coinmarketcap.com/"
        }
        
        for attempt in range(3):
            try:
                response = requests.get(self.api_url, headers=headers, timeout=15)
                if response.status_code == 429:
                    logger.warning("Rate-limit (429) algılandı, bekleniyor...")
                    time.sleep(5)
                    continue
                response.raise_for_status()
                data = response.json()
                
                crypto_list = data.get("data", {}).get("cryptoCurrencyList", [])
                parsed_data = []
                for coin in crypto_list:
                    quotes = coin.get("quotes", [{}])[0]
                    parsed_data.append({
                        "rank": coin.get("cmcRank"),
                        "name": coin.get("name"),
                        "symbol": coin.get("symbol"),
                        "price": quotes.get("price"),
                        "percent_change_1h": quotes.get("percentChange1h"),
                        "percent_change_24h": quotes.get("percentChange24h"),
                        "percent_change_7d": quotes.get("percentChange7d"),
                        "market_cap": quotes.get("marketCap"),
                        "volume_24h": quotes.get("volume24h"),
                    })
                return parsed_data
            except Exception as e:
                logger.error(f"Veri çekme hatası (Deneme {attempt+1}): {e}")
                time.sleep(3)
        return []

    def process_data(self, raw_data: list) -> pd.DataFrame:
        """Veriyi temizler, NaN değerleri güvenli hale getirir ve depoya kaydeder."""
        if not raw_data:
            return pd.DataFrame()

        df = pd.DataFrame(raw_data)
        timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
        df["timestamp"] = timestamp

        numeric_cols = ["rank", "price", "percent_change_1h", "percent_change_24h", "percent_change_7d", "market_cap", "volume_24h"]
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            
        # NaN değerlerin çökme yaratmaması için güvenli varsayılan değerler atama
        df.fillna({
            "rank": 0,
            "price": 0.0,
            "percent_change_1h": 0.0,
            "percent_change_24h": 0.0,
            "percent_change_7d": 0.0,
            "market_cap": 0.0,
            "volume_24h": 0.0,
            "name": "Unknown",
            "symbol": "UNK"
        }, inplace=True)

        df.dropna(subset=["symbol", "price"], inplace=True)

        # Yerel Depolama
        try:
            with sqlite3.connect(self.db_path) as conn:
                df.to_sql("crypto_market", conn, if_exists="append", index=False)
            df.to_csv(self.csv_path, index=False, encoding="utf-8")
        except Exception as e:
            logger.error(f"Depolama hatası: {e}")

        return df

    def sync_github(self, timestamp_str):
        """Dosyaları GitHub'a otomatik push eder."""
        if not self.repo:
            return
        try:
            self.repo.index.add([self.db_path, self.csv_path, "app.py"])
            if not self.repo.is_dirty(untracked_files=True):
                return
            self.repo.index.commit(f"Auto-update snapshot: {timestamp_str}")
            origin = self.repo.remote(name="origin")
            origin.push(refspec="main")
            logger.info("GitHub senkronizasyonu başarılı.")
        except Exception as e:
            logger.error(f"GitHub senkronizasyon hatası: {e}")

async def main():
    bot = CryptoMarketBot(limit=15)
    console.print(Panel.fit("[bold cyan]Crypto Market Termux Bot Aktif[/]", subtitle="Live CMC Data"))

    while True:
        try:
            console.print("\n[yellow][*] Canlı piyasa verileri çekiliyor...[/]")
            raw_data = bot.fetch_data()
            
            if raw_data:
                df = bot.process_data(raw_data)
                timestamp = df["timestamp"].iloc[0]

                # Tablo Oluştur
                table = Table(title=f"Kripto Para Piyasa Durumu ({timestamp})", show_lines=True)
                table.add_column("Sıra", justify="center", style="cyan")
                table.add_column("İsim", style="magenta")
                table.add_column("Sembol", style="green")
                table.add_column("Fiyat (USD)", justify="right", style="yellow")
                table.add_column("24s Değişim", justify="right")

                for _, row in df.head(10).iterrows():
                    change_val = row["percent_change_24h"]
                    color = "green" if change_val >= 0 else "red"
                    table.add_row(
                        str(int(row["rank"])),
                        str(row["name"]),
                        str(row["symbol"]),
                        f"${row['price']:,.2f}",
                        f"[{color}]{change_val:.2f}%[/]"
                    )
                console.print(table)

                # GitHub Sync
                bot.sync_github(timestamp)
            else:
                logger.warning("Veri alınamadı, tekrar denenecek.")

        except Exception as e:
            logger.error(f"Döngü hatası: {e}")

        console.print("[dim]15 dakika bekleniyor...[/]")
        await asyncio.sleep(900)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[bold red]Bot durduruldu.[/]")
