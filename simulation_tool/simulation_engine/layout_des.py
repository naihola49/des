"""
Discrete Event Simulation driven by the factory layout graph (FactoryLayout).

Jobs are created at sources, move along edges (with optional probabilistic routing
for rework), are processed at stations, wait in buffers, and exit at sinks.
Uses the layout's node params for interarrival and processing distributions.
"""

import heapq
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np

from .distributions import sample_time, sample_manual_weibull_time

try:
    from layout.model import FactoryLayout, NodeType
except ImportError:
    from simulation_tool.layout.model import FactoryLayout, NodeType


@dataclass(order=True)
class _Event:
    time: float
    kind: str = field(compare=False)
    node_id: str = field(compare=False)
    job_id: int = field(compare=False, default=0)

    def __init__(self, time: float, kind: str, node_id: str = "", job_id: int = 0):
        self.time = time
        self.kind = kind
        self.node_id = node_id
        self.job_id = job_id


def _make_rng(seed: Optional[int] = None) -> np.random.Generator:
    return np.random.default_rng(seed)


class LayoutSimulator:
    """
    One replication of the layout-based DES.
    Run with .run(duration, seed=...) then read .results.
    """

    SOURCE_EMIT = "source_emit"
    PROCESSING_END = "processing_end"
    REWORK_RELEASE = "rework_release"
    MANUAL_BREAK_END = "manual_break_end"

    def __init__(self, layout: FactoryLayout):
        self.layout = layout
        self.rng: Optional[np.random.Generator] = None
        self.clock = 0.0
        self._heap: List[_Event] = []
        self._job_counter = 0
        self._job_entered: Dict[int, float] = {}
        self._completed: List[float] = []  # cycle times
        self._node_queues: Dict[str, List[int]] = {}
        self._station_current: Dict[str, Optional[int]] = {}
        self._manual_current: Dict[str, Optional[int]] = {}
        self._rework_current: Dict[str, Optional[int]] = {}
        # For manual nodes, track time since the last break (in simulation hours).
        # For now, "last break" is initialized at simulation start -> future, change to actual estimate of breaks during sim time period
        self._manual_last_break_time: Dict[str, float] = {}
        self._manual_on_break: Dict[str, bool] = {}
        self._source_next_emit: Dict[str, float] = {}

        for n in layout.nodes:
            self._node_queues[n.id] = []
            if n.type == NodeType.STATION:
                self._station_current[n.id] = None
            elif n.type == NodeType.MANUAL:
                self._manual_current[n.id] = None
                self._manual_last_break_time[n.id] = 0.0
                self._manual_on_break[n.id] = False
            elif n.type == NodeType.REWORK:
                self._rework_current[n.id] = None

    def run(
        self,
        duration: float,
        seed: Optional[int] = None,
        warmup: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Run one replication until simulation time reaches duration.
        Returns metrics (throughput, avg_cycle_time, etc.) for jobs that reached a sink.
        """
        self.rng = _make_rng(seed)
        self.clock = 0.0
        self._job_counter = 0
        self._job_entered.clear()
        self._completed.clear()
        for k in self._node_queues:
            self._node_queues[k].clear()
        for k in self._station_current:
            self._station_current[k] = None
        for k in self._manual_current:
            self._manual_current[k] = None
        for k in self._rework_current:
            self._rework_current[k] = None
        for k in self._manual_last_break_time:
            self._manual_last_break_time[k] = 0.0
        for k in self._manual_on_break:
            self._manual_on_break[k] = False
        self._source_next_emit.clear()
        self._heap.clear()

        source_ids = self.layout.source_ids()
        if not source_ids:
            return self._empty_results()

        for sid in source_ids:
            node = self.layout.node_by_id(sid)
            if node and node.type == NodeType.SOURCE:
                t = sample_time(node.params, self.rng)
                self._source_next_emit[sid] = t
                heapq.heappush(self._heap, _Event(t, self.SOURCE_EMIT, sid, 0))

        while self._heap and self._heap[0].time <= duration:
            ev = heapq.heappop(self._heap)
            self.clock = ev.time
            if ev.kind == self.SOURCE_EMIT:
                self._do_source_emit(ev.node_id, duration)
            elif ev.kind == self.PROCESSING_END:
                self._do_processing_end(ev.node_id, ev.job_id)
            elif ev.kind == self.REWORK_RELEASE:
                self._do_rework_release(ev.node_id, ev.job_id)
            elif ev.kind == self.MANUAL_BREAK_END:
                self._do_manual_break_end(ev.node_id)

        return self._compute_results(duration, warmup)

    def _do_source_emit(self, source_id: str, duration: float) -> None:
        self._job_counter += 1
        job_id = self._job_counter
        self._job_entered[job_id] = self.clock
        next_id = self.layout.sample_next_node(source_id, self.rng)
        if next_id:
            self._push_job(job_id, next_id)
        next_t = self.clock + sample_time(
            self.layout.node_by_id(source_id).params, self.rng
        )
        if next_t <= duration:
            heapq.heappush(
                self._heap, _Event(next_t, self.SOURCE_EMIT, source_id, 0)
            )
        self._source_next_emit[source_id] = next_t

    def _do_processing_end(self, station_id: str, job_id: int) -> None:
        # A processing_end can correspond to either a regular station or a manual node.
        if station_id in self._station_current:
            self._station_current[station_id] = None
        if station_id in self._manual_current:
            self._manual_current[station_id] = None
        next_id = self.layout.sample_next_node(station_id, self.rng)
        if next_id:
            self._push_job(job_id, next_id)
        node = self.layout.node_by_id(station_id)
        # For manual nodes, optionally start a break instead of immediately taking
        # the next job, based on hours since the last break ended.
        if node and node.type == NodeType.MANUAL:
            params = node.params or {}
            interval = float(params.get("break_interval_hours", 0.0) or 0.0)
            duration = float(params.get("break_duration", 0.0) or 0.0)
            if (
                interval > 0.0
                and duration > 0.0
                and not self._manual_on_break.get(station_id, False)
            ):
                hours_since_last_break = max(
                    0.0, self.clock - self._manual_last_break_time.get(station_id, 0.0)
                )
                if hours_since_last_break >= interval:
                    # Start a break: operator is unavailable until MANUAL_BREAK_END.
                    self._manual_on_break[station_id] = True
                    end_t = self.clock + duration
                    heapq.heappush(
                        self._heap,
                        _Event(end_t, self.MANUAL_BREAK_END, station_id, 0),
                    )
                    return

        q = self._node_queues[station_id]
        if q:
            next_job = q.pop(0)
            if node and node.type == NodeType.MANUAL:
                self._start_manual_processing(station_id, next_job)
            else:
                self._start_processing(station_id, next_job)
        else:
            self._try_pull_from_upstream(station_id)

    def _do_rework_release(self, rework_id: str, job_id: int) -> None:
        self._rework_current[rework_id] = None
        next_id = self.layout.sample_next_node(rework_id, self.rng)
        if next_id:
            self._push_job(job_id, next_id)
        q = self._node_queues[rework_id]
        if q:
            next_job = q.pop(0)
            self._start_rework_delay(rework_id, next_job)

    def _push_job(self, job_id: int, node_id: str) -> None:
        node = self.layout.node_by_id(node_id)
        if not node:
            return
        if node.type == NodeType.SINK:
            if job_id in self._job_entered:
                self._completed.append(self.clock - self._job_entered[job_id])
            return
        if node.type == NodeType.STATION:
            self._node_queues[node_id].append(job_id)
            if self._station_current[node_id] is None:
                self._try_start_one_at_station(node_id)
            return
        if node.type == NodeType.MANUAL:
            self._node_queues[node_id].append(job_id)
            if (
                self._manual_current[node_id] is None
                and not self._manual_on_break.get(node_id, False)
            ):
                self._try_start_one_at_manual(node_id)
            return
        if node.type == NodeType.BUFFER:
            cap = node.params.get("capacity")
            if cap is not None and len(self._node_queues[node_id]) >= cap:
                return
            self._node_queues[node_id].append(job_id)
            self._drain_buffer(node_id)
            return
        if node.type == NodeType.REWORK:
            self._node_queues[node_id].append(job_id)
            if self._rework_current[node_id] is None:
                self._try_start_one_at_rework(node_id)
            return

    def _try_start_one_at_station(self, station_id: str) -> None:
        q = self._node_queues[station_id]
        if not q:
            self._try_pull_from_upstream(station_id)
            return
        job_id = q.pop(0)
        self._start_processing(station_id, job_id)

    def _try_start_one_at_manual(self, manual_id: str) -> None:
        if self._manual_on_break.get(manual_id, False):
            return
        q = self._node_queues[manual_id]
        if not q:
            self._try_pull_from_upstream(manual_id)
            return
        job_id = q.pop(0)
        self._start_manual_processing(manual_id, job_id)

    def _start_processing(self, station_id: str, job_id: int) -> None:
        node = self.layout.node_by_id(station_id)
        if not node or node.type != NodeType.STATION:
            return
        self._station_current[station_id] = job_id
        pt = sample_time(node.params, self.rng)
        end_t = self.clock + pt
        heapq.heappush(
            self._heap,
            _Event(end_t, self.PROCESSING_END, station_id, job_id),
        )

    def _start_manual_processing(self, manual_id: str, job_id: int) -> None:
        node = self.layout.node_by_id(manual_id)
        if not node or node.type != NodeType.MANUAL:
            return
        self._manual_current[manual_id] = job_id
        last_break = self._manual_last_break_time.get(manual_id, 0.0)
        hours_since_last_break = max(0.0, self.clock - last_break)
        pt = sample_manual_weibull_time(node.params, hours_since_last_break, self.rng)
        end_t = self.clock + pt
        heapq.heappush(
            self._heap,
            _Event(end_t, self.PROCESSING_END, manual_id, job_id),
        )

    def _do_manual_break_end(self, manual_id: str) -> None:
        # End of a manual operator's break; update last_break_time and try to
        # start processing the next waiting job (or pull from upstream).
        self._manual_on_break[manual_id] = False
        self._manual_last_break_time[manual_id] = self.clock
        self._try_start_one_at_manual(manual_id)

    def _try_pull_from_upstream(self, node_id: str) -> None:
        for e in self.layout.edges_to(node_id):
            from_id = e.from_id
            q = self._node_queues.get(from_id, [])
            if not q:
                continue
            job_id = q.pop(0)
            self._push_job(job_id, node_id)
            return

    def _drain_buffer(self, buffer_id: str) -> None:
        for e in self.layout.edges_from(buffer_id):
            to_id = e.to_id
            q = self._node_queues.get(buffer_id, [])
            if not q:
                return
            job_id = q.pop(0)
            self._push_job(job_id, to_id)
            return

    def _try_start_one_at_rework(self, rework_id: str) -> None:
        q = self._node_queues[rework_id]
        if not q:
            return
        job_id = q.pop(0)
        self._start_rework_delay(rework_id, job_id)

    def _start_rework_delay(self, rework_id: str, job_id: int) -> None:
        node = self.layout.node_by_id(rework_id)
        delay = 0.0
        if node and node.params:
            delay = float(node.params.get("delay", 0.0))
        if delay <= 0:
            delay = 1e-6
        self._rework_current[rework_id] = job_id
        end_t = self.clock + delay
        heapq.heappush(
            self._heap,
            _Event(end_t, self.REWORK_RELEASE, rework_id, job_id),
        )

    def _compute_results(
        self, duration: float, warmup: float
    ) -> Dict[str, Any]:
        cycle_times = [c for c in self._completed if c >= 0]
        if warmup > 0 and self._job_entered:
            pass
        n = len(cycle_times)
        total_time = max(1e-9, duration - warmup)
        throughput = n / total_time if total_time > 0 else 0.0
        avg_cycle = float(np.mean(cycle_times)) if cycle_times else 0.0
        return {
            "throughput": throughput,
            "avg_cycle_time": avg_cycle,
            "total_completed": n,
            "cycle_times": cycle_times,
            "simulation_time": self.clock,
        }

    def _empty_results(self) -> Dict[str, Any]:
        return {
            "throughput": 0.0,
            "avg_cycle_time": 0.0,
            "total_completed": 0,
            "cycle_times": [],
            "simulation_time": 0.0,
        }
