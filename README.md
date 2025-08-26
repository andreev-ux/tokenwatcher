# TokenWatcher

**TokenWatcher** is a lightweight Python service that monitors any Solana token:
- Detects **SWAP trades** via [Helius](https://helius.xyz) enhanced webhooks.  
- Correctly identifies **BUY** and **SELL** operations.  
- Sends formatted alerts to **Telegram**.  
- Tracks token price via [DexScreener](https://dexscreener.com) and notifies on significant changes.  
- Runs as a background service under **systemd** on Linux.  

---

## Features

- Monitors swaps involving your token mint.  
- BUY if token appears in `tokenOutputs`, SELL if in `tokenInputs`.  
- Trade alerts include amount and Solscan transaction link.  
- Price alerts based on percentage deviation from the last alert price.  
- Configurable thresholds via environment variables.  

---

## Installation

Clone repository and set up environment:

    git clone https://github.com/yourname/tokenwatcher.git
    cd tokenwatcher
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt

---

## Running under systemd

1. Copy the service file:

    sudo cp tokenwatcher.service /etc/systemd/system/

2. Reload and enable the service:

    sudo systemctl daemon-reload
    sudo systemctl enable tokenwatcher
    sudo systemctl start tokenwatcher

3. Check logs:

    journalctl -u tokenwatcher -f -a -o cat --no-pager

---

## Environment Variables

| Variable             | Description                                                                 | Default  |
|----------------------|-----------------------------------------------------------------------------|----------|
| TELEGRAM_BOT_TOKEN   | Telegram bot token obtained from [@BotFather](https://t.me/BotFather)        | –        |
| TELEGRAM_CHAT_ID     | Target chat or channel ID where notifications will be sent                  | –        |
| HELIUS_API_KEY       | API key for [Helius](https://helius.xyz)                                    | –        |
| TOKEN_MINT           | Mint address of your Solana token                                           | –        |
| TOKEN_DECIMALS       | Number of decimals for your token                                           | 9        |
| THRESHOLD            | Minimum trade amount (in tokens) to trigger a Telegram alert                | 30000    |
| PRICE_ALERT_PCT      | Percentage change from the last alert price to trigger a new price alert    | 5        |
| PRICE_POLL           | Price polling interval in seconds                                           | 60       |
| PYTHONUNBUFFERED     | Ensures logs are flushed immediately (recommended for systemd)              | 1        |

---

## Testing locally

Run the app manually:

    python tokenwatcher.py

Send a test webhook event:

    curl -X POST "http://localhost:8787/helius"       -H "Content-Type: application/json"       -d '[{"transaction":{"signature":"TESTSIG"},"events":{"swap":[{"tokenInputs":[{"mint":"YourSolanaTokenMintAddressHere","rawTokenAmount":{"tokenAmount":"1500000000000","decimals":9}}],"tokenOutputs":[{"mint":"EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v","rawTokenAmount":{"tokenAmount":"123000000","decimals":6}}]}]}}]'

You should see DBG lines in logs and a Telegram alert if thresholds are met.

---

## License

MIT License.  
Feel free to fork, modify and contribute.
