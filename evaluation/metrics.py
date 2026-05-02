from typing import Dict, List


def evaluate_predictions(gold: List[str], pred: List[str]) -> Dict[str, float]:
    if len(gold) != len(pred):
        raise ValueError("gold and pred must have same length")
    if not gold:
        return {"accuracy": 0.0, "precision": 0.0, "recall": 0.0}

    correct = sum(1 for g, p in zip(gold, pred) if g == p)
    labels = set(gold) | set(pred)
    tp = fp = fn = 0
    for label in labels:
        for g, p in zip(gold, pred):
            if p == label and g == label:
                tp += 1
            elif p == label and g != label:
                fp += 1
            elif p != label and g == label:
                fn += 1

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    return {
        "accuracy": correct / len(gold),
        "precision": precision,
        "recall": recall,
    }
