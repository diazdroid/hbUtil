import asyncio
import re
import argparse
from lightweight_discord import DiscordClient
from hbcalc import calculate_essence_cost, get_max_level, get_optimal_upgrade, apply_upgrade_spend

# Owo bot ID
OWO_ID = "408785106942164992"

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
    print(f"Upgrading {trait} by {count} levels...")
    cmd = f"owo upgrade {trait} {count}"
    reply = await wait_for_owo_reply(client, channel_id, cmd)
    if reply:
        if "You do not have enough animal essence" in reply.get("content", ""):
            print("Failed: Not enough animal essence.")
            return False
        print(f"Upgrade successful (or verified): {reply.get('content', '')}")
        return True
    return False

async def process_account(token, channel_id, is_test=False):
    print(f"\n--- Processing account {token[:15]}... ---")

    if is_test:
        print("TEST MODE: Skipping real API calls.")
        # Mocking data based on prompt images
        stats = {
            "efficiency": {"level": 199, "progress": 50504},
            "duration": {"level": 200, "progress": 0},
            "cost": {"level": 5, "progress": 0},
            "gain": {"level": 141, "progress": 0},
            "experience": {"level": 21, "progress": 234},
            "radar": {"level": 1, "progress": 0},
            "animal_essence": 239185  # Used the second account's essence for testing
        }
        print(f"Current Stats: {stats}")

        current_essence = stats["animal_essence"]

        while current_essence > 0:
            optimal_trait, cost = get_optimal_upgrade(stats, current_essence)

            if not optimal_trait or cost <= 0:
                print("No affordable upgrades left or all traits maxed.")
                break

            print(f"Calculated Optimal Upgrade: {optimal_trait} for {cost} essence")
            print(f"TEST MODE: Would have sent `owo upgrade {optimal_trait} {cost}`")

            # Since we only get the cost back, we simulate the state update locally
            new_level, new_progress = apply_upgrade_spend(optimal_trait, stats[optimal_trait]["level"], stats[optimal_trait]["progress"], cost)
            stats[optimal_trait]["level"] = new_level
            stats[optimal_trait]["progress"] = new_progress

            current_essence -= cost
            stats["animal_essence"] = current_essence
            print(f"New state -> {optimal_trait}: Level {new_level} [Progress {new_progress}], Remaining Essence: {current_essence}\n")
    else:
        async with DiscordClient(token) as client:
            print("Fetching HuntBot stats (owo hb)...")
            reply = await wait_for_owo_reply(client, channel_id, "owo hb")
            if not reply:
                print("Failed to get HuntBot info from OwO bot.")
                return

            stats = parse_hb_message(reply.get("content", ""), reply.get("embeds", []))

            print(f"Current Stats: {stats}")

            if stats["animal_essence"] <= 0:
                print("No animal essence available for upgrades. Exiting account.")
                return

            current_essence = stats["animal_essence"]

            while current_essence > 0:
                optimal_trait, cost = get_optimal_upgrade(stats, current_essence)

                if not optimal_trait or cost <= 0:
                    print("No affordable upgrades left or all traits maxed.")
                    break

                print(f"Calculated Optimal Upgrade: {optimal_trait} with {cost} essence")

                success = await upgrade_trait(client, channel_id, optimal_trait, cost)
                if not success:
                    break # Stop if upgrade failed

                # Update local stats correctly
                new_level, new_progress = apply_upgrade_spend(optimal_trait, stats[optimal_trait]["level"], stats[optimal_trait]["progress"], cost)
                stats[optimal_trait]["level"] = new_level
                stats[optimal_trait]["progress"] = new_progress

                current_essence -= cost
                stats["animal_essence"] = current_essence

                await asyncio.sleep(2) # Avoid spamming the API

async def main():
    parser = argparse.ArgumentParser(description="OwO Huntbot Auto Upgrader")
    parser.add_argument("--channel", type=str, help="Discord Channel ID to spam OwO commands", default="1234567890")
    parser.add_argument("--test", action="store_true", help="Run in test mode without hitting API")
    args = parser.parse_args()

    tokens = await read_tokens()
    if not tokens:
        print("No tokens found. Please create tokens.txt and add Discord user tokens.")
        return

    for token in tokens:
        await process_account(token, args.channel, is_test=args.test)
        if not args.test:
            await asyncio.sleep(5) # Delay between accounts

if __name__ == "__main__":
    asyncio.run(main())
