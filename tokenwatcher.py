import os
import asyncio
import aiohttp
from aiohttp import web
import time

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

TOKEN_MINT = os.getenv("TOKEN_MINT", "YourSolanaTokenMintAddressHere")
DECIMALS = {
    TOKEN_MINT: int(os.getenv("TOKEN_DECIMALS", "9")),
    "So11111111111111111111111111111111111111112": 9,
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB": 6,
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": 6,
}

LISTEN_PORT = 8787
WEBHOOK_PATH = "/helius"

THRESHOLD = int(os.getenv("THRESHOLD", "30000"))
PRICE_POLL = int(os.getenv("PRICE_POLL", "60"))
PRICE_ALERT_PCT = float(os.getenv("PRICE_ALERT_PCT", "5"))


def amount_ui(raw_amt: dict | str | float, mint: str) -> float:
    try:
        if isinstance(raw_amt, dict):
            val = float(raw_amt.get("tokenAmount") or 0)
            dec = raw_amt.get("decimals", DECIMALS.get(mint, 9))
        else:
            val = float(raw_amt or 0)
            dec = DECIMALS.get(mint, 9)
    except Exception:
        return 0.0
    return val / (10 ** int(dec))


async def tg_send(session, text: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        async with session.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": text}) as r:
            await r.text()
    except Exception as e:
        print("TG error:", e, flush=True)


def extract_sig(obj: dict) -> str:
    return obj.get("transaction", {}).get("signature", "")


def side_from_swap(tx: dict) -> tuple[float, str]:
    swaps = (tx.get("events") or {}).get("swap") or []
    token_in = token_out = 0.0
    for ev in swaps:
        for inp in ev.get("tokenInputs", []):
            if inp.get("mint") == TOKEN_MINT:
                token_out += amount_ui(inp.get("rawTokenAmount"), TOKEN_MINT)
        for out in ev.get("tokenOutputs", []):
            if out.get("mint") == TOKEN_MINT:
                token_in += amount_ui(out.get("rawTokenAmount"), TOKEN_MINT)
    if token_in > token_out:
        return token_in, "BUY"
    if token_out > token_in:
        return token_out, "SELL"
    return 0.0, ""


async def handle_helius(request: web.Request):
    app = request.app
    data = await request.json()
    session = app["session"]
    for obj in data:
        tx = obj.get("transaction", {})
        sig = extract_sig(obj)
        amount, side = side_from_swap(tx)
        print(f"DBG sig={sig} amount={amount:.2f} side={side} thr={THRESHOLD}", flush=True)
        if side and amount >= THRESHOLD:
            url = f"https://solscan.io/tx/{sig}"
            await tg_send(session, f"💸 {side} {amount:,.2f} TOKEN\n{url}")
    return web.Response(text="ok")


async def fetch_price(session) -> float:
    url = f"https://api.dexscreener.com/latest/dex/tokens/{TOKEN_MINT}"
    async with session.get(url) as r:
        js = await r.json()
    pairs = js.get("pairs") or []
    if not pairs:
        return 0.0
    return float(pairs[0].get("priceUsd") or 0)


async def price_loop(app: web.Application):
    session = app["session"]
    last_alert_price = None
    while True:
        try:
            p = await fetch_price(session)
            if p > 0:
                if last_alert_price is None:
                    last_alert_price = p
                else:
                    change = (p - last_alert_price) / last_alert_price * 100
                    if abs(change) >= PRICE_ALERT_PCT:
                        print(f"DBG price_alert p={p:.6f} change={change:+.2f}% thr={PRICE_ALERT_PCT}", flush=True)
                        await tg_send(session, f"📈 Price {p:.4f}$ ({change:+.2f}%)")
                        last_alert_price = p
        except Exception as e:
            print("price err", e, flush=True)
        await asyncio.sleep(PRICE_POLL)


async def on_start(app: web.Application):
    app["session"] = aiohttp.ClientSession()
    app["price_task"] = asyncio.create_task(price_loop(app))
    await tg_send(app["session"], "✅ TokenWatcher started")


async def on_stop(app: web.Application):
    await app["session"].close()


def main():
    app = web.Application()
    app.router.add_post(WEBHOOK_PATH, handle_helius)
    app.on_startup.append(on_start)
    app.on_cleanup.append(on_stop)
    web.run_app(app, port=LISTEN_PORT)


if __name__ == "__main__":
    main()
