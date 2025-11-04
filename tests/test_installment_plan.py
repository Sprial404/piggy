import unittest
from datetime import date, timedelta
from decimal import Decimal

from piggy.installment_plan import build_installment_plan, PaymentStatus


class TestBuildInstallmentPlan(unittest.TestCase):

    def test_build_plan_with_equal_installments(self):
        """Test building a plan with evenly divided installments"""
        plan = build_installment_plan(
            merchant_name="Test Store",
            total_amount=Decimal("1200.00"),
            purchase_date=date(2024, 1, 1),
            num_installments=4,
            days_between=30,
            first_payment_date=date(2024, 2, 1)
        )

        self.assertEqual(plan.merchant_name, "Test Store")
        self.assertEqual(plan.total_amount, Decimal("1200.00"))
        self.assertEqual(plan.purchase_date, date(2024, 1, 1))
        self.assertEqual(len(plan.installments), 4)

        expected_amount = Decimal("300.00")
        for inst in plan.installments:
            self.assertEqual(inst.amount, expected_amount)
            self.assertEqual(inst.status, PaymentStatus.PENDING)

    def test_installment_dates_are_sequential(self):
        """Test that installment due dates are correctly spaced"""
        plan = build_installment_plan(
            merchant_name="Test Store",
            total_amount=Decimal("600.00"),
            purchase_date=date(2024, 1, 1),
            num_installments=3,
            days_between=14,
            first_payment_date=date(2024, 1, 15)
        )

        expected_dates = [
            date(2024, 1, 15),
            date(2024, 1, 29),
            date(2024, 2, 12)
        ]

        for i, inst in enumerate(plan.installments):
            self.assertEqual(inst.due_date, expected_dates[i])

    def test_installment_numbers_are_sequential(self):
        """Test that installment numbers start at 1 and increment"""
        plan = build_installment_plan(
            merchant_name="Test Store",
            total_amount=Decimal("500.00"),
            purchase_date=date(2024, 1, 1),
            num_installments=5,
            days_between=7,
            first_payment_date=date(2024, 1, 8)
        )

        for i, inst in enumerate(plan.installments, start=1):
            self.assertEqual(inst.installment_number, i)

    def test_single_installment(self):
        """Test building a plan with a single installment"""
        plan = build_installment_plan(
            merchant_name="Test Store",
            total_amount=Decimal("250.00"),
            purchase_date=date(2024, 1, 1),
            num_installments=1,
            days_between=30,
            first_payment_date=date(2024, 2, 1)
        )

        self.assertEqual(len(plan.installments), 1)
        self.assertEqual(plan.installments[0].amount, Decimal("250.00"))
        self.assertEqual(plan.installments[0].due_date, date(2024, 2, 1))

    def test_weekly_payment_schedule(self):
        """Test weekly payment frequency"""
        plan = build_installment_plan(
            merchant_name="Test Store",
            total_amount=Decimal("280.00"),
            purchase_date=date(2024, 1, 1),
            num_installments=4,
            days_between=7,
            first_payment_date=date(2024, 1, 8)
        )

        expected_dates = [
            date(2024, 1, 8),
            date(2024, 1, 15),
            date(2024, 1, 22),
            date(2024, 1, 29)
        ]

        for i, inst in enumerate(plan.installments):
            self.assertEqual(inst.due_date, expected_dates[i])

    def test_fortnightly_payment_schedule(self):
        """Test fortnightly payment frequency"""
        plan = build_installment_plan(
            merchant_name="Test Store",
            total_amount=Decimal("560.00"),
            purchase_date=date(2024, 1, 1),
            num_installments=4,
            days_between=14,
            first_payment_date=date(2024, 1, 15)
        )

        expected_amount = Decimal("140.00")
        for inst in plan.installments:
            self.assertEqual(inst.amount, expected_amount)

    def test_custom_payment_schedule(self):
        """Test custom days between payments"""
        plan = build_installment_plan(
            merchant_name="Test Store",
            total_amount=Decimal("450.00"),
            purchase_date=date(2024, 1, 1),
            num_installments=3,
            days_between=21,
            first_payment_date=date(2024, 1, 22)
        )

        expected_dates = [
            date(2024, 1, 22),
            date(2024, 2, 12),
            date(2024, 3, 4)
        ]

        for i, inst in enumerate(plan.installments):
            self.assertEqual(inst.due_date, expected_dates[i])

    def test_all_installments_start_pending(self):
        """Test that all installments start with PENDING status"""
        plan = build_installment_plan(
            merchant_name="Test Store",
            total_amount=Decimal("1000.00"),
            purchase_date=date(2024, 1, 1),
            num_installments=10,
            days_between=30,
            first_payment_date=date(2024, 2, 1)
        )

        for inst in plan.installments:
            self.assertEqual(inst.status, PaymentStatus.PENDING)
            self.assertIsNone(inst.paid_date)

    def test_computed_properties(self):
        """Test that computed properties work correctly"""
        plan = build_installment_plan(
            merchant_name="Test Store",
            total_amount=Decimal("600.00"),
            purchase_date=date(2024, 1, 1),
            num_installments=3,
            days_between=30,
            first_payment_date=date(2024, 2, 1)
        )

        self.assertEqual(plan.num_installments, 3)
        self.assertEqual(plan.remaining_balance, Decimal("600.00"))
        self.assertFalse(plan.is_fully_paid)
        self.assertEqual(plan.next_payment_due, date(2024, 2, 1))
        self.assertEqual(len(plan.unpaid_installments), 3)


if __name__ == '__main__':
    unittest.main()
