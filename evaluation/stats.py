"""Statistics for evaluation reports: intervals, paired tests, calibration and agreement.

Pure functions with no third-party dependencies, so they are cheap to unit test.
"""
import math
import random


def wilson(successes, total, z=1.96):
    """95% Wilson score interval for a proportion, as (low, high)."""
    if total == 0:
        return (0.0, 0.0)
    p = successes / total
    denominator = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denominator
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return (max(0.0, centre - half), min(1.0, centre + half))


def bootstrap_ci(values, iterations=10000, seed=7, alpha=0.05):
    """Percentile bootstrap interval for the mean of ``values``."""
    if not values:
        return (0.0, 0.0)
    rng = random.Random(seed)
    n = len(values)
    means = sorted(sum(values[rng.randrange(n)] for _ in range(n)) / n for _ in range(iterations))
    return (means[int(alpha / 2 * iterations)], means[int((1 - alpha / 2) * iterations) - 1])


def paired_bootstrap(a, b, iterations=10000, seed=7, alpha=0.05):
    """Mean of a - b over paired items with a bootstrap interval and two-sided p-value."""
    if len(a) != len(b):
        raise ValueError("paired samples must have the same length")
    if not a:
        return {"diff": 0.0, "low": 0.0, "high": 0.0, "p": 1.0}
    diffs = [x - y for x, y in zip(a, b, strict=True)]
    rng = random.Random(seed)
    n = len(diffs)
    means = sorted(sum(diffs[rng.randrange(n)] for _ in range(n)) / n for _ in range(iterations))
    below = sum(m <= 0 for m in means) / iterations
    above = sum(m >= 0 for m in means) / iterations
    return {"diff": sum(diffs) / n, "low": means[int(alpha / 2 * iterations)],
            "high": means[int((1 - alpha / 2) * iterations) - 1], "p": min(1.0, 2 * min(below, above))}


def mcnemar_exact(wins, losses):
    """Two-sided exact McNemar p-value from the discordant counts."""
    n = wins + losses
    if n == 0:
        return 1.0
    k = min(wins, losses)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def calibrate_floor(recall_by_floor, reference_recall, keep=0.98):
    """Highest evidence floor whose recall stays within ``keep`` of the ungated reference.

    ``recall_by_floor`` maps floor -> recall on a small labelled calibration set.
    Returns None when no floor qualifies (the gate should then stay off).
    """
    qualifying = [floor for floor, recall in recall_by_floor.items() if recall >= keep * reference_recall]
    return max(qualifying) if qualifying else None


def cohen_kappa(first, second):
    """Cohen's kappa for two raters' labels over the same items."""
    if len(first) != len(second):
        raise ValueError("raters must label the same items")
    if not first:
        return 0.0
    n = len(first)
    labels = set(first) | set(second)
    observed = sum(x == y for x, y in zip(first, second, strict=True)) / n
    expected = sum((first.count(label) / n) * (second.count(label) / n) for label in labels)
    return 1.0 if expected == 1 else (observed - expected) / (1 - expected)
