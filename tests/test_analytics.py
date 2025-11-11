import unittest
from datetime import date
from decimal import Decimal

from piggy.analytics import (
    filter_plans_by_amount,
    filter_plans_by_date,
    filter_plans_by_merchant,
    filter_plans_by_status,
)
from piggy.installment_plan import InstallmentPlan, PaymentStatus


class TestFilterPlansByMerchant(unittest.TestCase):
    def setUp(self):
        """Set up test plans"""
        self.plans = {
            "plan1": InstallmentPlan.build(
                merchant_name="Apple Store",
                total_amount=Decimal("1200.00"),
                purchase_date=date(2024, 1, 1),
                num_installments=4,
                days_between=30,
                first_payment_date=date(2024, 2, 1),
            ),
            "plan2": InstallmentPlan.build(
                merchant_name="Best Buy",
                total_amount=Decimal("900.00"),
                purchase_date=date(2024, 1, 15),
                num_installments=3,
                days_between=30,
                first_payment_date=date(2024, 2, 15),
            ),
            "plan3": InstallmentPlan.build(
                merchant_name="Amazon",
                total_amount=Decimal("500.00"),
                purchase_date=date(2024, 2, 1),
                num_installments=2,
                days_between=30,
                first_payment_date=date(2024, 3, 1),
            ),
        }

    def test_exact_match(self):
        """Test exact merchant name match"""
        result = filter_plans_by_merchant(self.plans, "Apple Store")
        self.assertEqual(len(result), 1)
        self.assertIn("plan1", result)

    def test_partial_match(self):
        """Test partial merchant name match"""
        result = filter_plans_by_merchant(self.plans, "Buy")
        self.assertEqual(len(result), 1)
        self.assertIn("plan2", result)

    def test_case_insensitive(self):
        """Test case-insensitive matching"""
        result = filter_plans_by_merchant(self.plans, "apple")
        self.assertEqual(len(result), 1)
        self.assertIn("plan1", result)

    def test_no_match(self):
        """Test no matching merchants"""
        result = filter_plans_by_merchant(self.plans, "Nonexistent Store")
        self.assertEqual(len(result), 0)

    def test_multiple_matches(self):
        """Test query matching multiple merchants"""
        result = filter_plans_by_merchant(self.plans, "A")
        self.assertEqual(len(result), 2)
        self.assertIn("plan1", result)
        self.assertIn("plan3", result)

    def test_empty_query(self):
        """Test empty query returns all plans"""
        result = filter_plans_by_merchant(self.plans, "")
        self.assertEqual(len(result), 3)


class TestFilterPlansByStatus(unittest.TestCase):
    def setUp(self):
        """Set up test plans with different statuses"""
        self.plans = {
            "plan1": InstallmentPlan.build(
                merchant_name="Store A",
                total_amount=Decimal("300.00"),
                purchase_date=date(2024, 1, 1),
                num_installments=3,
                days_between=30,
                first_payment_date=date(2024, 2, 1),
            ),
            "plan2": InstallmentPlan.build(
                merchant_name="Store B",
                total_amount=Decimal("400.00"),
                purchase_date=date(2024, 1, 1),
                num_installments=2,
                days_between=30,
                first_payment_date=date(2024, 1, 5),
            ),
            "plan3": InstallmentPlan.build(
                merchant_name="Store C",
                total_amount=Decimal("500.00"),
                purchase_date=date(2024, 1, 1),
                num_installments=2,
                days_between=30,
                first_payment_date=date(2024, 3, 1),
            ),
        }

        # Mark plan1 as fully paid
        for inst in self.plans["plan1"].installments:
            inst.mark_full_payment(date(2024, 2, 1))

        # Mark plan2 installments as overdue
        for inst in self.plans["plan2"].installments:
            inst.status = PaymentStatus.OVERDUE

    def test_filter_fully_paid_true(self):
        """Test filtering for fully paid plans"""
        result = filter_plans_by_status(self.plans, fully_paid=True)
        self.assertEqual(len(result), 1)
        self.assertIn("plan1", result)

    def test_filter_fully_paid_false(self):
        """Test filtering for unpaid plans"""
        result = filter_plans_by_status(self.plans, fully_paid=False)
        self.assertEqual(len(result), 2)
        self.assertIn("plan2", result)
        self.assertIn("plan3", result)

    def test_filter_has_overdue_true(self):
        """Test filtering for plans with overdue payments"""
        result = filter_plans_by_status(self.plans, has_overdue=True)
        # Both plan2 (manually marked) and plan3 (old dates) have overdue payments
        self.assertEqual(len(result), 2)
        self.assertIn("plan2", result)
        self.assertIn("plan3", result)

    def test_filter_has_overdue_false(self):
        """Test filtering for plans without overdue payments"""
        result = filter_plans_by_status(self.plans, has_overdue=False)
        # Only plan1 (fully paid) has no overdue
        self.assertEqual(len(result), 1)
        self.assertIn("plan1", result)

    def test_filter_combined(self):
        """Test combining fully_paid and has_overdue filters"""
        result = filter_plans_by_status(self.plans, fully_paid=False, has_overdue=False)
        # No plans are both unpaid and without overdue
        self.assertEqual(len(result), 0)

    def test_no_filters(self):
        """Test with no filters returns all plans"""
        result = filter_plans_by_status(self.plans)
        self.assertEqual(len(result), 3)


