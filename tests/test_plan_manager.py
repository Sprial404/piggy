"""
Pytest tests for PlanManager functionality.
"""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from piggy.installment_plan import InstallmentPlan
from piggy.plan_manager import PlanManager


@pytest.fixture
def sample_plan():
    """Create a sample installment plan for testing."""
    return InstallmentPlan.build(
        merchant_name="Test Store",
        total_amount=Decimal("1200.00"),
        purchase_date=date(2024, 1, 1),
        num_installments=4,
        days_between=30,
        first_payment_date=date(2024, 2, 1),
    )


@pytest.fixture
def plan_manager(tmp_path):
    """Create a plan manager with temporary storage directory."""
    return PlanManager(storage_dir=tmp_path)


@pytest.mark.unit
class TestPlanManager:
    """Tests for PlanManager plan storage and retrieval."""

    def test_add_plan(self, plan_manager, sample_plan):
        """Test adding a plan to storage."""
        plan_manager.add_plan("test_plan", sample_plan)
        assert "test_plan" in plan_manager.plans
        assert plan_manager.get_plan("test_plan") == sample_plan

    def test_get_plan_existing(self, plan_manager, sample_plan):
        """Test retrieving an existing plan."""
        plan_manager.add_plan("test_plan", sample_plan)
        retrieved = plan_manager.get_plan("test_plan")
        assert retrieved is not None
        assert retrieved.merchant_name == "Test Store"

    def test_get_plan_nonexistent(self, plan_manager):
        """Test retrieving a nonexistent plan returns None."""
        result = plan_manager.get_plan("nonexistent")
        assert result is None

    def test_remove_plan_existing(self, plan_manager, sample_plan):
        """Test removing an existing plan."""
        plan_manager.add_plan("test_plan", sample_plan)
        result = plan_manager.remove_plan("test_plan")
        assert result is True
        assert plan_manager.get_plan("test_plan") is None

    def test_remove_plan_nonexistent(self, plan_manager):
        """Test removing a nonexistent plan returns False."""
        result = plan_manager.remove_plan("nonexistent")
        assert result is False

    def test_list_plans_empty(self, plan_manager):
        """Test listing plans when empty."""
        plans = plan_manager.list_plans()
        assert len(plans) == 0
        assert isinstance(plans, dict)

    def test_list_plans_with_data(self, plan_manager, sample_plan):
        """Test listing plans with data."""
        plan_manager.add_plan("plan1", sample_plan)
        plan_manager.add_plan("plan2", sample_plan)
        plans = plan_manager.list_plans()
        assert len(plans) == 2
        assert "plan1" in plans
        assert "plan2" in plans

    def test_has_plans_empty(self, plan_manager):
        """Test has_plans when empty."""
        assert plan_manager.has_plans() is False

    def test_has_plans_with_data(self, plan_manager, sample_plan):
        """Test has_plans with data."""
        plan_manager.add_plan("test_plan", sample_plan)
        assert plan_manager.has_plans() is True


@pytest.mark.unit
class TestPlanManagerPersistence:
    """Tests for PlanManager file persistence operations."""

    def test_save_all_empty(self, plan_manager):
        """Test saving with no plans."""
        saved_count, errors = plan_manager.save_all()
        assert saved_count == 0
        assert len(errors) == 0

    def test_save_all_with_plans(self, plan_manager, sample_plan, tmp_path):
        """Test saving plans to disk."""
        plan_manager.add_plan("plan1", sample_plan)
        plan_manager.add_plan("plan2", sample_plan)

        saved_count, errors = plan_manager.save_all()

        assert saved_count == 2
        assert len(errors) == 0
        assert (tmp_path / "plan1.json").exists()
        assert (tmp_path / "plan2.json").exists()

    def test_load_all_empty_directory(self, plan_manager):
        """Test loading from empty directory."""
        loaded_count, errors = plan_manager.load_all()
        assert loaded_count == 0
        assert len(errors) == 0

    def test_load_all_nonexistent_directory(self):
        """Test loading from nonexistent directory."""
        manager = PlanManager(storage_dir=Path("/nonexistent/dir"))
        loaded_count, errors = manager.load_all()
        assert loaded_count == 0
        assert len(errors) == 0

    def test_save_and_load_roundtrip(self, sample_plan, tmp_path):
        """Test saving and loading plans."""
        manager = PlanManager(storage_dir=tmp_path)
        manager.add_plan("plan1", sample_plan)
        manager.add_plan("plan2", sample_plan)

        saved_count, save_errors = manager.save_all()
        assert saved_count == 2
        assert len(save_errors) == 0

        new_manager = PlanManager(storage_dir=tmp_path)
        loaded_count, load_errors = new_manager.load_all()

        assert loaded_count == 2
        assert len(load_errors) == 0
        assert new_manager.has_plans()
        assert new_manager.get_plan("plan1") is not None
        assert new_manager.get_plan("plan2") is not None

    def test_storage_dir_created(self, sample_plan, tmp_path):
        """Test that storage directory is created on save."""
        temp_path = tmp_path / "new_dir"
        manager = PlanManager(storage_dir=temp_path)

        assert not temp_path.exists()

        manager.add_plan("test", sample_plan)
        manager.save_all()

        assert temp_path.exists()
        assert temp_path.is_dir()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
