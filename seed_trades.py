"""
Seed script to import trades from external API format into TradeFlow.
Usage: python seed_trades.py
"""
import requests
from datetime import datetime, timezone

# ── Config ────────────────────────────────────────────────────────────────────
API_BASE = "http://localhost:8000/api"
EMAIL    = "isamazasylvin@gmail.com"
PASSWORD = "Test@123"
ACCOUNT_ID = "acc_demo_1e4664a8"
# ─────────────────────────────────────────────────────────────────────────────

RAW_TRADES = [
    {"id":63017621,"direction":1,"profit":"7.17","volume":"0.0100","symbol":"XAUUSD.x","commission":"0.00","swap":"0.00","tp":"4675.4400","sl":"4664.3200","open_time":"2026-05-11T12:14:18Z","open_price":"4668.2400000","close_time":"2026-05-11T12:20:46Z","close_price":"4675.4100000"},
    {"id":62464834,"direction":2,"profit":"19.35","volume":"0.0100","symbol":"XAUUSD.x","commission":"0.00","swap":"0.00","tp":"4706.8900","sl":"0.0000","open_time":"2026-05-07T16:03:48Z","open_price":"4726.2300000","close_time":"2026-05-07T16:19:03Z","close_price":"4706.8800000"},
    {"id":62464833,"direction":2,"profit":"16.84","volume":"0.0100","symbol":"XAUUSD.x","commission":"0.00","swap":"0.00","tp":"4709.8100","sl":"0.0000","open_time":"2026-05-07T16:03:47Z","open_price":"4726.1700000","close_time":"2026-05-07T16:18:18Z","close_price":"4709.3300000"},
    {"id":61258889,"direction":1,"profit":"12.56","volume":"0.0400","symbol":"XAUUSD.x","commission":"0.00","swap":"0.00","tp":"4538.3700","sl":"0.0000","open_time":"2026-05-04T16:04:59Z","open_price":"4522.4200000","close_time":"2026-05-04T16:21:23Z","close_price":"4525.5600000"},
    {"id":61258887,"direction":1,"profit":"29.20","volume":"0.1000","symbol":"XAUUSD.x","commission":"0.00","swap":"0.00","tp":"4538.4300","sl":"0.0000","open_time":"2026-05-04T16:04:54Z","open_price":"4522.6400000","close_time":"2026-05-04T16:21:23Z","close_price":"4525.5600000"},
    {"id":61096151,"direction":1,"profit":"102.28","volume":"0.0400","symbol":"XAUUSD.x","commission":"0.00","swap":"0.00","tp":"4581.0200","sl":"4559.5400","open_time":"2026-05-04T10:24:25Z","open_price":"4533.6100000","close_time":"2026-05-04T11:30:50Z","close_price":"4559.1800000"},
    {"id":61148868,"direction":2,"profit":"-7.60","volume":"0.1000","symbol":"XAUUSD.x","commission":"0.00","swap":"0.00","tp":"0.0000","sl":"0.0000","open_time":"2026-05-04T08:45:26Z","open_price":"4577.3800000","close_time":"2026-05-04T08:50:37Z","close_price":"4578.1400000"},
    {"id":61148800,"direction":2,"profit":"-59.30","volume":"0.1000","symbol":"XAUUSD.x","commission":"0.00","swap":"0.00","tp":"4561.6900","sl":"0.0000","open_time":"2026-05-04T08:30:09Z","open_price":"4574.5100000","close_time":"2026-05-04T08:40:41Z","close_price":"4580.4400000"},
    {"id":61053364,"direction":1,"profit":"56.15","volume":"0.1000","symbol":"GBPJPY.x","commission":"0.00","swap":"0.00","tp":"213.5830","sl":"212.1310","open_time":"2026-05-04T03:55:47Z","open_price":"4522.6400000","close_time":"2026-05-04T05:21:23Z","close_price":"213.0030000"},
    {"id":61050652,"direction":1,"profit":"-32.39","volume":"0.0200","symbol":"XAUUSD.x","commission":"0.00","swap":"0.00","tp":"4649.2500","sl":"4580.1700","open_time":"2026-05-04T03:43:39Z","open_price":"4602.9300000","close_time":"2026-05-04T07:59:44Z","close_price":"4586.7350000"},
    # --- batch 2 ---
    {"id":60748294,"direction":1,"profit":"54.71","volume":"0.0100","symbol":"XAUUSD.x","commission":"0.00","swap":"0.00","tp":"4630.8600","sl":"4556.6700","open_time":"2026-05-01T08:50:30Z","open_price":"4569.7500000","close_time":"2026-05-01T13:59:55Z","close_price":"4624.4600000"},
    {"id":60735268,"direction":1,"profit":"57.61","volume":"1.1000","symbol":"GBPJPY.x","commission":"0.00","swap":"0.00","tp":"0.0000","sl":"0.0000","open_time":"2026-05-01T07:08:53Z","open_price":"212.9610000","close_time":"2026-05-01T07:08:57Z","close_price":"213.0430000"},
    {"id":60735244,"direction":1,"profit":"43.62","volume":"1.1000","symbol":"GBPJPY.x","commission":"0.00","swap":"0.00","tp":"0.0000","sl":"0.0000","open_time":"2026-05-01T07:07:31Z","open_price":"212.6910000","close_time":"2026-05-01T07:08:33Z","close_price":"212.7530000"},
    {"id":60735084,"direction":1,"profit":"34.07","volume":"0.1000","symbol":"GBPJPY.x","commission":"0.00","swap":"0.00","tp":"213.1710","sl":"0.0000","open_time":"2026-05-01T06:56:20Z","open_price":"212.0550000","close_time":"2026-05-01T07:07:04Z","close_price":"212.5870000"},
    {"id":60698789,"direction":2,"profit":"-3.80","volume":"0.1000","symbol":"NZDUSD.x","commission":"0.00","swap":"0.00","tp":"0.5823","sl":"0.5929","open_time":"2026-05-01T05:17:59Z","open_price":"0.5892600","close_time":"2026-05-01T07:09:25Z","close_price":"0.5896400"},
    {"id":60652428,"direction":1,"profit":"-43.37","volume":"0.1000","symbol":"GBPJPY.x","commission":"0.00","swap":"0.77","tp":"214.7610","sl":"212.3720","open_time":"2026-04-30T20:12:30Z","open_price":"213.0290000","close_time":"2026-05-01T06:47:22Z","close_price":"212.3520000"},
    {"id":60578850,"direction":1,"profit":"100.38","volume":"0.1000","symbol":"GBPJPY.x","commission":"0.00","swap":"0.00","tp":"215.2140","sl":"209.8880","open_time":"2026-04-30T12:17:37Z","open_price":"211.4300000","close_time":"2026-04-30T15:04:10Z","close_price":"213.0040000"},
    {"id":60555001,"direction":1,"profit":"-14.96","volume":"0.0100","symbol":"XAUUSD.x","commission":"0.00","swap":"0.00","tp":"4678.9000","sl":"4605.2400","open_time":"2026-04-30T10:17:51Z","open_price":"4630.7500000","close_time":"2026-04-30T15:04:10Z","close_price":"4615.7900000"},
    {"id":60270449,"direction":1,"profit":"43.94","volume":"0.0100","symbol":"XAUUSD.x","commission":"0.00","swap":"-1.96","tp":"4596.5600","sl":"4508.7200","open_time":"2026-04-29T15:05:38Z","open_price":"4543.9700000","close_time":"2026-04-30T07:17:34Z","close_price":"4587.9100000"},
    {"id":60031908,"direction":1,"profit":"-51.27","volume":"0.0100","symbol":"XAUUSD.x","commission":"0.00","swap":"-0.65","tp":"4694.7300","sl":"4547.7800","open_time":"2026-04-28T20:10:31Z","open_price":"4598.6700000","close_time":"2026-04-29T12:53:02Z","close_price":"4547.4000000"},
    # --- batch 3 ---
    {"id":59254795,"direction":1,"profit":"46.31","volume":"0.0100","symbol":"XAUUSD.x","commission":"0.00","swap":"0.00","tp":"4736.8300","sl":"4653.0000","open_time":"2026-04-24T07:47:29Z","open_price":"4689.9300000","close_time":"2026-04-24T14:12:17Z","close_price":"4736.2400000"},
    {"id":59254772,"direction":1,"profit":"41.65","volume":"0.0100","symbol":"XAUUSD.x","commission":"0.00","swap":"0.00","tp":"4770.4200","sl":"4690.9500","open_time":"2026-04-24T07:46:31Z","open_price":"4690.5300000","close_time":"2026-04-24T14:20:35Z","close_price":"4732.1800000"},
    {"id":50346495,"direction":1,"profit":"-34.49","volume":"0.0100","symbol":"XAUUSD.x","commission":"0.00","swap":"0.00","tp":"4509.3800","sl":"4413.0400","open_time":"2026-03-27T08:15:01Z","open_price":"4447.2900000","close_time":"2026-03-27T10:43:26Z","close_price":"4412.8000000"},
]


