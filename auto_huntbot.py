import asyncio
import re
import argparse
from lightweight_discord import DiscordClient
from hbcalc import calculate_essence_cost, get_max_level, get_optimal_upgrade

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
            text += f"{field.get('name', '')} {field.get('value', '')}\n"

    # Parse levels
    # Efficiency - Lvl 199
    # Duration - Lvl 200
    # Cost - Lvl 5 [MAX]
    # Gain - Lvl 141
    # Experience - Lvl 21
    # Radar - Lvl 1
    # Animal Essence - 239,185

    traits = ["efficiency", "duration", "cost", "gain", "experience", "radar"]
    for trait in traits:
        # Looking for `Efficiency - \n ... Lvl 199` or `Efficiency\nLvl 199`
        # Because we flattened it, we can just search for the trait name and the closest Lvl
        match = re.search(f"{trait}.*?Lvl\\s+(\\d+)", text, re.IGNORECASE | re.DOTALL)
        if match:
            stats[trait] = int(match.group(1))

    # Parse essence
    # Current Max Autohunt: 4,592 animals, 72,262 essence
    # Also "Animal Essence - 239,185"
    essence_match = re.search(r"Animal Essence\s*-\s*([\d,]+)", text, re.IGNORECASE)
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
            "efficiency": 199,
            "duration": 200,
            "cost": 5,
            "gain": 141,
            "experience": 21,
            "radar": 1,
            "animal_essence": 239185  # Used the second account's essence for testing
        }
        print(f"Current Stats: {stats}")

        current_essence = stats["animal_essence"]

        while current_essence > 0:
            optimal_trait, count, cost = get_optimal_upgrade(stats, current_essence)

            if not optimal_trait or count == 0:
                print("No affordable upgrades left or all traits maxed.")
                break

            print(f"Calculated Optimal Upgrade: {optimal_trait} for {count} levels (Cost: {cost})")
            print(f"TEST MODE: Would have sent `owo upgrade {optimal_trait} {count}`")

            # Update local stats and loop
            stats[optimal_trait] += count
            current_essence -= cost
            stats["animal_essence"] = current_essence
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
                optimal_trait, count, cost = get_optimal_upgrade(stats, current_essence)

                if not optimal_trait or count == 0:
                    print("No affordable upgrades left or all traits maxed.")
                    break

                print(f"Calculated Optimal Upgrade: {optimal_trait} for {count} levels (Cost: {cost})")

                success = await upgrade_trait(client, channel_id, optimal_trait, count)
                if not success:
                    break # Stop if upgrade failed

                # Update local stats and loop
                stats[optimal_trait] += count
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
