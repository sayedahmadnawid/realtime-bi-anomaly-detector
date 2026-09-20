"""
Anomaly injection engine (generator v2).

Lets us schedule anomalies that modify the generator's normal output for a
window of simulated time, so the downstream detection engine has something
real to catch - and so anomalies can be demoed on demand rather than
waited for.

Anomaly types (per docs/business.md):
    sudden_drop   - value drops sharply to `magnitude` fraction of normal,
                    stays there for the duration
    sudden_spike  - value jumps sharply to `magnitude` multiple of normal,
                    stays there for the duration
    slow_drift    - value gradually moves from normal (1.0x) to `magnitude`x
                    linearly over the duration
    flatline      - value forced to (near) zero for the duration,
                    simulating an outage/pipeline failure

An anomaly targets a specific metric, and optionally a specific category
(None = applies to every category of that metric, and to site-wide
metrics like traffic/signups which have no category).
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4

VALID_TYPES = {"sudden_drop", "sudden_spike", "slow_drift", "flatline"}


@dataclass
class Anomaly:
    anomaly_type: str
    metric: str
    category: Optional[str]          # None = applies to all categories of this metric
    start_time: datetime
    duration_minutes: int
    magnitude: float = 1.0           # meaning depends on anomaly_type; unused for flatline
    id: str = None

    def __post_init__(self):
        if self.anomaly_type not in VALID_TYPES:
            raise ValueError(f"Unknown anomaly_type '{self.anomaly_type}'. Valid: {VALID_TYPES}")
        if self.id is None:
            self.id = str(uuid4())[:8]

    @property
    def end_time(self) -> datetime:
        return self.start_time + timedelta(minutes=self.duration_minutes)

    def is_active_at(self, ts: datetime) -> bool:
        return self.start_time <= ts < self.end_time

    def applies_to(self, metric: str, category: Optional[str]) -> bool:
        if metric != self.metric:
            return False
        return self.category is None or self.category == category

    def multiplier_at(self, ts: datetime) -> float:
        """
        Return the multiplier to apply to the "normal" value at this
        timestamp. Only meaningful when is_active_at(ts) is True.
        """
        if self.anomaly_type == "sudden_drop":
            return self.magnitude
        if self.anomaly_type == "sudden_spike":
            return self.magnitude
        if self.anomaly_type == "flatline":
            return 0.0
        if self.anomaly_type == "slow_drift":
            elapsed = (ts - self.start_time).total_seconds()
            total = (self.end_time - self.start_time).total_seconds()
            progress = min(max(elapsed / total, 0.0), 1.0) if total > 0 else 1.0
            # linear interpolation from 1.0 (normal) to magnitude
            return 1.0 + (self.magnitude - 1.0) * progress
        raise ValueError(f"Unhandled anomaly_type '{self.anomaly_type}'")


class AnomalyEngine:
    """
    Holds scheduled anomalies and applies them to generator output.
    Expired anomalies are pruned lazily on each apply() call.
    """

    def __init__(self):
        self._anomalies: list[Anomaly] = []

    def schedule(
        self,
        anomaly_type: str,
        metric: str,
        start_time: datetime,
        duration_minutes: int,
        category: Optional[str] = None,
        magnitude: float = 1.0,
    ) -> Anomaly:
        anomaly = Anomaly(
            anomaly_type=anomaly_type,
            metric=metric,
            category=category,
            start_time=start_time,
            duration_minutes=duration_minutes,
            magnitude=magnitude,
        )
        self._anomalies.append(anomaly)
        return anomaly

    def active_at(self, ts: datetime) -> list[Anomaly]:
        return [a for a in self._anomalies if a.is_active_at(ts)]

    def apply(self, ts: datetime, metric: str, category: Optional[str], value: float) -> float:
        """
        Given a "normal" generated value, return the value after applying
        any currently-active anomalies that target this metric/category.
        If multiple anomalies match (unusual but possible), multipliers
        compound.
        """
        result = value
        for anomaly in self._anomalies:
            if anomaly.is_active_at(ts) and anomaly.applies_to(metric, category):
                result *= anomaly.multiplier_at(ts)
        return result

    def prune_expired(self, ts: datetime) -> None:
        """Drop anomalies that have fully ended, to keep the list small
        over a long-running process."""
        self._anomalies = [a for a in self._anomalies if a.end_time > ts]