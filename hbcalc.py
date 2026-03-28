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

def calculate_essence_cost(trait, current_level, target_level):
    """
    Calculates total essence required to go from current_level to target_level.
    """
    trait_data = TRAITS_DATA.get(trait, [])
    if not trait_data:
        # Fallback or empty
        return 0

    total_cost = 0
    for level_info in trait_data:
        lvl = level_info["level"]
        if current_level <= lvl < target_level:
            total_cost += level_info["essence_to_level_up"]

    return total_cost

def get_optimal_upgrade(current_stats, available_essence):
    """
    Returns (trait_name, count, total_cost) for the optimal upgrade.
    Priorities: Cost > Efficiency/Duration (cheaper) > Gain > Experience > Radar
    Instead of buying 1 by 1, it calculates the maximum affordable levels for the top priority.
    If the top priority is not affordable, it stops and waits (returns None),
    enforcing the roadmap rather than falling back to buying cheaper, lower-priority traits.
    """
    def calc_max_affordable(trait, current_lvl):
        max_lvl = get_max_level(trait)
        affordable_levels = 0
        total_cost = 0

        for level_info in TRAITS_DATA.get(trait, []):
            lvl = level_info["level"]
            if current_lvl + affordable_levels <= lvl < max_lvl:
                cost = level_info["essence_to_level_up"]
                if total_cost + cost <= available_essence:
                    affordable_levels += 1
                    total_cost += cost
                else:
                    break
        return affordable_levels, total_cost

    # 1. Cost (Max 5)
    if current_stats["cost"] < get_max_level("cost"):
        count, cost = calc_max_affordable("cost", current_stats["cost"])
        if count > 0:
            return "cost", count, cost
        return None, 0, 0 # Enforce priority: Wait for essence

    # 2. Efficiency & Duration (Parallel)
    eff_lvl = current_stats["efficiency"]
    dur_lvl = current_stats["duration"]

    eff_max = get_max_level("efficiency")
    dur_max = get_max_level("duration")

    if eff_lvl < eff_max or dur_lvl < dur_max:
        # Determine which one is cheaper right now to maintain parallelism
        eff_cost_1 = calculate_essence_cost("efficiency", eff_lvl, eff_lvl + 1) if eff_lvl < eff_max else float('inf')
        dur_cost_1 = calculate_essence_cost("duration", dur_lvl, dur_lvl + 1) if dur_lvl < dur_max else float('inf')

        target_trait = "efficiency" if eff_cost_1 <= dur_cost_1 else "duration"
        count, cost = calc_max_affordable(target_trait, current_stats[target_trait])

        if count > 0:
            # Only buy 1 level or multiple if they are cheap, but to maintain parallelism let's just
            # buy until it costs more than the other trait's current next level, OR buy all if we have tons
            # To avoid API spam, we buy all we can afford for this target trait, up to where it's still reasonable,
            # but getting max affordable is generally safe and reduces API calls.
            return target_trait, count, cost
        return None, 0, 0 # Enforce priority: Wait for essence

    # 3. Gain (Max 200)
    if current_stats["gain"] < get_max_level("gain"):
        count, cost = calc_max_affordable("gain", current_stats["gain"])
        if count > 0:
            return "gain", count, cost
        return None, 0, 0 # Enforce priority

    # 4. Experience (Max 200)
    if current_stats["experience"] < get_max_level("experience"):
        count, cost = calc_max_affordable("experience", current_stats["experience"])
        if count > 0:
            return "experience", count, cost
        return None, 0, 0 # Enforce priority

    # 5. Radar (Max 999)
    if current_stats["radar"] < get_max_level("radar"):
        count, cost = calc_max_affordable("radar", current_stats["radar"])
        if count > 0:
            return "radar", count, cost

    return None, 0, 0
