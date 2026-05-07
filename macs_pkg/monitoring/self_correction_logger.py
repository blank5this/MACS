"""Self-correction event logger — formats correction events for console output."""

from __future__ import annotations

import logging

from .event_bus import Event, EventType, get_event_bus

logger = logging.getLogger("self_correction")


class SelfCorrectionLogger:
    """Subscribes to self-correction events and emits formatted log lines.

    Attach to the global event bus::

        logger = SelfCorrectionLogger()
        logger.attach()
    """

    def attach(self, bus=None) -> None:
        if bus is None:
            bus = get_event_bus()
        bus.subscribe(self._handle, EventType.CORRECTION_ATTEMPT_STARTED)
        bus.subscribe(self._handle, EventType.CORRECTION_QUALITY_EVALUATED)
        bus.subscribe(self._handle, EventType.CORRECTION_COMPLETED)

    async def _handle(self, event: Event) -> None:
        t = event.type
        d = event.data
        task_id = d.get("task_id", "?")
        ts = event.timestamp.strftime("%H:%M:%S.%f")[:-3]

        if t == EventType.CORRECTION_ATTEMPT_STARTED:
            fb = " [with feedback]" if d["has_feedback"] else ""
            logger.info(
                f"[{ts}] [Correction] Task={task_id} "
                f"Attempt={d['attempt']}/{d['max_attempts']}{fb} started"
            )

        elif t == EventType.CORRECTION_QUALITY_EVALUATED:
            status = "PASS" if d["passed"] else "FAIL"
            logger.info(
                f"[{ts}] [Correction] Task={task_id} Attempt={d['attempt']} "
                f"quality_score={d['quality_score']:.2f} ({status})"
            )

        elif t == EventType.CORRECTION_COMPLETED:
            status = "SUCCESS" if d["success"] else "FAILED"
            extra = f" error={d['error']}" if not d["success"] else ""
            if d.get("quality_score") is not None:
                extra += f" final_quality_score={d['quality_score']:.2f}"
            logger.info(
                f"[{ts}] [Correction] Task={task_id} {status} "
                f"total_attempts={d['total_attempts']}{extra}"
            )