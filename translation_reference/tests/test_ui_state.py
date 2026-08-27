import sys
import unittest
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP_DIR))

from ui_state import Stage, StageStatus, WorkflowState


class WorkflowStateTests(unittest.TestCase):
    def test_initial_state_only_prepare_is_ready(self):
        state = WorkflowState()
        self.assertIs(state.status(Stage.PREPARE), StageStatus.READY)
        self.assertIs(state.status(Stage.TRANSLATE), StageStatus.LOCKED)
        self.assertIs(state.status(Stage.REVIEW), StageStatus.LOCKED)
        self.assertIs(state.status(Stage.APPLY), StageStatus.LOCKED)
        self.assertEqual(state.requirement(Stage.TRANSLATE), "Conclua uma varredura para continuar.")

    def test_successful_scan_unlocks_translation(self):
        state = WorkflowState()
        state.mark_scan_started()
        self.assertIs(state.status(Stage.PREPARE), StageStatus.RUNNING)
        state.mark_scan_finished(success=True)
        self.assertIs(state.status(Stage.PREPARE), StageStatus.COMPLETE)
        self.assertIs(state.status(Stage.TRANSLATE), StageStatus.READY)

    def test_translation_with_review_unlocks_review_and_apply(self):
        state = WorkflowState()
        state.mark_scan_finished(success=True)
        state.mark_translation_started()
        self.assertIs(state.status(Stage.TRANSLATE), StageStatus.RUNNING)
        state.mark_translation_finished(success=True, has_review=True)
        self.assertIs(state.status(Stage.TRANSLATE), StageStatus.COMPLETE)
        self.assertIs(state.status(Stage.REVIEW), StageStatus.READY)
        self.assertIs(state.status(Stage.APPLY), StageStatus.READY)

    def test_failed_operation_stays_recoverable(self):
        state = WorkflowState()
        state.mark_scan_started()
        state.mark_scan_finished(success=False)
        self.assertIs(state.status(Stage.PREPARE), StageStatus.ERROR)
        self.assertTrue(state.can_open(Stage.PREPARE))
        self.assertFalse(state.can_open(Stage.TRANSLATE))

    def test_failed_translation_is_recoverable(self):
        state = WorkflowState()
        state.mark_scan_finished(success=True)
        state.mark_translation_started()
        state.mark_translation_finished(success=False, has_review=False)
        self.assertIs(state.status(Stage.TRANSLATE), StageStatus.ERROR)
        self.assertTrue(state.can_open(Stage.TRANSLATE))

    def test_successful_translation_without_review_keeps_later_stages_locked(self):
        state = WorkflowState()
        state.mark_scan_finished(success=True)
        state.mark_translation_finished(success=True, has_review=False)
        self.assertIs(state.status(Stage.REVIEW), StageStatus.LOCKED)
        self.assertIs(state.status(Stage.APPLY), StageStatus.LOCKED)

    def test_apply_success_and_failure_statuses(self):
        state = WorkflowState()
        state.mark_apply_finished(success=False)
        self.assertIs(state.status(Stage.APPLY), StageStatus.ERROR)
        state.mark_apply_finished(success=True)
        self.assertIs(state.status(Stage.APPLY), StageStatus.COMPLETE)

    def test_retry_result_updates_review_without_relocking_apply(self):
        state = WorkflowState()
        state.mark_scan_finished(success=True)
        state.mark_translation_finished(success=True, has_review=True)

        state.mark_retry_finished(success=True, has_remaining=True)
        self.assertIs(state.status(Stage.REVIEW), StageStatus.WARNING)
        self.assertIs(state.status(Stage.APPLY), StageStatus.READY)

        state.mark_retry_finished(success=True, has_remaining=False)
        self.assertIs(state.status(Stage.REVIEW), StageStatus.READY)
        self.assertIs(state.status(Stage.APPLY), StageStatus.READY)

        state.mark_retry_finished(success=False, has_remaining=True)
        self.assertIs(state.status(Stage.REVIEW), StageStatus.ERROR)
        self.assertIs(state.status(Stage.APPLY), StageStatus.READY)

    def test_requirements_describe_locked_stages(self):
        state = WorkflowState()
        self.assertEqual(state.requirement(Stage.REVIEW), "Conclua uma tradução para revisar os resultados.")
        self.assertEqual(state.requirement(Stage.APPLY), "Conclua uma tradução válida antes de aplicar.")
        self.assertEqual(state.requirement(Stage.PREPARE), "")


if __name__ == "__main__":
    unittest.main()
