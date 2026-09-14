"""Small, simulator-independent definitions for the first handoff experiment."""


def summarize(episodes, n_stages):
    if not episodes:
        raise ValueError("Cannot summarize an empty evaluation")
    count = len(episodes)
    successes = [sum(row["completed"] > stage for row in episodes)
                 for stage in range(n_stages)]
    reached = [count] + successes[:-1]
    return {
        "episodes": count,
        "stage_reached_counts": reached,
        "stage_success_counts": successes,
        "prefix_success_rates": [n / count for n in successes],
        "conditional_success_rates": [n / d if d else None for n, d in zip(successes, reached)],
        "success_rate": successes[-1] / count,
        "mean_steps": sum(row["steps"] for row in episodes) / count,
    }


def rpd(original, modified):
    return (original - modified) / original if original > 0 else None


def reset_robot_state(current, reference, mode):
    if mode not in ("original", "none"):
        raise ValueError("reset mode must be original or none")
    if current.shape != reference.shape or current.ndim != 1 or len(current) < 42:
        raise ValueError("Incompatible BOSS flattened state vectors")
    result = current.copy()
    if mode == "original":
        # Preserve the published fixed slices; [41:] is not a general qvel offset.
        result[1:10] = reference[1:10]
        result[41:] = reference[41:]
    return result


def model_index(modified_bddl, original_names, mapping):
    matches = [key.removesuffix(".bddl") for key, values in mapping.items()
               if modified_bddl in values]
    if len(matches) != 1 or matches[0] not in original_names:
        raise ValueError(f"Expected one original skill for {modified_bddl}, got {matches}")
    return original_names.index(matches[0])


def select_task_ids(n_tasks, requested=None):
    ids = list(range(n_tasks)) if requested is None else list(requested)
    if not ids or len(set(ids)) != len(ids) or any(type(i) is not int or not 0 <= i < n_tasks for i in ids):
        raise ValueError(f"Task IDs must be unique integers in [0, {n_tasks - 1}]")
    return ids