class TestFilterPlansByAmount(unittest.TestCase):
    def setUp(self):
        """Set up test plans with different amounts"""
        self.plans = {
            "plan1": InstallmentPlan.build(
                merchant_name="Store A",
                total_amount=Decimal("500.00"),
                purchase_date=date(2024, 1, 1),
                num_installments=2,
                days_between=30,
                first_payment_date=date(2024, 2, 1),
            ),
            "plan2": InstallmentPlan.build(
                merchant_name="Store B",
                total_amount=Decimal("1000.00"),
                purchase_date=date(2024, 1, 1),
                num_installments=4,
                days_between=30,
                first_payment_date=date(2024, 2, 1),
            ),
            "plan3": InstallmentPlan.build(
                merchant_name="Store C",
                total_amount=Decimal("1500.00"),
                purchase_date=date(2024, 1, 1),
                num_installments=3,
                days_between=30,
                first_payment_date=date(2024, 2, 1),
            ),
        }

        # Mark first installment of plan2 as paid
        self.plans["plan2"].installments[0].mark_full_payment(date(2024, 2, 1))

    def test_filter_min_total(self):
        """Test filtering by minimum total amount"""
        result = filter_plans_by_amount(self.plans, min_total=Decimal("1000.00"))
        self.assertEqual(len(result), 2)
        self.assertIn("plan2", result)
        self.assertIn("plan3", result)

    def test_filter_max_total(self):
        """Test filtering by maximum total amount"""
        result = filter_plans_by_amount(self.plans, max_total=Decimal("1000.00"))
        self.assertEqual(len(result), 2)
        self.assertIn("plan1", result)
        self.assertIn("plan2", result)

    def test_filter_total_range(self):
        """Test filtering by total amount range"""
        result = filter_plans_by_amount(self.plans, min_total=Decimal("600.00"), max_total=Decimal("1200.00"))
        self.assertEqual(len(result), 1)
        self.assertIn("plan2", result)

    def test_filter_min_remaining(self):
        """Test filtering by minimum remaining balance"""
        result = filter_plans_by_amount(self.plans, min_remaining=Decimal("1000.00"))
        self.assertEqual(len(result), 1)
        self.assertIn("plan3", result)

    def test_filter_max_remaining(self):
        """Test filtering by maximum remaining balance"""
        result = filter_plans_by_amount(self.plans, max_remaining=Decimal("600.00"))
        self.assertEqual(len(result), 1)
        self.assertIn("plan1", result)

    def test_filter_remaining_range(self):
        """Test filtering by remaining balance range"""
        result = filter_plans_by_amount(self.plans, min_remaining=Decimal("500.00"), max_remaining=Decimal("800.00"))
        self.assertEqual(len(result), 2)
        self.assertIn("plan1", result)
        self.assertIn("plan2", result)

    def test_filter_combined(self):
        """Test combining total and remaining filters"""
        result = filter_plans_by_amount(self.plans, min_total=Decimal("900.00"), max_remaining=Decimal("800.00"))
        self.assertEqual(len(result), 1)
        self.assertIn("plan2", result)

    def test_no_filters(self):
        """Test with no filters returns all plans"""
        result = filter_plans_by_amount(self.plans)
        self.assertEqual(len(result), 3)