def get_token() -> str:
    resp = requests.post(f"{API_BASE}/auth/login", json={"email": EMAIL, "password": PASSWORD})
    resp.raise_for_status()
    return resp.json()["access_token"]


def calc_duration(open_time: str, close_time: str) -> str:
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    delta = datetime.strptime(close_time, fmt) - datetime.strptime(open_time, fmt)
    total = int(delta.total_seconds())
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h {m}m"
    return f"{m}m {s}s"


def calc_status(pnl: float) -> str:
    if pnl > 0:
        return "WIN"
    if pnl < 0:
        return "LOSS"
    return "BE"


def transform(t: dict) -> dict:
    pnl        = float(t["profit"])
    open_dt    = datetime.strptime(t["open_time"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    close_dt   = datetime.strptime(t["close_time"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    sl         = float(t["sl"])
    tp         = float(t["tp"])

    return {
        "account_id":    ACCOUNT_ID,
        "symbol":        t["symbol"].replace(".x", ""),  # strip broker suffix
        "side":          "LONG" if t["direction"] == 1 else "SHORT",
        "entry_price":   float(t["open_price"]),
        "exit_price":    float(t["close_price"]),
        "close_price":   float(t["close_price"]),
        "quantity":      float(t["volume"]),
        "pnl":           pnl,
        "commission":    float(t["commission"]),
        "swap":          float(t["swap"]),
        "duration":      calc_duration(t["open_time"], t["close_time"]),
        "trade_type":    "Day Trade",
        "execution_type":"Market",
        "status":        calc_status(pnl),
        "stop_loss":     sl if sl != 0 else None,
        "take_profit":   tp if tp != 0 else None,
        "setups":        [],
        "general_tags":  [],
        "exit_tags":     [],
        "process_tags":  [],
        "executed_at":   open_dt.isoformat(),
        "closed_at":     close_dt.isoformat(),
        "date":          open_dt.date().isoformat(),
        "time":          open_dt.strftime("%H:%M"),
        "close_time":    close_dt.strftime("%H:%M"),
    }


def main():
    token   = get_token()
    headers = {"Authorization": f"Bearer {token}"}

    ok = err = 0
    for t in RAW_TRADES:
        payload = transform(t)
        resp = requests.post(f"{API_BASE}/trades/", json=payload, headers=headers)
        if resp.status_code == 201:
            print(f"✓ {payload['symbol']} {payload['side']} {payload['date']}  PnL={payload['pnl']}")
            ok += 1
        else:
            print(f"✗ id={t['id']}  {resp.status_code}: {resp.text}")
            err += 1

    print(f"\nDone — {ok} created, {err} failed")


if __name__ == "__main__":
    main()
