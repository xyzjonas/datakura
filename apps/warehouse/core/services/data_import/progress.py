"""Progress reporting for long running imports"""

import time
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class ProgressSnapshot:
    stage: str | None
    phase: str | None
    stage_done: int
    stage_total: int
    percent: float


ProgressSink = Callable[[ProgressSnapshot], None]


class ImportProgress:
    """
    Tracks import progress as a weighted sum of stages (one per input file).

    The bundle declares the stages and their weights (input size in bytes), the
    individual importers only report `set_total` / `advance` for their records.
    The sink is throttled, so advancing per record is cheap.
    """

    def __init__(
        self,
        sink: ProgressSink | None = None,
        total_weight: float = 1.0,
        min_interval: float = 0.5,
        clock: Callable[[], float] = time.monotonic,
    ):
        self._sink = sink
        self._total_weight = max(total_weight, 1e-9)
        self._min_interval = min_interval
        self._clock = clock
        self._last_emit = float("-inf")

        self._finished_weight = 0.0
        self._stage: str | None = None
        self._stage_weight = 0.0
        self._phase: str | None = None
        self._done = 0
        self._total = 0

    @property
    def snapshot(self) -> ProgressSnapshot:
        fraction = min(self._done / self._total, 1.0) if self._total else 0.0
        weight = self._finished_weight + self._stage_weight * fraction
        return ProgressSnapshot(
            stage=self._stage,
            phase=self._phase,
            stage_done=self._done,
            stage_total=self._total,
            percent=round(min(weight / self._total_weight, 1.0) * 100, 1),
        )

    def begin_stage(self, label: str, weight: float) -> None:
        self._stage, self._stage_weight = label, weight
        self._done = self._total = 0
        self._phase = "parsing"
        self._emit(force=True)

    def set_phase(self, phase: str) -> None:
        self._phase = phase
        self._emit(force=True)

    def set_total(self, units: int) -> None:
        self._total, self._done = units, 0
        self._phase = "importing"
        self._emit(force=True)

    def advance(self, units: int = 1) -> None:
        self._done += units
        self._emit()

    def end_stage(self) -> None:
        self._finished_weight += self._stage_weight
        self._stage_weight = 0.0
        self._done = self._total
        self._emit(force=True)

    def finish(self) -> None:
        self._finished_weight = self._total_weight
        self._stage_weight = 0.0
        self._phase = "done"
        self._emit(force=True)

    def _emit(self, force: bool = False) -> None:
        if self._sink is None:
            return
        now = self._clock()
        if force or now - self._last_emit >= self._min_interval:
            self._last_emit = now
            self._sink(self.snapshot)
