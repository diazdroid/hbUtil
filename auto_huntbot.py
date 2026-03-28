import asyncio
import re
import argparse
import aiohttp
from lightweight_discord import DiscordClient, DiscordAPIError
from hbcalc import calculate_essence_cost, get_max_level, calculate_bulk_upgrades, apply_upgrade_spend

# Version
VERSION = "1.0.1"

# Owo bot ID
OWO_ID = "408785106942164992"

async def check_for_updates():
    """
    Checks the diazdroid/hbUtil GitHub repository for a newer version of the script.
    """
    url = "https://raw.githubusercontent.com/diazdroid/hbUtil/main/auto_huntbot.py"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=5) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    match = re.search(r'VERSION\s*=\s*"([^"]+)"', text)
                    if match:
                        remote_version = match.group(1)
                        if remote_version != VERSION:
                            print(f"\n[!] A new version of hbUtil is available (v{remote_version})!")
                            print(f"[!] Please update your script by re-running the installation command or doing 'git pull'.")
                            print(f"[!] You are currently on v{VERSION}.\n")
    except Exception:
        # Silently fail if there is no internet connection or GitHub is unreachable
        pass

async def read_tokens(file_path="tokens.txt"):
    try:
        with open(file_path, "r") as f:
            tokens = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        return tokens
    except FileNotFoundError:
        print(f"Error: {file_path} not found.")
        return []

def parse_hb_message(content, embeds):
    """
    Parses the 'owo hb' message to extract stats.
    Returns a dict with traits and essence.
    """
    stats = {
        "efficiency": 0,
        "duration": 0,
        "cost": 0,
        "gain": 0,
        "experience": 0,
        "radar": 0,
        "animal_essence": 0
    }

    text = ""
    if content:
        text += content + "\n"
    for embed in embeds:
        if "description" in embed:
            text += embed["description"] + "\n"
        for field in embed.get("fields", []):
            name = field.get('name') or field.get('rawName') or ''
            val = field.get('value') or field.get('rawValue') or ''
            text += f"{name} {val}\n"

    # Parse levels and progress
    # ⏱️ Efficiency - `240/H` `Lvl 215 [MAX]`
    # ⏳ Duration - `21.3H` `Lvl 208 [0/87952]`
    # 🔧 Gain - `4325 essence/H` `Lvl 173 [48737/107891]`

    traits = ["efficiency", "duration", "cost", "gain", "experience", "radar"]
    for trait in traits:
        # Dictionary to hold both level and current progress towards next level
        stats[trait] = {"level": 0, "progress": 0}

        # Looking for `Efficiency` followed by `Lvl <number>` ignoring backticks
        # And potentially a progress bracket `[current/total]`
        clean_text = text.replace('`', '')

        # Match level
        match = re.search(f"{trait}.*?Lvl\\s+(\\d+)", clean_text, re.IGNORECASE | re.DOTALL)
        if match:
            stats[trait]["level"] = int(match.group(1))

            # Now look for the bracket right after the level, e.g. `[48737/107891]` or `[MAX]`
            # We constrain the search to a small window after the 'Lvl XX' to avoid matching another trait's bracket
            substr_after_lvl = clean_text[match.end(1):match.end(1)+50]
            bracket_match = re.search(r"\[([\d,]+)/[\d,]+\]", substr_after_lvl)
            if bracket_match:
                stats[trait]["progress"] = int(bracket_match.group(1).replace(",", ""))

    # Parse essence
    # <a:essence:451638978299428875> Animal Essence - `0`
    clean_text = text.replace('`', '')
    essence_match = re.search(r"Animal Essence\s*-\s*([\d,]+)", clean_text, re.IGNORECASE)
    if essence_match:
        stats["animal_essence"] = int(essence_match.group(1).replace(",", ""))

    return stats

async def wait_for_owo_reply(client, channel_id, command, delay=2, max_wait=10):
    """
    Sends a command and waits for OwO bot to reply.
    """
    # Get last message id to only look at new messages
    msgs = await client.get_messages(channel_id, limit=1)
    last_id = msgs[0]["id"] if msgs else "0"

    await client.send_message(channel_id, command)

    # Wait for response
    for _ in range(int(max_wait / delay)):
        await asyncio.sleep(delay)
        recent_msgs = await client.get_messages(channel_id, limit=5)
        for msg in recent_msgs:
            if msg["id"] <= last_id:
                break
            if msg.get("author", {}).get("id") == OWO_ID:
                # Check for slowmode
                if "slow down" in msg.get("content", "").lower():
                    # Extract slowmode time
                    slow_match = re.search(r"(\d+)\s*second", msg["content"], re.IGNORECASE)
                    wait_time = int(slow_match.group(1)) if slow_match else 5
                    print(f"Hit slowmode! Waiting {wait_time} seconds...")
                    await asyncio.sleep(wait_time + 1)
                    return await wait_for_owo_reply(client, channel_id, command, delay, max_wait)
                return msg
    return None

async def upgrade_trait(client, channel_id, trait, count):
    """
    Sends the upgrade command.
    """
    print(f"[*] Upgrading '{trait}' with {count:,} essence...")
    cmd = f"owo upgrade {trait} {count}"
    reply = await wait_for_owo_reply(client, channel_id, cmd)
    if reply:
        if "You do not have enough animal essence" in reply.get("content", ""):
            print("[-] Failed: Not enough animal essence.")
            return False
        # Extract the success confirmation line
        lines = reply.get('content', '').split('\n')
        success_line = lines[0] if lines else "Success"
        # Clean discord formatting like bolding
        success_line = success_line.replace('**', '')
        print(f"[+] {success_line}")
        return True
    return False

