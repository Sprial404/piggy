import unittest
from datetime import date
from decimal import Decimal

from piggy.installment_plan import InstallmentPlan, PaymentStatus


class TestBuildInstallmentPlan(unittest.TestCase):

    def test_build_plan_with_equal_installments(self):
        """Test building a plan with evenly divided installments"""
        plan = InstallmentPlan.build(
            merchant_name="Test Store",
            total_amount=Decimal("1200.00"),
            purchase_date=date(2024, 1, 1),
            num_installments=4,
            days_between=30,
            first_payment_date=date(2024, 2, 1),
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
        plan = InstallmentPlan.build(
            merchant_name="Test Store",
            total_amount=Decimal("600.00"),
            purchase_date=date(2024, 1, 1),
            num_installments=3,
            days_between=14,
            first_payment_date=date(2024, 1, 15),
        )

        expected_dates = [date(2024, 1, 15), date(2024, 1, 29), date(2024, 2, 12)]

        for i, inst in enumerate(plan.installments):
            self.assertEqual(inst.due_date, expected_dates[i])

    def test_installment_numbers_are_sequential(self):
        """Test that installment numbers start at 1 and increment"""
        plan = InstallmentPlan.build(
            merchant_name="Test Store",
            total_amount=Decimal("500.00"),
            purchase_date=date(2024, 1, 1),
            num_installments=5,
            days_between=7,
            first_payment_date=date(2024, 1, 8),
        )

        for i, inst in enumerate(plan.installments, start=1):
            self.assertEqual(inst.installment_number, i)

    def test_single_installment(self):
        """Test building a plan with a single installment"""
        plan = InstallmentPlan.build(
            merchant_name="Test Store",
            total_amount=Decimal("250.00"),
            purchase_date=date(2024, 1, 1),
            num_installments=1,
            days_between=30,
            first_payment_date=date(2024, 2, 1),
        )

        self.assertEqual(len(plan.installments), 1)
        self.assertEqual(plan.installments[0].amount, Decimal("250.00"))
        self.assertEqual(plan.installments[0].due_date, date(2024, 2, 1))

    def test_weekly_payment_schedule(self):
        """Test weekly payment frequency"""
        plan = InstallmentPlan.build(
            merchant_name="Test Store",
            total_amount=Decimal("280.00"),
            purchase_date=date(2024, 1, 1),
            num_installments=4,
            days_between=7,
            first_payment_date=date(2024, 1, 8),
        )

        expected_dates = [date(2024, 1, 8), date(2024, 1, 15), date(2024, 1, 22), date(2024, 1, 29)]

        for i, inst in enumerate(plan.installments):
            self.assertEqual(inst.due_date, expected_dates[i])

    def test_fortnightly_payment_schedule(self):
        """Test fortnightly payment frequency"""
        plan = InstallmentPlan.build(
            merchant_name="Test Store",
            total_amount=Decimal("560.00"),
            purchase_date=date(2024, 1, 1),
            num_installments=4,
            days_between=14,
            first_payment_date=date(2024, 1, 15),
        )

        expected_amount = Decimal("140.00")
        for inst in plan.installments:
            self.assertEqual(inst.amount, expected_amount)

    def test_custom_payment_schedule(self):
        """Test custom days between payments"""
        plan = InstallmentPlan.build(
            merchant_name="Test Store",
            total_amount=Decimal("450.00"),
            purchase_date=date(2024, 1, 1),
            num_installments=3,
            days_between=21,
            first_payment_date=date(2024, 1, 22),
        )

        expected_dates = [date(2024, 1, 22), date(2024, 2, 12), date(2024, 3, 4)]

        for i, inst in enumerate(plan.installments):
            self.assertEqual(inst.due_date, expected_dates[i])

    def test_all_installments_start_pending(self):
        """Test that all installments start with PENDING status"""
        plan = InstallmentPlan.build(
            merchant_name="Test Store",
            total_amount=Decimal("1000.00"),
            purchase_date=date(2024, 1, 1),
            num_installments=10,
            days_between=30,
            first_payment_date=date(2024, 2, 1),
        )

        for inst in plan.installments:
            self.assertEqual(inst.status, PaymentStatus.PENDING)
            self.assertIsNone(inst.paid_date)

    def test_computed_properties(self):
        """Test that computed properties work correctly"""
        plan = InstallmentPlan.build(
            merchant_name="Test Store",
            total_amount=Decimal("600.00"),
            purchase_date=date(2024, 1, 1),
            num_installments=3,
            days_between=30,
            first_payment_date=date(2024, 2, 1),
        )

        self.assertEqual(plan.num_installments, 3)
        self.assertEqual(plan.remaining_balance, Decimal("600.00"))
        self.assertFalse(plan.is_fully_paid)
        self.assertEqual(plan.next_payment_due, date(2024, 2, 1))
        self.assertEqual(len(plan.unpaid_installments), 3)


class TestGetInstallments(unittest.TestCase):

    def setUp(self):
        """Set up test data"""
        self.plan = InstallmentPlan.build(
            merchant_name="Test Store",
            total_amount=Decimal("1200.00"),
            purchase_date=date(2024, 1, 1),
            num_installments=4,
            days_between=30,
            first_payment_date=date(2024, 2, 1),
        )

    def test_get_all_installments_with_none(self):
        """Test getting all installments when numbers=None"""
        result = self.plan.get_installments(None)
        self.assertEqual(len(result), 4)
        self.assertEqual(result, self.plan.installments)

    def test_get_all_installments_without_argument(self):
        """Test getting all installments without passing argument"""
        result = self.plan.get_installments()
        self.assertEqual(len(result), 4)
        self.assertEqual(result, self.plan.installments)

    def test_get_single_installment(self):
        """Test getting a single installment by number"""
        result = self.plan.get_installments([2])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].installment_number, 2)
        self.assertEqual(result[0].amount, Decimal("300.00"))

    def test_get_multiple_installments(self):
        """Test getting multiple installments by numbers"""
        result = self.plan.get_installments([1, 3, 4])
        self.assertEqual(len(result), 3)
        self.assertEqual([inst.installment_number for inst in result], [1, 3, 4])

    def test_get_installments_preserves_order(self):
        """Test that installments are returned in requested order"""
        result = self.plan.get_installments([4, 2, 1])
        self.assertEqual([inst.installment_number for inst in result], [4, 2, 1])

    def test_get_installment_nonexistent_raises_error(self):
        """Test that requesting nonexistent installment raises ValueError"""
        with self.assertRaises(ValueError) as context:
            self.plan.get_installments([5])
        self.assertIn("Installment #5 does not exist", str(context.exception))

    def test_get_installments_partial_invalid_raises_error(self):
        """Test that requesting mix of valid and invalid numbers raises error"""
        with self.assertRaises(ValueError) as context:
            self.plan.get_installments([1, 2, 99])
        self.assertIn("Installment #99 does not exist", str(context.exception))

    def test_get_installments_empty_list(self):
        """Test getting installments with empty list"""
        result = self.plan.get_installments([])
        self.assertEqual(len(result), 0)
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
