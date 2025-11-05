import tempfile
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

from piggy.installment_plan import InstallmentPlan
from piggy.plan_manager import PlanManager


class TestPlanManager(unittest.TestCase):

    def setUp(self):
        """Set up test data with temporary directory"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.manager = PlanManager(storage_dir=self.temp_dir)

        self.sample_plan = InstallmentPlan.build(
            merchant_name="Test Store",
            total_amount=Decimal("1200.00"),
            purchase_date=date(2024, 1, 1),
            num_installments=4,
            days_between=30,
            first_payment_date=date(2024, 2, 1)
        )

    def tearDown(self):
        """Clean up temporary files"""
        if self.temp_dir.exists():
            for file in self.temp_dir.glob("*.json"):
                file.unlink()
            self.temp_dir.rmdir()

    def test_add_plan(self):
        """Test adding a plan to storage"""
        self.manager.add_plan("test_plan", self.sample_plan)
        self.assertIn("test_plan", self.manager.plans)
        self.assertEqual(self.manager.get_plan("test_plan"), self.sample_plan)

    def test_get_plan_existing(self):
        """Test retrieving an existing plan"""
        self.manager.add_plan("test_plan", self.sample_plan)
        retrieved = self.manager.get_plan("test_plan")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.merchant_name, "Test Store")

    def test_get_plan_nonexistent(self):
        """Test retrieving a nonexistent plan returns None"""
        result = self.manager.get_plan("nonexistent")
        self.assertIsNone(result)

    def test_remove_plan_existing(self):
        """Test removing an existing plan"""
        self.manager.add_plan("test_plan", self.sample_plan)
        result = self.manager.remove_plan("test_plan")
        self.assertTrue(result)
        self.assertIsNone(self.manager.get_plan("test_plan"))

    def test_remove_plan_nonexistent(self):
        """Test removing a nonexistent plan returns False"""
        result = self.manager.remove_plan("nonexistent")
        self.assertFalse(result)

    def test_list_plans_empty(self):
        """Test listing plans when empty"""
        plans = self.manager.list_plans()
        self.assertEqual(len(plans), 0)
        self.assertIsInstance(plans, dict)

    def test_list_plans_with_data(self):
        """Test listing plans with data"""
        self.manager.add_plan("plan1", self.sample_plan)
        self.manager.add_plan("plan2", self.sample_plan)
        plans = self.manager.list_plans()
        self.assertEqual(len(plans), 2)
        self.assertIn("plan1", plans)
        self.assertIn("plan2", plans)

    def test_has_plans_empty(self):
        """Test has_plans when empty"""
        self.assertFalse(self.manager.has_plans())

    def test_has_plans_with_data(self):
        """Test has_plans with data"""
        self.manager.add_plan("test_plan", self.sample_plan)
        self.assertTrue(self.manager.has_plans())

    def test_save_all_empty(self):
        """Test saving with no plans"""
        saved_count, errors = self.manager.save_all()
        self.assertEqual(saved_count, 0)
        self.assertEqual(len(errors), 0)

    def test_save_all_with_plans(self):
        """Test saving plans to disk"""
        self.manager.add_plan("plan1", self.sample_plan)
        self.manager.add_plan("plan2", self.sample_plan)

        saved_count, errors = self.manager.save_all()

        self.assertEqual(saved_count, 2)
        self.assertEqual(len(errors), 0)
        self.assertTrue((self.temp_dir / "plan1.json").exists())
        self.assertTrue((self.temp_dir / "plan2.json").exists())

    def test_load_all_empty_directory(self):
        """Test loading from empty directory"""
        loaded_count, errors = self.manager.load_all()
        self.assertEqual(loaded_count, 0)
        self.assertEqual(len(errors), 0)

    def test_load_all_nonexistent_directory(self):
        """Test loading from nonexistent directory"""
        manager = PlanManager(storage_dir=Path("/nonexistent/dir"))
        loaded_count, errors = manager.load_all()
        self.assertEqual(loaded_count, 0)
        self.assertEqual(len(errors), 0)

    def test_save_and_load_roundtrip(self):
        """Test saving and loading plans"""
        self.manager.add_plan("plan1", self.sample_plan)
        self.manager.add_plan("plan2", self.sample_plan)

        saved_count, save_errors = self.manager.save_all()
        self.assertEqual(saved_count, 2)
        self.assertEqual(len(save_errors), 0)

        new_manager = PlanManager(storage_dir=self.temp_dir)
        loaded_count, load_errors = new_manager.load_all()

        self.assertEqual(loaded_count, 2)
        self.assertEqual(len(load_errors), 0)
        self.assertTrue(new_manager.has_plans())
        self.assertIsNotNone(new_manager.get_plan("plan1"))
        self.assertIsNotNone(new_manager.get_plan("plan2"))

    def test_storage_dir_created(self):
        """Test that storage directory is created on save"""
        temp_path = Path(tempfile.mktemp())
        manager = PlanManager(storage_dir=temp_path)

        self.assertFalse(temp_path.exists())

        manager.add_plan("test", self.sample_plan)
        manager.save_all()

        self.assertTrue(temp_path.exists())
        self.assertTrue(temp_path.is_dir())

        for file in temp_path.glob("*.json"):
            file.unlink()
        temp_path.rmdir()


if __name__ == '__main__':
    unittest.main()
