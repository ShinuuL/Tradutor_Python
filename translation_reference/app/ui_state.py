from dataclasses import dataclass, field
from enum import Enum


class Stage(str, Enum):
    PREPARE = "prepare"
    TRANSLATE = "translate"
    REVIEW = "review"
    APPLY = "apply"


class StageStatus(str, Enum):
    LOCKED = "locked"
    READY = "ready"
    RUNNING = "running"
    COMPLETE = "complete"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class WorkflowState:
    _statuses: dict = field(default_factory=lambda: {
        Stage.PREPARE: StageStatus.READY,
        Stage.TRANSLATE: StageStatus.LOCKED,
        Stage.REVIEW: StageStatus.LOCKED,
        Stage.APPLY: StageStatus.LOCKED,
    })

    def status(self, stage):
        return self._statuses[stage]

    def can_open(self, stage):
        return self.status(stage) is not StageStatus.LOCKED

    def requirement(self, stage):
        messages = {
            Stage.TRANSLATE: "Conclua uma varredura para continuar.",
            Stage.REVIEW: "Conclua uma tradução para revisar os resultados.",
            Stage.APPLY: "Conclua uma tradução válida antes de aplicar.",
        }
        return messages.get(stage, "")

    def mark_scan_started(self):
        self._statuses[Stage.PREPARE] = StageStatus.RUNNING

    def mark_scan_finished(self, success):
        self._statuses[Stage.PREPARE] = StageStatus.COMPLETE if success else StageStatus.ERROR
        if success:
            self._statuses[Stage.TRANSLATE] = StageStatus.READY

    def mark_translation_started(self):
        self._statuses[Stage.TRANSLATE] = StageStatus.RUNNING

    def mark_translation_finished(self, success, has_review):
        self._statuses[Stage.TRANSLATE] = StageStatus.COMPLETE if success else StageStatus.ERROR
        if success and has_review:
            self._statuses[Stage.REVIEW] = StageStatus.READY
            self._statuses[Stage.APPLY] = StageStatus.READY

    def mark_apply_finished(self, success):
        self._statuses[Stage.APPLY] = StageStatus.COMPLETE if success else StageStatus.ERROR

    def mark_retry_finished(self, success, has_remaining):
        """Record a retry result without changing the already-valid apply stage."""
        if not success:
            self._statuses[Stage.REVIEW] = StageStatus.ERROR
        elif has_remaining:
            self._statuses[Stage.REVIEW] = StageStatus.WARNING
        else:
            self._statuses[Stage.REVIEW] = StageStatus.READY
