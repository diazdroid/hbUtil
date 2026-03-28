import json
import os

def load_traits_data():
    """
    Loads trait cost data. If not found, returns empty dict.
    We generated traits_data.json previously in the workflow.
    """
    if os.path.exists("traits_data.json"):
        with open("traits_data.json", "r") as f:
            return json.load(f)
    return {}

TRAITS_DATA = load_traits_data()

def get_max_level(trait):
    """
    Returns max level for a given trait.
    """
    max_levels = {
        "cost": 5,
        "efficiency": 215,
        "duration": 235, # Extrapolated from wiki
        "gain": 200,
        "experience": 200,
        "radar": 999
    }
    return max_levels.get(trait, 0)

def apply_upgrade_spend(trait, current_level, current_progress, essence_spent):
    """
    Simulates spending essence on a trait to determine its new level and progress.
    Returns (new_level, new_progress).
    """
    trait_data = TRAITS_DATA.get(trait, [])
    if not trait_data:
        return current_level, current_progress

    remaining_spend = essence_spent
    new_level = current_level
    new_progress = current_progress

    for level_info in trait_data:
        if new_level == level_info["level"]:
            cost_to_next = level_info["essence_to_level_up"] - new_progress
            if remaining_spend >= cost_to_next:
                remaining_spend -= cost_to_next
                new_level += 1
                new_progress = 0
            else:
                new_progress += remaining_spend
                remaining_spend = 0
                break

    return new_level, new_progress

def calculate_essence_cost(trait, current_level, target_level, progress=0):
    """
    Calculates total essence required to go from current_level to target_level.
    It subtracts any progress already invested towards the first level up.
    """
    trait_data = TRAITS_DATA.get(trait, [])
    if not trait_data:
        # Fallback or empty
        return 0

    total_cost = 0
    first_level_adjusted = False

    for level_info in trait_data:
        lvl = level_info["level"]
        if current_level <= lvl < target_level:
            cost = level_info["essence_to_level_up"]
            if not first_level_adjusted:
                cost -= progress
                # If negative (shouldn't happen), cap at 0
                cost = max(cost, 0)
                first_level_adjusted = True
            total_cost += cost

    return total_cost

def get_optimal_upgrade(current_stats, available_essence):
    """
    Returns (trait_name, amount_to_spend) for the optimal upgrade.
    New Algorithm: ROI Driven.
    Instead of hard-blocking the entire progression on 'Cost', we find the cheapest upgrade among the
    core traits (Cost, Efficiency, Duration, and optionally Gain) and upgrade that. This ensures the account
    always progresses and generates more essence while naturally reaching the thresholds for expensive Cost levels.
    """
    # Traits considered for active ROI-based progression (in order of tie-breaker priority)
    core_traits = ["cost", "efficiency", "duration", "gain"]

    # Calculate the exact cost for the next immediate level of each core trait
    next_level_costs = {}
    for trait in core_traits:
        curr_lvl = current_stats[trait]["level"]
        max_lvl = get_max_level(trait)

        if curr_lvl < max_lvl:
            cost = calculate_essence_cost(trait, curr_lvl, curr_lvl + 1, current_stats[trait]["progress"])
            next_level_costs[trait] = cost

    if not next_level_costs:
        # If all core traits are maxed, fallback to Experience then Radar
        for trait in ["experience", "radar"]:
            curr_lvl = current_stats[trait]["level"]
            max_lvl = get_max_level(trait)
            if curr_lvl < max_lvl:
                cost = calculate_essence_cost(trait, curr_lvl, curr_lvl + 1, current_stats[trait]["progress"])
                if cost <= available_essence:
                    # Calculate how much we can spend in total on this fallback trait
                    total_spend = 0
                    first_level_adjusted = False
                    for level_info in TRAITS_DATA.get(trait, []):
                        lvl = level_info["level"]
                        if curr_lvl <= lvl < max_lvl:
                            c = level_info["essence_to_level_up"]
                            if not first_level_adjusted:
                                c -= current_stats[trait]["progress"]
                                c = max(c, 0)
                                first_level_adjusted = True
                            if total_spend + c <= available_essence:
                                total_spend += c
                            else:
                                break
                    if total_spend > 0:
                        return trait, total_spend
        return None, 0

    # Find the cheapest core trait to upgrade next
    cheapest_trait = min(next_level_costs, key=next_level_costs.get)
    cheapest_cost = next_level_costs[cheapest_trait]

    # If we can't afford the absolute cheapest next upgrade, we just wait.
    if cheapest_cost > available_essence:
        return None, 0

    # If we can afford it, let's buy as many levels of THIS specific trait as we can,
    # BUT we must stop if the next level of this trait becomes more expensive than
    # another core trait's current next level. This keeps progression balanced.

    # Get the cost of the second cheapest trait to act as our "cap" for balanced spending
    other_costs = [cost for t, cost in next_level_costs.items() if t != cheapest_trait]
    max_level_cost_cap = min(other_costs) if other_costs else float('inf')

    total_spend = 0
    curr_lvl = current_stats[cheapest_trait]["level"]
    progress = current_stats[cheapest_trait]["progress"]
    max_lvl = get_max_level(cheapest_trait)
    first_level_adjusted = False

    for level_info in TRAITS_DATA.get(cheapest_trait, []):
        lvl = level_info["level"]
        if curr_lvl <= lvl < max_lvl:
            cost = level_info["essence_to_level_up"]

            if not first_level_adjusted:
                cost -= progress
                cost = max(cost, 0)
                first_level_adjusted = True
            else:
                # For subsequent levels, compare the FULL cost of that level to the cap
                if cost > max_level_cost_cap:
                    break

            if total_spend + cost <= available_essence:
                total_spend += cost
            else:
                break

    if total_spend > 0:
        return cheapest_trait, total_spend

    return None, 0
