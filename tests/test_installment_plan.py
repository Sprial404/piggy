import unittest
from datetime import date
from decimal import Decimal

from pydantic import ValidationError

from piggy.installment_plan import Installment, InstallmentPlan, PaymentStatus


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


class TestPartialPayments(unittest.TestCase):
    """Test partial payment functionality"""

    def test_amount_paid_defaults_to_zero(self):
        """Test that amount_paid defaults to zero for new installments"""
        inst = Installment(installment_number=1, amount=Decimal("100.00"), due_date=date(2024, 2, 1))
        self.assertEqual(inst.amount_paid, Decimal("0"))

    def test_remaining_amount_calculation(self):
        """Test remaining_amount property calculates correctly"""
        inst = Installment(
            installment_number=1, amount=Decimal("100.00"), due_date=date(2024, 2, 1), amount_paid=Decimal("30.00")
        )
        self.assertEqual(inst.remaining_amount, Decimal("70.00"))

    def test_is_partially_paid_property(self):
        """Test is_partially_paid property returns correct values"""
        inst = Installment(installment_number=1, amount=Decimal("100.00"), due_date=date(2024, 2, 1))

        # Not paid at all
        self.assertFalse(inst.is_partially_paid)

        # Partially paid
        inst.amount_paid = Decimal("50.00")
        self.assertTrue(inst.is_partially_paid)

        # Fully paid
        inst.amount_paid = Decimal("100.00")
        self.assertFalse(inst.is_partially_paid)

    def test_mark_partial_payment_success(self):
        """Test marking a partial payment works correctly"""
        inst = Installment(installment_number=1, amount=Decimal("100.00"), due_date=date(2024, 2, 1))

        inst.mark_partial_payment(Decimal("30.00"), date(2024, 2, 5))

        self.assertEqual(inst.amount_paid, Decimal("30.00"))
        self.assertEqual(inst.remaining_amount, Decimal("70.00"))
        self.assertTrue(inst.is_partially_paid)
        self.assertEqual(inst.status, PaymentStatus.PENDING)
        self.assertIsNone(inst.paid_date)

    def test_mark_partial_payment_multiple_times(self):
        """Test multiple partial payments accumulate correctly"""
        inst = Installment(installment_number=1, amount=Decimal("100.00"), due_date=date(2024, 2, 1))

        inst.mark_partial_payment(Decimal("30.00"), date(2024, 2, 5))
        inst.mark_partial_payment(Decimal("20.00"), date(2024, 2, 10))

        self.assertEqual(inst.amount_paid, Decimal("50.00"))
        self.assertEqual(inst.remaining_amount, Decimal("50.00"))
        self.assertTrue(inst.is_partially_paid)

    def test_mark_partial_payment_completes_to_paid(self):
        """Test partial payment that completes the full amount marks as PAID"""
        inst = Installment(installment_number=1, amount=Decimal("100.00"), due_date=date(2024, 2, 1))

        inst.mark_partial_payment(Decimal("60.00"), date(2024, 2, 5))
        inst.mark_partial_payment(Decimal("40.00"), date(2024, 2, 10))

        self.assertEqual(inst.amount_paid, Decimal("100.00"))
        self.assertEqual(inst.remaining_amount, Decimal("0"))
        self.assertFalse(inst.is_partially_paid)
        self.assertEqual(inst.status, PaymentStatus.PAID)
        self.assertEqual(inst.paid_date, date(2024, 2, 10))

    def test_mark_partial_payment_exceeds_amount_raises_error(self):
        """Test that partial payment exceeding remaining amount raises ValueError"""
        inst = Installment(
            installment_number=1, amount=Decimal("100.00"), due_date=date(2024, 2, 1), amount_paid=Decimal("60.00")
        )

        with self.assertRaises(ValueError) as context:
            inst.mark_partial_payment(Decimal("50.00"), date(2024, 2, 5))

        self.assertIn("exceed remaining balance", str(context.exception))

    def test_amount_paid_cannot_exceed_amount_validation(self):
        """Test Pydantic validation prevents amount_paid > amount"""
        with self.assertRaises(ValidationError) as context:
            Installment(
                installment_number=1, amount=Decimal("100.00"), due_date=date(2024, 2, 1), amount_paid=Decimal("150.00")
            )

        self.assertIn("amount_paid cannot exceed", str(context.exception))

    def test_mark_paid_sets_amount_paid(self):
        """Test mark_paid sets amount_paid to full amount"""
        inst = Installment(
            installment_number=1, amount=Decimal("100.00"), due_date=date(2024, 2, 1), amount_paid=Decimal("30.00")
        )

        inst.mark_full_payment(date(2024, 2, 5))

        self.assertEqual(inst.amount_paid, Decimal("100.00"))
        self.assertEqual(inst.remaining_amount, Decimal("0"))
        self.assertEqual(inst.status, PaymentStatus.PAID)
        self.assertEqual(inst.paid_date, date(2024, 2, 5))

    def test_mark_unpaid_resets_amount_paid(self):
        """Test mark_unpaid resets amount_paid to zero"""
        inst = Installment(
            installment_number=1,
            amount=Decimal("100.00"),
            due_date=date(2024, 2, 1),
            status=PaymentStatus.PAID,
            paid_date=date(2024, 2, 5),
            amount_paid=Decimal("100.00"),
        )

        inst.mark_unpaid()

        self.assertEqual(inst.amount_paid, Decimal("0"))
        self.assertEqual(inst.remaining_amount, Decimal("100.00"))
        self.assertEqual(inst.status, PaymentStatus.PENDING)
        self.assertIsNone(inst.paid_date)

    def test_remaining_balance_with_partial_payments(self):
        """Test InstallmentPlan.remaining_balance accounts for partial payments"""
        plan = InstallmentPlan(
            merchant_name="Test Store",
            total_amount=Decimal("300.00"),
            purchase_date=date(2024, 1, 1),
            installments=[
                Installment(
                    installment_number=1,
                    amount=Decimal("100.00"),
                    due_date=date(2024, 2, 1),
                    amount_paid=Decimal("50.00"),  # Partially paid
                ),
                Installment(
                    installment_number=2,
                    amount=Decimal("100.00"),
                    due_date=date(2024, 3, 1),
                    status=PaymentStatus.PAID,
                    paid_date=date(2024, 3, 1),
                    amount_paid=Decimal("100.00"),  # Fully paid
                ),
                Installment(
                    installment_number=3,
                    amount=Decimal("100.00"),
                    due_date=date(2024, 4, 1),
                    # Not paid - amount_paid defaults to 0
                ),
            ],
        )

        # Remaining balance should be:
        # Installment 1: 50.00 remaining
        # Installment 2: 0.00 remaining (paid)
        # Installment 3: 100.00 remaining
        # Total: 150.00
        self.assertEqual(plan.remaining_balance, Decimal("150.00"))


if __name__ == "__main__":
    unittest.main()
