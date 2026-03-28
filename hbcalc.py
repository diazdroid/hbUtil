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
    Priorities: Cost > Efficiency/Duration (cheaper) > Gain > Experience > Radar
    It calculates the exact amount of essence to spend (e.g., 30000) instead of levels,
    incorporating any current progress the trait has.
    """
    def calc_amount_to_spend(trait, current_lvl, progress):
        max_lvl = get_max_level(trait)
        total_cost = 0
        first_level_adjusted = False

        for level_info in TRAITS_DATA.get(trait, []):
            lvl = level_info["level"]
            if current_lvl <= lvl < max_lvl:
                cost = level_info["essence_to_level_up"]
                if not first_level_adjusted:
                    cost -= progress
                    cost = max(cost, 0)
                    first_level_adjusted = True

                if total_cost + cost <= available_essence:
                    total_cost += cost
                else:
                    break
        return total_cost

    # 1. Cost (Max 5)
    if current_stats["cost"]["level"] < get_max_level("cost"):
        cost = calc_amount_to_spend("cost", current_stats["cost"]["level"], current_stats["cost"]["progress"])
        if cost > 0:
            return "cost", cost
        return None, 0 # Enforce priority: Wait for essence

    # 2. Efficiency & Duration (Parallel)
    eff_lvl = current_stats["efficiency"]["level"]
    dur_lvl = current_stats["duration"]["level"]
    eff_prog = current_stats["efficiency"]["progress"]
    dur_prog = current_stats["duration"]["progress"]

    eff_max = get_max_level("efficiency")
    dur_max = get_max_level("duration")

    if eff_lvl < eff_max or dur_lvl < dur_max:
        # Determine which one is cheaper right now to maintain parallelism
        eff_cost_1 = calculate_essence_cost("efficiency", eff_lvl, eff_lvl + 1, eff_prog) if eff_lvl < eff_max else float('inf')
        dur_cost_1 = calculate_essence_cost("duration", dur_lvl, dur_lvl + 1, dur_prog) if dur_lvl < dur_max else float('inf')

        if eff_cost_1 <= dur_cost_1:
            target_trait = "efficiency"
            other_cost = dur_cost_1
        else:
            target_trait = "duration"
            other_cost = eff_cost_1

        # Limit spending so we don't accidentally max out one trait while the other is left behind.
        # Stop buying levels for the target_trait once its next level cost exceeds the other trait's cost.
        def calc_balanced_spend(trait, current_lvl, progress, max_spend_cap, max_level_cost_cap):
            max_lvl = get_max_level(trait)
            total_cost = 0
            first_level_adjusted = False

            for level_info in TRAITS_DATA.get(trait, []):
                lvl = level_info["level"]
                if current_lvl <= lvl < max_lvl:
                    cost = level_info["essence_to_level_up"]

                    if not first_level_adjusted:
                        cost -= progress
                        cost = max(cost, 0)
                        first_level_adjusted = True
                    else:
                        # For subsequent levels, compare the FULL cost of that level to max_level_cost_cap
                        if cost > max_level_cost_cap:
                            break

                    if total_cost + cost <= max_spend_cap:
                        total_cost += cost
                    else:
                        break
            return total_cost

        cost = calc_balanced_spend(target_trait, current_stats[target_trait]["level"], current_stats[target_trait]["progress"], available_essence, other_cost)

        if cost > 0:
            return target_trait, cost
        return None, 0 # Enforce priority: Wait for essence

    # 3. Gain (Max 200)
    if current_stats["gain"]["level"] < get_max_level("gain"):
        cost = calc_amount_to_spend("gain", current_stats["gain"]["level"], current_stats["gain"]["progress"])
        if cost > 0:
            return "gain", cost
        return None, 0 # Enforce priority

    # 4. Experience (Max 200)
    if current_stats["experience"]["level"] < get_max_level("experience"):
        cost = calc_amount_to_spend("experience", current_stats["experience"]["level"], current_stats["experience"]["progress"])
        if cost > 0:
            return "experience", cost
        return None, 0 # Enforce priority

    # 5. Radar (Max 999)
    if current_stats["radar"]["level"] < get_max_level("radar"):
        cost = calc_amount_to_spend("radar", current_stats["radar"]["level"], current_stats["radar"]["progress"])
        if cost > 0:
            return "radar", cost

    return None, 0
