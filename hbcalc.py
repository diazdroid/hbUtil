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
    max_lvl = get_max_level(trait)

    if not trait_data:
        return current_level, current_progress

    remaining_spend = essence_spent
    new_level = current_level
    new_progress = current_progress

    for level_info in trait_data:
        if new_level == level_info["level"] and new_level < max_lvl:
            cost_to_next = level_info["essence_to_level_up"] - new_progress
            if remaining_spend >= cost_to_next:
                remaining_spend -= cost_to_next
                new_level += 1
                new_progress = 0
            else:
                new_progress += remaining_spend
                remaining_spend = 0
                break

    # Safeguard caps
    if new_level >= max_lvl:
        new_level = max_lvl
        new_progress = 0

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

def calculate_bulk_upgrades(current_stats, available_essence, target_traits=None):
    """
    Simulates the ROI progression in memory to avoid spamming the Discord API.
    Returns a dictionary of total essence to spend per trait.
    If target_traits is provided, it ONLY considers and upgrades those traits.
    """
    if target_traits is None:
        target_traits = ["cost", "efficiency", "duration", "gain"]

    import copy
    stats = copy.deepcopy(current_stats)
    remaining_essence = available_essence
    spend_plan = {}

    for trait in target_traits:
        spend_plan[trait] = 0

    while remaining_essence > 0:
        next_level_costs = {}
        for trait in target_traits:
            curr_lvl = stats[trait]["level"]
            max_lvl = get_max_level(trait)

            if curr_lvl < max_lvl:
                cost = calculate_essence_cost(trait, curr_lvl, curr_lvl + 1, stats[trait]["progress"])
                next_level_costs[trait] = cost

        if not next_level_costs:
            # All strictly targeted traits are maxed out, stop progression.
            break

        # Find the cheapest trait to upgrade next among the targets
        cheapest_trait = min(next_level_costs, key=next_level_costs.get)
        cheapest_cost = next_level_costs[cheapest_trait]

        # If we can't afford the absolute cheapest next upgrade, stop completely.
        if cheapest_cost > remaining_essence:
            break

        # Get the cost of the second cheapest trait to act as our "cap" for balanced spending
        other_costs = [cost for t, cost in next_level_costs.items() if t != cheapest_trait]
        max_level_cost_cap = min(other_costs) if other_costs else float('inf')

        total_spend = 0
        curr_lvl = stats[cheapest_trait]["level"]
        progress = stats[cheapest_trait]["progress"]
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
                    if cost > max_level_cost_cap:
                        break

                if total_spend + cost <= remaining_essence:
                    total_spend += cost
                else:
                    break

        if total_spend > 0:
            spend_plan[cheapest_trait] += total_spend
            remaining_essence -= total_spend

            # Simulate the state update in memory
            new_lvl, new_prog = apply_upgrade_spend(cheapest_trait, stats[cheapest_trait]["level"], stats[cheapest_trait]["progress"], total_spend)
            stats[cheapest_trait]["level"] = new_lvl
            stats[cheapest_trait]["progress"] = new_prog
        else:
            break

    # Clean up empty spends
    final_plan = {k: v for k, v in spend_plan.items() if v > 0}
    return final_plan