class TestFilterPlansByDate(unittest.TestCase):
    def setUp(self):
        """Set up test plans with different dates"""
        self.plans = {
            "plan1": InstallmentPlan.build(
                merchant_name="Store A",
                total_amount=Decimal("300.00"),
                purchase_date=date(2024, 1, 1),
                num_installments=3,
                days_between=30,
                first_payment_date=date(2024, 2, 1),
            ),
            "plan2": InstallmentPlan.build(
                merchant_name="Store B",
                total_amount=Decimal("400.00"),
                purchase_date=date(2024, 2, 15),
                num_installments=2,
                days_between=30,
                first_payment_date=date(2024, 3, 15),
            ),
            "plan3": InstallmentPlan.build(
                merchant_name="Store C",
                total_amount=Decimal("500.00"),
                purchase_date=date(2024, 3, 1),
                num_installments=2,
                days_between=30,
                first_payment_date=date(2024, 4, 1),
            ),
        }

        # Mark first payment of plan1 as paid
        self.plans["plan1"].installments[0].mark_full_payment(date(2024, 2, 1))

    def test_filter_purchase_after(self):
        """Test filtering by purchase date after"""
        result = filter_plans_by_date(self.plans, purchase_after=date(2024, 2, 1))
        self.assertEqual(len(result), 2)
        self.assertIn("plan2", result)
        self.assertIn("plan3", result)

    def test_filter_purchase_before(self):
        """Test filtering by purchase date before"""
        result = filter_plans_by_date(self.plans, purchase_before=date(2024, 2, 1))
        self.assertEqual(len(result), 1)
        self.assertIn("plan1", result)

    def test_filter_purchase_range(self):
        """Test filtering by purchase date range"""
        result = filter_plans_by_date(self.plans, purchase_after=date(2024, 1, 15), purchase_before=date(2024, 2, 20))
        self.assertEqual(len(result), 1)
        self.assertIn("plan2", result)

    def test_filter_next_payment_after(self):
        """Test filtering by next payment date after"""
        result = filter_plans_by_date(self.plans, next_payment_after=date(2024, 3, 15))
        self.assertEqual(len(result), 2)
        self.assertIn("plan2", result)
        self.assertIn("plan3", result)

    def test_filter_next_payment_before(self):
        """Test filtering by next payment date before"""
        result = filter_plans_by_date(self.plans, next_payment_before=date(2024, 3, 14))
        self.assertEqual(len(result), 1)
        self.assertIn("plan1", result)

    def test_filter_next_payment_range(self):
        """Test filtering by next payment date range"""
        result = filter_plans_by_date(
            self.plans, next_payment_after=date(2024, 3, 1), next_payment_before=date(2024, 3, 31)
        )
        self.assertEqual(len(result), 2)
        self.assertIn("plan1", result)
        self.assertIn("plan2", result)

    def test_filter_no_next_payment(self):
        """Test filtering when plan has no next payment"""
        # Mark all installments as paid for plan1
        for inst in self.plans["plan1"].installments:
            inst.mark_full_payment(date(2024, 2, 1))

        result = filter_plans_by_date(self.plans, next_payment_after=date(2024, 2, 1))
        # plan1 should be excluded because it has no next payment
        self.assertEqual(len(result), 2)
        self.assertIn("plan2", result)
        self.assertIn("plan3", result)

    def test_no_filters(self):
        """Test with no filters returns all plans"""
        result = filter_plans_by_date(self.plans)
        self.assertEqual(len(result), 3)


if __name__ == "__main__":
    unittest.main()
