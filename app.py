import asyncio
import logging
import random
import sqlite3
import sys
import time
import pandas as pd
import requests
from git import Repo
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from telegram import Bot

TELEGRAM_TOKEN = "7526393717:AAGX5efyXkmIgC2LEM3c3VazzUBVa3YgMd4"
CHAT_ID = "1239624540"
telegram_bot = Bot(token=TELEGRAM_TOKEN) if TELEGRAM_TOKEN != "SENIN_BOT_TOKEN_BURAYA" else None

console = Console()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("CryptoBot")

USER_AGENTS = [
    "Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
]

class CryptoMarketBot:
    def __init__(self, limit=20, db_path="crypto_data.db", csv_path="crypto_snapshot.csv"):
        self.limit = limit
        self.api_url = f"https://api.coinmarketcap.com/data-api/v3/cryptocurrency/listing?start=1&limit={self.limit}&convert=USD"
        self.db_path = db_path
        self.csv_path = csv_path
        self._init_db()
        self._init_git()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS crypto_market (
                    timestamp TEXT, rank INTEGER, name TEXT, symbol TEXT,
                    price REAL, percent_change_1h REAL, percent_change_24h REAL,
                    percent_change_7d REAL, market_cap REAL, volume_24h REAL
                )
            ''')
            conn.commit()

    def _init_git(self):
        try:
            self.repo = Repo(".")
        except Exception:
            self.repo = None

    def fetch_data(self) -> list:
        headers = {"User-Agent": random.choice(USER_AGENTS), "Accept": "application/json"}
        for _ in range(3):
            try:
                res = requests.get(self.api_url, headers=headers, timeout=15)
                if res.status_code == 429:
                    time.sleep(5)
                    continue
                res.raise_for_status()
                crypto_list = res.json().get("data", {}).get("cryptoCurrencyList", [])
                parsed = []
                for coin in crypto_list:
                    q = coin.get("quotes", [{}])[0]
                    parsed.append({
                        "rank": coin.get("cmcRank"), "name": coin.get("name"),
                        "symbol": coin.get("symbol"), "price": q.get("price"),
                        "percent_change_1h": q.get("percentChange1h"),
                        "percent_change_24h": q.get("percentChange24h"),
                        "percent_change_7d": q.get("percentChange7d"),
                        "market_cap": q.get("marketCap"), "volume_24h": q.get("volume24h")
                    })
                return parsed
            except Exception as e:
                logger.error(f"Hata: {e}")
                time.sleep(3)
        return []

    def process_data(self, raw_data: list) -> pd.DataFrame:
        if not raw_data: return pd.DataFrame()
        df = pd.DataFrame(raw_data)
        timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
        df["timestamp"] = timestamp
        cols = ["rank", "price", "percent_change_1h", "percent_change_24h", "percent_change_7d", "market_cap", "volume_24h"]
        for c in cols: df[c] = pd.to_numeric(df[c], errors="coerce")
        df.fillna(0, inplace=True)
        df.dropna(subset=["symbol", "price"], inplace=True)
        try:
            with sqlite3.connect(self.db_path) as conn:
                df.to_sql("crypto_market", conn, if_exists="append", index=False)
            df.to_csv(self.csv_path, index=False, encoding="utf-8")
        except Exception as e:
            logger.error(f"DB Hatası: {e}")
        return df

    def sync_github(self, ts):
        if not self.repo: return
        try:
            self.repo.index.add([self.db_path, self.csv_path, "app.py"])
            if not self.repo.is_dirty(untracked_files=True): return
            self.repo.index.commit(f"Auto update: {ts}")
            self.repo.remote(name="origin").push(refspec="main")
            logger.info("GitHub sync başarılı.")
        except Exception as e:
            logger.error(f"Git hata: {e}")

async def send_telegram(df, ts):
    if not telegram_bot: return
    try:
        msg = f"📊 *Kripto Raporu* ({ts})\n\n"
        for _, row in df.head(5).iterrows():
            e = "🟢" if row["percent_change_24h"] >= 0 else "🔴"
            msg += f"{e} *{row['symbol']}*: ${row['price']:,.2f} ({row['percent_change_24h']:.2f}%)\n"
        await telegram_bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Telegram hata: {e}")

async def main():
    bot = CryptoMarketBot(limit=15)
    console.print(Panel.fit("[bold cyan]Crypto Bot Çalışıyor[/]"))
    while True:
        raw = bot.fetch_data()
        if raw:
            df = bot.process_data(raw)
            ts = df["timestamp"].iloc[0]
            
            table = Table(title=f"Piyasa Durumu ({ts})", show_lines=True)
            table.add_column("Sıra", style="cyan")
            table.add_column("İsim", style="magenta")
            table.add_column("Sembol", style="green")
            table.add_column("Fiyat", justify="right", style="yellow")
            table.add_column("24s Değişim", justify="right")
            
            for _, r in df.head(10).iterrows():
                col = "green" if r["percent_change_24h"] >= 0 else "red"
                table.add_row(str(int(r['rank'])), str(r['name']), str(r['symbol']), f"${r['price']:,.2f}", f"[{col}]{r['percent_change_24h']:.2f}%[/]")
            console.print(table)
            
            bot.sync_github(ts)
            await send_telegram(df, ts)
        await asyncio.sleep(900)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[red]Durduruldu.[/]")
