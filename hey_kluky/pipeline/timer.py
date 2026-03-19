import time


class PipelineTimer:
    """Tracks timing for each stage of the voice pipeline."""

    def __init__(self):
        self._stages: list[tuple[str, float]] = []
        self._current_stage: str | None = None
        self._current_start: float = 0.0
        self._cycle_start: float = 0.0

    def start_cycle(self):
        self._stages = []
        self._current_stage = None
        self._cycle_start = time.perf_counter()

    def start(self, stage: str):
        self._end_current()
        self._current_stage = stage
        self._current_start = time.perf_counter()

    def stop(self):
        self._end_current()

    def _end_current(self):
        if self._current_stage is not None:
            elapsed = time.perf_counter() - self._current_start
            self._stages.append((self._current_stage, elapsed))
            self._current_stage = None

    def print_summary(self):
        self._end_current()
        if not self._stages:
            return

        total = time.perf_counter() - self._cycle_start
        name_width = max(len(name) for name, _ in self._stages)
        name_width = max(name_width, 5)  # minimum width

        border = f"+-{'-' * name_width}-+----------+"
        print(border)
        print(f"| {'Stage':<{name_width}} | Time (s) |")
        print(border)
        for name, elapsed in self._stages:
            print(f"| {name:<{name_width}} | {elapsed:>8.2f} |")
        print(border)
        print(f"| {'TOTAL':<{name_width}} | {total:>8.2f} |")
        print(border)


timer = PipelineTimer()
