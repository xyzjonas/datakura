from apps.warehouse.core.services.data_import.progress import ImportProgress


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def tracked(total_weight=100, min_interval=0.5):
    clock, snapshots = Clock(), []
    progress = ImportProgress(
        snapshots.append, total_weight, min_interval=min_interval, clock=clock
    )
    return progress, clock, snapshots


def test_percent_is_weighted_by_stage_size():
    progress, _, _ = tracked(total_weight=100)

    progress.begin_stage("big", weight=75)
    progress.set_total(10)
    progress.advance(4)
    assert progress.snapshot.percent == 30.0  # 75 * 4/10 of 100
    progress.advance(6)
    progress.end_stage()
    assert progress.snapshot.percent == 75.0

    progress.begin_stage("small", weight=25)
    progress.set_total(2)
    progress.advance(1)
    assert progress.snapshot.percent == 87.5
    progress.advance(1)
    progress.end_stage()
    progress.finish()

    snapshot = progress.snapshot
    assert (snapshot.percent, snapshot.phase) == (100.0, "done")


def test_snapshot_reports_stage_counts_and_phases():
    progress, _, snapshots = tracked()

    progress.begin_stage("products", weight=100)
    progress.set_phase("validating")
    progress.set_total(3)
    progress.advance(2)

    last = progress.snapshot
    assert (last.stage, last.phase) == ("products", "importing")
    assert (last.stage_done, last.stage_total) == (2, 3)
    assert [s.phase for s in snapshots[:3]] == ["parsing", "validating", "importing"]


def test_percent_never_exceeds_100_and_never_divides_by_zero():
    progress, _, _ = tracked(total_weight=10)
    progress.begin_stage("s", weight=10)
    progress.set_total(0)
    assert progress.snapshot.percent == 0.0

    progress.set_total(2)
    progress.advance(5)  # over-reporting must not break the scale
    assert progress.snapshot.percent == 100.0


def test_zero_total_weight_is_safe():
    progress, _, _ = tracked(total_weight=0)

    progress.begin_stage("s", weight=0)
    progress.set_total(1)
    progress.advance()

    assert progress.snapshot.percent == 0.0


def test_advance_is_throttled_but_structural_changes_are_not():
    progress, clock, snapshots = tracked(min_interval=1.0)
    progress.begin_stage("s", weight=10)
    progress.set_total(1000)
    baseline = len(snapshots)

    for _ in range(100):
        progress.advance()
    assert len(snapshots) == baseline  # within the interval of the forced emit

    clock.now += 1.1
    for _ in range(100):
        progress.advance()
    assert len(snapshots) == baseline + 1
    assert snapshots[-1].stage_done == 101

    progress.end_stage()
    assert len(snapshots) == baseline + 2  # forced


def test_works_without_a_sink():
    progress = ImportProgress()

    progress.begin_stage("s", weight=1)
    progress.set_total(2)
    progress.advance(2)
    progress.end_stage()
    progress.finish()

    assert progress.snapshot.percent == 100.0


def test_services_run_standalone_without_progress():
    # importers stay usable (e.g. from management commands) with no progress given
    from apps.warehouse.core.services.data_import.customer_import import (
        CustomerImportService,
    )

    assert CustomerImportService().import_from_json("[]").created_count == 0
