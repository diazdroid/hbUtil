# OwO HuntBot Auto-Upgrader (hbUtil)

An intelligent, lightweight, and fully automated script to mathematically optimize and upgrade your OwO Discord Bot's `HuntBot` traits.

## 🚀 Features

- **Mathematical ROI Solver**: Instead of blindly spending your hard-earned Animal Essence on random levels, this script uses a "Cheapest Next" algorithm. It compares the upcoming costs of all core traits and buys the cheapest one, guaranteeing your essence generation rate snowballs as fast as possible.
- **Bulk Execution (Anti-Spam)**: Simulates the entire spending loop in local memory. Instead of sending 50 small upgrade commands to Discord (which triggers API bans), it bundles the costs and sends exactly *one* command per trait (e.g., `owo upgrade efficiency 45200`).
- **Dynamic Trait Selection**: Choose exactly what you want to upgrade via command-line arguments. Want to focus purely on `gain` and `duration`? You can easily toggle them.
- **Rate-Limit & Slowmode Protection**: Built-in detection for Discord's `429 Too Many Requests` and OwO's `slow down! please wait x seconds` responses. It automatically sleeps and retries.
- **Multi-Account Support**: Drop as many Discord Tokens as you want into `tokens.txt` and it will securely cycle through all of them.

## ⚙️ Installation

1. **Prerequisites**: Ensure you have Python 3.7+ installed.
2. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/hbUtil.git
   cd hbUtil
   ```
3. **Install Dependencies**:
   This project relies on `aiohttp` for lightweight asynchronous HTTP requests to Discord.
   ```bash
   # Windows
   pip install aiohttp

   # macOS / Linux
   pip3 install aiohttp
   ```

## 🔐 Setup

1. Copy the example tokens file:
   ```bash
   cp tokens.example.txt tokens.txt
   ```
2. Open `tokens.txt` in a text editor and paste your Discord User Tokens (one token per line).
   *Note: `tokens.txt` is already added to `.gitignore` to prevent accidental leaks.*

## 🛠️ Usage

### Basic Usage
To run the auto-upgrader on all tokens using the default optimal Core Traits (`cost`, `efficiency`, `duration`, `gain`):

```bash
python auto_huntbot.py --channel 123456789012345678
```
*(Replace `123456789012345678` with the ID of the Discord channel where the OwO bot is present.)*

### Dynamic Trait Selection
If you want to focus exclusively on specific traits (for example, you want to burn essence on `radar` and `experience`):

```bash
python auto_huntbot.py --channel 123456789012345678 --traits radar experience
```

### Dry-Run / Test Mode
If you want to see what decisions the bot *would* make without actually sending any commands or spending any essence, use the `--test` flag. This will simulate a default base-level account:

```bash
python auto_huntbot.py --channel 123456789012345678 --test
```

## 📜 Strategy Documentation
For a deep dive into the math and strategy behind the bot's upgrade logic, see [analysis.txt](analysis.txt).

## ⚠️ Disclaimer
Automating user accounts (Self-botting) is against Discord's Terms of Service. Use this tool responsibly, in private servers, and at your own risk. The developers are not responsible for any account suspensions.