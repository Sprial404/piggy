from pathlib import Path
from typing import Optional

from piggy.installment_plan import InstallmentPlan


class PlanManager:
    """
    Manages installment plan storage and persistence.

    Encapsulates plan storage and file I/O operations, removing the need
    for global state.
    """

    def __init__(self, storage_dir: Path = Path("data")):
        """
        Initialize the plan manager.

        :param storage_dir: Directory for saving/loading plan files
        """
        self.storage_dir = storage_dir
        self.plans: dict[str, InstallmentPlan] = {}

    def add_plan(self, plan_id: str, plan: InstallmentPlan) -> None:
        """
        Add a plan to storage.

        :param plan_id: Unique identifier for the plan
        :param plan: InstallmentPlan instance to store
        """
        self.plans[plan_id] = plan

    def get_plan(self, plan_id: str) -> Optional[InstallmentPlan]:
        """
        Retrieve a plan by ID.

        :param plan_id: Plan identifier
        :return: InstallmentPlan if found, None otherwise
        """
        return self.plans.get(plan_id)

    def remove_plan(self, plan_id: str) -> bool:
        """
        Remove a plan from storage.

        :param plan_id: Plan identifier
        :return: True if plan was removed, False if not found
        """
        if plan_id in self.plans:
            del self.plans[plan_id]
            return True
        return False

    def list_plans(self) -> dict[str, InstallmentPlan]:
        """
        Get all plans.

        :return: Dictionary of plan_id -> InstallmentPlan
        """
        return self.plans

    def has_plans(self) -> bool:
        """
        Check if any plans are stored.

        :return: True if plans exist, False otherwise
        """
        return len(self.plans) > 0

    def save_all(self) -> tuple[int, list[str]]:
        """
        Save all plans to disk.

        :return: Tuple of (saved_count, error_messages)
        """
        self.storage_dir.mkdir(exist_ok=True)
        saved_count = 0
        errors = []

        for plan_id, plan in self.plans.items():
            try:
                file_path = self.storage_dir / f"{plan_id}.json"
                plan.to_json(str(file_path))
                saved_count += 1
            except Exception as e:
                errors.append(f"Error saving {plan_id}: {e}")

        return saved_count, errors

    def load_all(self) -> tuple[int, list[str]]:
        """
        Load all plans from disk.

        :return: Tuple of (loaded_count, error_messages)
        """
        if not self.storage_dir.exists():
            return 0, []

        json_files = list(self.storage_dir.glob("*.json"))
        if not json_files:
            return 0, []

        loaded_count = 0
        errors = []

        for file_path in json_files:
            try:
                plan = InstallmentPlan.from_json_file(str(file_path))
                plan_id = file_path.stem
                self.plans[plan_id] = plan
                loaded_count += 1
            except Exception as e:
                errors.append(f"Error loading {file_path.name}: {e}")

        return loaded_count, errors
