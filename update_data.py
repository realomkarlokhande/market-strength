"""Builds data.json: Nifty 500 relative-strength ratings from daily prices.
Run: pip install yfinance pandas requests && python scripts/update_data.py
"""
import io, json, datetime as dt
import pandas as pd, requests, yfinance as yf

URL = "https://niftyindices.com/IndexConstituent/ind_nifty500list.csv"
meta = pd.read_csv(io.StringIO(requests.get(URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=30).text))
meta["t"] = meta["Symbol"].str.strip() + ".NS"

px = yf.download(list(meta.t), period="15mo", auto_adjust=True, progress=False, threads=True)
close, volume = px["Close"], px["Volume"]

rows = []
for _, m in meta.iterrows():
    t = m.t
    if t not in close.columns:
        continue
    c = close[t].dropna()
    if len(c) < 253:
        continue
    ret = lambda n: c.iloc[-1] / c.iloc[-1 - n] - 1
    v = volume[t].dropna()
    vr = float(v.iloc[-1] / v.iloc[-51:-1].mean()) if len(v) > 51 and v.iloc[-51:-1].mean() > 0 else 1.0
    rows.append({
        "s": m["Symbol"].strip(), "n": m["Company Name"], "sec": m["Industry"],
        "score": 0.4 * ret(63) + 0.2 * ret(126) + 0.2 * ret(189) + 0.2 * ret(252),
        "r3": round(ret(63) * 100, 1), "r6": round(ret(126) * 100, 1), "r12": round(ret(252) * 100, 1),
        "hi": round((c.iloc[-1] / c.iloc[-252:].max() - 1) * 100, 1),
        "vol": round(vr, 1), "p": round(float(c.iloc[-1]), 2),
        "c": [round(float(x), 2) for x in c.iloc[-120:]],
    })

df = pd.DataFrame(rows)
df["rs"] = (df["score"].rank(pct=True) * 98 + 1).round().astype(int)
out = df.drop(columns="score").to_dict("records")
json.dump({"updated": dt.date.today().isoformat(), "sample": False, "stocks": out},
          open("data.json", "w"), separators=(",", ":"))
print(f"Wrote {len(out)} stocks")
