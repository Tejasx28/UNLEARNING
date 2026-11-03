"""Small, runnable explanation of the project's ATU controller decisions.

Uses the project's default thresholds and sample weights.
The example supplies illustrative measurements; it does not train an LLM.
Actual implementation: src/atu/controller.py and src/atu/trainer.py.
"""


def classify_target(current_score, initial_score, leaked,
                    floor=-3.16265, stubborn_threshold=-1.8):
    # A recovery probe has priority, even when the direct-answer score is low.
    if leaked:
        return "LEAKING", 1.8
    if current_score <= floor:
        return "SUPPRESSED", 0.0
    if current_score > stubborn_threshold:
        return "STUBBORN", 1.4

    gap = (current_score - floor) / max(0.1, initial_score - floor)
    return "UNLEARNING", max(0.2, min(1.0, gap))


def stop_decision(states, initial_retain_score, current_retain_score,
                  any_dev_leak, max_drop=0.03):
    # Retained-knowledge risk has priority over a success decision.
    drift = initial_retain_score - current_retain_score
    if drift > max_drop:
        return "STOP: retained-knowledge risk"
    if states and all(state == "SUPPRESSED" for state in states) and not any_dev_leak:
        return "STOP: all targets suppressed, zero development leaks"
    return "CONTINUE: remeasure after the next training round"


if __name__ == "__main__":
    examples = [
        ("Fact A", -3.60, -1.00, False),
        ("Fact B", -2.50, -1.00, False),
        ("Fact C", -1.00, -0.50, False),
        ("Fact D", -3.60, -1.00, True),
    ]
    print("Illustrative measurements, not experimental results\n")
    states = []
    for name, current, initial, leaked in examples:
        state, weight = classify_target(current, initial, leaked)
        states.append(state)
        print(f"{name}: {state:11s}  sample weight = {weight:.2f}")

    print("\n" + stop_decision(states, -1.00, -1.01, any_dev_leak=True))
    print(stop_decision(["SUPPRESSED"], -1.00, -1.01, any_dev_leak=False))
    print(stop_decision(["SUPPRESSED"], -1.00, -1.05, any_dev_leak=False))