async def process_account(token, channel_id, is_test=False, target_traits=None):
    # Mask token for security
    masked_token = f"{token[:15]}..." if len(token) > 15 else token
    print(f"\n{'='*40}")
    print(f"[ACCOUNT] Processing token: {masked_token}")
    print(f"{'='*40}")

    if is_test:
        print("[!] TEST MODE: Skipping real API calls.")
        # Mocking data based on a blank account to test the new ROI progression
        stats = {
            "efficiency": {"level": 0, "progress": 0},
            "duration": {"level": 0, "progress": 0},
            "cost": {"level": 0, "progress": 0},
            "gain": {"level": 0, "progress": 0},
            "experience": {"level": 0, "progress": 0},
            "radar": {"level": 0, "progress": 0},
            "animal_essence": 99999999
        }
        print(f"[*] Base Essence: {stats['animal_essence']:,}")

        current_essence = stats["animal_essence"]

        bulk_spends = calculate_bulk_upgrades(stats, current_essence, target_traits)
        if not bulk_spends:
            print("[-] No affordable upgrades left or all traits maxed.")
        else:
            print(f"[+] Bulk Calculation Complete: {bulk_spends}")
            for trait, cost in bulk_spends.items():
                print(f"   > [TEST] Sent: `owo upgrade {trait} {cost}`")

                # Update local stats for simulation visibility
                new_level, new_progress = apply_upgrade_spend(trait, stats[trait]["level"], stats[trait]["progress"], cost)
                stats[trait]["level"] = new_level
                stats[trait]["progress"] = new_progress
                current_essence -= cost
                stats["animal_essence"] = current_essence

                prog_str = "MAX" if new_level >= get_max_level(trait) else f"{new_progress:,} XP"
                print(f"   > [TEST] New State: {trait.capitalize()} Lvl {new_level} [{prog_str}] | Remaining Essence: {current_essence:,}")

    else:
        try:
            async with DiscordClient(token) as client:
                print("[*] Fetching HuntBot statistics (`owo hb`)...")
                reply = await wait_for_owo_reply(client, channel_id, "owo hb")
                if not reply:
                    print("[-] Failed to retrieve HuntBot information from OwO bot. Proceeding to next account.")
                    return

                stats = parse_hb_message(reply.get("content", ""), reply.get("embeds", []))

                if stats["animal_essence"] <= 0:
                    print("[-] No animal essence available for upgrades. Skipping account.")
                    return

                print(f"[*] Available Animal Essence: {stats['animal_essence']:,}")
                current_essence = stats["animal_essence"]

                bulk_spends = calculate_bulk_upgrades(stats, current_essence, target_traits)

                if not bulk_spends:
                    print("[-] No affordable upgrades left for the targeted traits.")
                    return

                print(f"[+] Commencing Bulk Spends: {bulk_spends}")

                for trait, cost in bulk_spends.items():
                    success = await upgrade_trait(client, channel_id, trait, cost)
                    if not success:
                        print(f"[-] Upgrade sequence halted for {trait}.")
                        break

                    # Small delay to respect rate limits between commands
                    await asyncio.sleep(2)
            print("[+] Account processing complete.")
        except DiscordAPIError as e:
            if e.status == 401:
                print("[-] Error: Unauthorized (401). Invalid or expired token. Skipping account.")
            elif e.status == 403:
                print("[-] Error: Forbidden (403). Account lacks access to this channel or is locked. Skipping.")
            else:
                print(f"[-] Discord API Error: {e.status} - {e.message}")
        except Exception as e:
            print(f"[-] An unexpected error occurred: {str(e)}")

async def main():
    parser = argparse.ArgumentParser(description="OwO Huntbot Auto Upgrader")
    parser.add_argument("--channel", type=str, help="Discord Channel ID to target")
    parser.add_argument("--test", action="store_true", help="Run in test mode without hitting Discord API")
    parser.add_argument("--traits", type=str, nargs="+",
                        help="List of traits to upgrade dynamically (e.g. --traits cost efficiency duration gain).",
                        default=["cost", "efficiency", "duration", "gain"])
    args = parser.parse_args()

    # Pre-execution checks
    await check_for_updates()

    if not args.test and not args.channel:
        print("[-] Error: '--channel' argument is required unless running in '--test' mode.")
        return

    tokens = await read_tokens()
    if not tokens:
        print("[-] Error: 'tokens.txt' not found or empty.")
        return

    # Validate provided traits
    valid_traits = {"efficiency", "duration", "cost", "gain", "experience", "radar"}
    target_traits = [t.lower() for t in args.traits if t.lower() in valid_traits]
    if not target_traits:
        print("[-] Error: No valid traits provided in arguments. Exiting.")
        return

    print(f"\n[INFO] Initializing OwO HuntBot Upgrader v{VERSION}")
    print(f"[INFO] Targeted Traits: {', '.join(target_traits)}")
    print(f"[INFO] Loaded Accounts: {len(tokens)}")

    for token in tokens:
        await process_account(token, args.channel, is_test=args.test, target_traits=target_traits)
        if not args.test:
            await asyncio.sleep(5) # Cooldown between accounts

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[!] Execution interrupted by user.")
