import sqlite3
import pandas as pd
from flask import Flask, render_template

app = Flask(__name__)

def get_latest_macro():
    try:
        with sqlite3.connect("crypto_data.db") as conn:
            df = pd.read_sql("SELECT * FROM jr_macro_metrics ORDER BY timestamp DESC LIMIT 1", conn)
            if not df.empty:
                return df.iloc[0].to_dict()
    except Exception:
        pass
    return {
        "btc_dominance": 59.76,
        "eth_dominance": 11.21,
        "fear_greed_index": 75,
        "liquidations": 164284783
    }

@app.route("/")
def index():
    try:
        df = pd.read_csv("crypto_snapshot.csv")
        data = df.to_dict(orient="records")
        timestamp = df["timestamp"].iloc[0] if not df.empty else "Bilinmiyor"
    except Exception:
        data = []
        timestamp = "Veri Bekleniyor..."
    
    macro = get_latest_macro()
    return render_template("index.html", data=data, timestamp=timestamp, macro=macro)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
