# OwO HuntBot Auto-Upgrader (hbUtil)

An intelligent, lightweight, and fully automated script to mathematically optimize and upgrade your OwO Discord Bot's `HuntBot` traits.

## 🚀 Features

- **Mathematical ROI Solver**: Instead of blindly spending your hard-earned Animal Essence on random levels, this script uses a "Cheapest Next" algorithm. It compares the upcoming costs of all core traits and buys the cheapest one, guaranteeing your essence generation rate snowballs as fast as possible.
- **Bulk Execution (Anti-Spam)**: Simulates the entire spending loop in local memory. Instead of sending 50 small upgrade commands to Discord (which triggers API bans), it bundles the costs and sends exactly *one* command per trait (e.g., `owo upgrade efficiency 45200`).
- **Dynamic Trait Selection**: Choose exactly what you want to upgrade via command-line arguments. Want to focus purely on `gain` and `duration`? You can easily toggle them.
- **Rate-Limit & Slowmode Protection**: Built-in detection for Discord's `429 Too Many Requests` and OwO's `slow down! please wait x seconds` responses. It automatically sleeps and retries.
- **Multi-Account Support**: Drop as many Discord Tokens as you want into `tokens.txt` and it will securely cycle through all of them.

## For Beginners:

### 💻 Windows (One-Click)

Open **PowerShell** as an Administrator and paste the following command. It will automatically install Python (if missing), Git (if missing), download the bot to your Desktop, install its dependencies, and run it.

```powershell
irm "https://raw.githubusercontent.com/diazdroid/hbUtil/main/windows-setup.ps1" | iex
```

Once installed:
1. Go to your Desktop and open the `hbUtil` folder.
2. Open `tokens.txt` in a text editor and paste your Discord User Tokens (one token per line).
3. Double click `run.bat` to start the bot.

---

## For Advanced Users:

### 💻 Windows / Linux

```bash
# Check Python version (Requires 3.7+):
python --version

# Clone the repository:
git clone https://github.com/diazdroid/hbUtil.git

# Enter into the cloned directory:
cd hbUtil

# Install Python Dependencies:
pip install -r requirements.txt

# Create your tokens file
cp tokens.example.txt tokens.txt
```

*(Edit `tokens.txt` to add your tokens)*

### Start the application:

```bash
# For Windows users:
run.bat

# Or manually:
python auto_huntbot.py --channel 123456789012345678
```

---

## 🛠️ Advanced CLI Usage

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