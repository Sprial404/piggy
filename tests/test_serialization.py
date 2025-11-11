import json
import tempfile
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

from pydantic import ValidationError

from piggy.installment_plan import Installment, InstallmentPlan, PaymentStatus


class TestInstallmentPlanSerialization(unittest.TestCase):

    def setUp(self):
        """Set up test data"""
        self.sample_plan = InstallmentPlan(
            merchant_name="Tech Store",
            total_amount=Decimal("1200.00"),
            purchase_date=date(2024, 1, 15),
            installments=[
                Installment(
                    installment_number=1,
                    amount=Decimal("400.00"),
                    due_date=date(2024, 2, 15),
                    status=PaymentStatus.PAID,
                    paid_date=date(2024, 2, 10),
                ),
                Installment(
                    installment_number=2,
                    amount=Decimal("400.00"),
                    due_date=date(2024, 3, 15),
                    status=PaymentStatus.PENDING,
                ),
                Installment(
                    installment_number=3,
                    amount=Decimal("400.00"),
                    due_date=date(2024, 4, 15),
                    status=PaymentStatus.PENDING,
                ),
            ],
        )

    def test_json_serialization_to_string(self):
        """Test JSON serialization to string"""
        json_str = self.sample_plan.to_json()

        # Verify it's valid JSON
        parsed = json.loads(json_str)
        self.assertIsInstance(parsed, dict)
        self.assertEqual(parsed["merchant_name"], "Tech Store")
        self.assertEqual(parsed["total_amount"], "1200.00")
        self.assertEqual(len(parsed["installments"]), 3)

    def test_json_serialization_to_file(self):
        """Test JSON serialization to file"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp_file:
            tmp_path = tmp_file.name

        try:
            # Serialize to file
            result = self.sample_plan.to_json(tmp_path)

            # Verify file was created and contains valid JSON
            self.assertTrue(Path(tmp_path).exists())
            file_content = Path(tmp_path).read_text()
            self.assertEqual(result, file_content)

            # Verify content is valid JSON
            parsed = json.loads(file_content)
            self.assertEqual(parsed["merchant_name"], "Tech Store")
        finally:
            # Clean up
            Path(tmp_path).unlink(missing_ok=True)

    def test_json_deserialization_from_string(self):
        """Test JSON deserialization from string"""
        json_str = self.sample_plan.to_json()
        restored_plan = InstallmentPlan.from_json(json_str)

        # Verify all data is preserved
        self.assertEqual(restored_plan.merchant_name, self.sample_plan.merchant_name)
        self.assertEqual(restored_plan.total_amount, self.sample_plan.total_amount)
        self.assertEqual(restored_plan.purchase_date, self.sample_plan.purchase_date)
        self.assertEqual(len(restored_plan.installments), len(self.sample_plan.installments))

        # Check first installment details
        original_inst = self.sample_plan.installments[0]
        restored_inst = restored_plan.installments[0]
        self.assertEqual(restored_inst.installment_number, original_inst.installment_number)
        self.assertEqual(restored_inst.amount, original_inst.amount)
        self.assertEqual(restored_inst.due_date, original_inst.due_date)
        self.assertEqual(restored_inst.status, original_inst.status)
        self.assertEqual(restored_inst.paid_date, original_inst.paid_date)

    def test_json_deserialization_from_file(self):
        """Test JSON deserialization from file"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp_file:
            tmp_path = tmp_file.name

        try:
            # Save to file
            self.sample_plan.to_json(tmp_path)

            # Load from file
            restored_plan = InstallmentPlan.from_json_file(tmp_path)

            # Verify data integrity
            self.assertEqual(restored_plan.merchant_name, self.sample_plan.merchant_name)
            self.assertEqual(restored_plan.total_amount, self.sample_plan.total_amount)
            self.assertEqual(restored_plan.remaining_balance, self.sample_plan.remaining_balance)
        finally:
            # Clean up
            Path(tmp_path).unlink(missing_ok=True)

    def test_csv_export(self):
        """Test CSV export functionality"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp_file:
            tmp_path = tmp_file.name

        try:
            # Export to CSV
            self.sample_plan.to_csv(tmp_path)

            # Verify file was created
            self.assertTrue(Path(tmp_path).exists())

            # Read and verify content
            content = Path(tmp_path).read_text()
            lines = content.strip().split("\n")

            # Check header matches flattened CSV format
            expected_headers = "merchant_name,total_amount,purchase_date,created_at,updated_at,installment_number,amount,due_date,status,paid_date,amount_paid,remaining_amount,is_paid,is_pending,is_overdue,is_partially_paid"
            self.assertEqual(lines[0], expected_headers)

            # Verify key data appears in CSV
            self.assertIn("Tech Store", content)
            self.assertIn("1200.00", content)

            # Should have header + 3 installment rows
            self.assertEqual(len(lines), 4)
        finally:
            # Clean up
            Path(tmp_path).unlink(missing_ok=True)

    def test_roundtrip_json_integrity(self):
        """Test that data survives JSON roundtrip without loss"""
        # Serialize and deserialize
        json_str = self.sample_plan.to_json()
        restored_plan = InstallmentPlan.from_json(json_str)

        # Check calculated properties are preserved
        self.assertEqual(restored_plan.remaining_balance, self.sample_plan.remaining_balance)
        self.assertEqual(restored_plan.is_fully_paid, self.sample_plan.is_fully_paid)
        self.assertEqual(restored_plan.next_payment_due, self.sample_plan.next_payment_due)
        self.assertEqual(restored_plan.num_installments, self.sample_plan.num_installments)


class TestInstallmentPlanValidation(unittest.TestCase):
    """Test domain model validation and negative cases"""

    def test_invalid_json_deserialization(self):
        """Test deserialization with invalid JSON"""
        with self.assertRaises(json.JSONDecodeError):
            InstallmentPlan.from_json("not valid json {")

    def test_missing_required_fields(self):
        """Test deserialization with missing required fields"""
        invalid_json = json.dumps(
            {
                "merchant_name": "Test",
                # Missing total_amount, purchase_date, installments
            }
        )

        with self.assertRaises(ValidationError):
            InstallmentPlan.from_json(invalid_json)

    def test_negative_total_amount(self):
        """Test that negative total_amount is rejected"""
        from pydantic import ValidationError

        with self.assertRaises(ValidationError):
            InstallmentPlan(
                merchant_name="Test",
                total_amount=Decimal("-100.00"),
                purchase_date=date(2024, 1, 1),
                installments=[Installment(installment_number=1, amount=Decimal("-100.00"), due_date=date(2024, 2, 1))],
            )

    def test_zero_total_amount(self):
        """Test that zero total_amount is rejected"""
        from pydantic import ValidationError

        with self.assertRaises(ValidationError):
            InstallmentPlan(
                merchant_name="Test", total_amount=Decimal("0"), purchase_date=date(2024, 1, 1), installments=[]
            )

    def test_empty_installments_list(self):
        """Test that empty installments list is rejected"""
        from pydantic import ValidationError

        with self.assertRaises(ValidationError):
            InstallmentPlan(
                merchant_name="Test", total_amount=Decimal("100.00"), purchase_date=date(2024, 1, 1), installments=[]
            )

    def test_installment_total_mismatch(self):
        """Test that installment totals must match plan total"""
        from pydantic import ValidationError

        with self.assertRaises(ValidationError) as context:
            InstallmentPlan(
                merchant_name="Test",
                total_amount=Decimal("1000.00"),
                purchase_date=date(2024, 1, 1),
                installments=[
                    Installment(installment_number=1, amount=Decimal("300.00"), due_date=date(2024, 2, 1)),
                    Installment(installment_number=2, amount=Decimal("300.00"), due_date=date(2024, 3, 1)),
                ],
            )

        self.assertIn("must equal total_amount", str(context.exception))

    def test_non_sequential_installment_numbers(self):
        """Test that installment numbers must be sequential"""
        from pydantic import ValidationError

        with self.assertRaises(ValidationError) as context:
            InstallmentPlan(
                merchant_name="Test",
                total_amount=Decimal("600.00"),
                purchase_date=date(2024, 1, 1),
                installments=[
                    Installment(installment_number=1, amount=Decimal("300.00"), due_date=date(2024, 2, 1)),
                    Installment(installment_number=3, amount=Decimal("300.00"), due_date=date(2024, 3, 1)),  # Skip 2
                ],
            )

        self.assertIn("sequential", str(context.exception))

    def test_paid_date_without_paid_status(self):
        """Test that paid_date can only be set when status is PAID"""
        from pydantic import ValidationError

        with self.assertRaises(ValidationError) as context:
            Installment(
                installment_number=1,
                amount=Decimal("100.00"),
                due_date=date(2024, 2, 1),
                status=PaymentStatus.PENDING,
                paid_date=date(2024, 1, 31),  # Should fail
            )

        self.assertIn("paid_date can only be set when status is PAID", str(context.exception))

    def test_file_not_found(self):
        """Test loading from non-existent file"""
        with self.assertRaises(FileNotFoundError):
            InstallmentPlan.from_json_file("/nonexistent/path/file.json")

    def test_negative_installment_amount(self):
        """Test that negative installment amount is rejected"""
        from pydantic import ValidationError

        with self.assertRaises(ValidationError):
            Installment(installment_number=1, amount=Decimal("-50.00"), due_date=date(2024, 2, 1))


class TestInstallmentPlanComputedProperties(unittest.TestCase):
    """Test computed properties and business logic"""

    def setUp(self):
        """Set up test data"""
        self.plan = InstallmentPlan(
            merchant_name="Test Store",
            total_amount=Decimal("1200.00"),
            purchase_date=date(2024, 1, 1),
            installments=[
                Installment(
                    installment_number=1,
                    amount=Decimal("400.00"),
                    due_date=date(2024, 1, 15),
                    status=PaymentStatus.PAID,
                    paid_date=date(2024, 1, 14),
                ),
                Installment(
                    installment_number=2,
                    amount=Decimal("400.00"),
                    due_date=date(2024, 2, 15),
                    status=PaymentStatus.PENDING,
                ),
                Installment(
                    installment_number=3,
                    amount=Decimal("400.00"),
                    due_date=date(2024, 3, 15),
                    status=PaymentStatus.OVERDUE,
                ),
            ],
        )

    def test_remaining_balance(self):
        """Test remaining_balance calculation"""
        # 400 (paid) should not count, 400 + 400 (unpaid) = 800
        self.assertEqual(self.plan.remaining_balance, Decimal("800.00"))

    def test_is_fully_paid_false(self):
        """Test is_fully_paid when plan is not fully paid"""
        self.assertFalse(self.plan.is_fully_paid)

    def test_is_fully_paid_true(self):
        """Test is_fully_paid when all installments are paid"""
        for inst in self.plan.installments:
            inst.status = PaymentStatus.PAID
            inst.paid_date = date(2024, 1, 1)

        self.assertTrue(self.plan.is_fully_paid)

    def test_next_payment_due(self):
        """Test next_payment_due property"""
        # Should return the earliest PENDING due date (2024-02-15)
        self.assertEqual(self.plan.next_payment_due, date(2024, 2, 15))

    def test_next_payment_due_when_fully_paid(self):
        """Test next_payment_due returns None when fully paid"""
        for inst in self.plan.installments:
            inst.status = PaymentStatus.PAID
            inst.paid_date = date(2024, 1, 1)

        self.assertIsNone(self.plan.next_payment_due)

    def test_unpaid_installments(self):
        """Test unpaid_installments property"""
        unpaid = self.plan.unpaid_installments

        self.assertEqual(len(unpaid), 2)
        self.assertEqual(unpaid[0].installment_number, 2)
        self.assertEqual(unpaid[1].installment_number, 3)

    def test_num_installments(self):
        """Test num_installments property"""
        self.assertEqual(self.plan.num_installments, 3)

    def test_get_installment(self):
        """Test get_installment method"""
        inst = self.plan.get_installment(2)
        self.assertEqual(inst.installment_number, 2)
        self.assertEqual(inst.amount, Decimal("400.00"))

    def test_get_installment_invalid_number(self):
        """Test get_installment with invalid number"""
        with self.assertRaises(ValueError) as context:
            self.plan.get_installment(99)

        self.assertIn("does not exist", str(context.exception))

    def test_get_installments_multiple(self):
        """Test get_installments with multiple numbers"""
        installments = self.plan.get_installments([1, 3])

        self.assertEqual(len(installments), 2)
        self.assertEqual(installments[0].installment_number, 1)
        self.assertEqual(installments[1].installment_number, 3)

    def test_get_installments_all(self):
        """Test get_installments with None returns all"""
        installments = self.plan.get_installments(None)

        self.assertEqual(len(installments), 3)

    def test_installment_is_paid(self):
        """Test Installment is_paid property"""
        self.assertTrue(self.plan.installments[0].is_paid)
        self.assertFalse(self.plan.installments[1].is_paid)

    def test_installment_is_pending(self):
        """Test Installment is_pending property"""
        self.assertFalse(self.plan.installments[0].is_pending)
        self.assertTrue(self.plan.installments[1].is_pending)

    def test_installment_is_overdue(self):
        """Test Installment is_overdue property"""
        self.assertFalse(self.plan.installments[0].is_overdue)
        self.assertTrue(self.plan.installments[2].is_overdue)

    def test_get_overdue_installments(self):
        """Test get_overdue_installments method"""
        overdue = self.plan.get_overdue_installments(as_of=date(2024, 3, 20))

        # Installments 2 and 3 should be overdue
        self.assertEqual(len(overdue), 2)

    def test_has_overdue_payments(self):
        """Test has_overdue_payments property"""
        self.assertTrue(self.plan.has_overdue_payments)

    def test_update_overdue_status(self):
        """Test update_overdue_status method"""
        # Create plan with pending installments in the past
        plan = InstallmentPlan(
            merchant_name="Test",
            total_amount=Decimal("600.00"),
            purchase_date=date(2024, 1, 1),
            installments=[
                Installment(
                    installment_number=1,
                    amount=Decimal("200.00"),
                    due_date=date(2024, 1, 15),
                    status=PaymentStatus.PENDING,
                ),
                Installment(
                    installment_number=2,
                    amount=Decimal("200.00"),
                    due_date=date(2024, 2, 15),
                    status=PaymentStatus.PENDING,
                ),
                Installment(
                    installment_number=3,
                    amount=Decimal("200.00"),
                    due_date=date(2024, 3, 15),
                    status=PaymentStatus.PENDING,
                ),
            ],
        )

        # Update as of March 1st - first two should be overdue
        updated_count = plan.update_overdue_status(as_of=date(2024, 3, 1))

        self.assertEqual(updated_count, 2)
        self.assertEqual(plan.installments[0].status, PaymentStatus.OVERDUE)
        self.assertEqual(plan.installments[1].status, PaymentStatus.OVERDUE)
        self.assertEqual(plan.installments[2].status, PaymentStatus.PENDING)


class TestInstallmentPlanSetters(unittest.TestCase):
    """Test setter methods and timestamp updates"""

    def setUp(self):
        """Set up test data"""
        self.plan = InstallmentPlan(
            merchant_name="Test Store",
            total_amount=Decimal("600.00"),
            purchase_date=date(2024, 1, 1),
            installments=[
                Installment(installment_number=1, amount=Decimal("300.00"), due_date=date(2024, 2, 1)),
                Installment(installment_number=2, amount=Decimal("300.00"), due_date=date(2024, 3, 1)),
            ],
        )

    def test_mark_installment_paid(self):
        """Test mark_installment_paid method"""
        paid_date = date(2024, 1, 31)
        self.plan.mark_installment_paid(1, paid_date)

        inst = self.plan.get_installment(1)
        self.assertEqual(inst.status, PaymentStatus.PAID)
        self.assertEqual(inst.paid_date, paid_date)

    def test_mark_installment_unpaid(self):
        """Test mark_installment_unpaid method"""
        # First mark as paid
        self.plan.mark_installment_paid(1, date(2024, 1, 31))

        # Then mark as unpaid
        self.plan.mark_installment_unpaid(1)

        inst = self.plan.get_installment(1)
        self.assertEqual(inst.status, PaymentStatus.PENDING)
        self.assertIsNone(inst.paid_date)

    def test_set_merchant_name(self):
        """Test set_merchant_name method"""
        old_updated_at = self.plan.updated_at

        self.plan.set_merchant_name("New Store")

        self.assertEqual(self.plan.merchant_name, "New Store")
        self.assertGreaterEqual(self.plan.updated_at, old_updated_at)

    def test_set_installment_amount(self):
        """Test set_installment_amount method"""
        self.plan.set_installment_amount(1, Decimal("350.00"))

        inst = self.plan.get_installment(1)
        self.assertEqual(inst.amount, Decimal("350.00"))
        # Total should be recalculated: 350 + 300 = 650
        self.assertEqual(self.plan.total_amount, Decimal("650.00"))

    def test_set_installment_due_date(self):
        """Test set_installment_due_date method"""
        new_date = date(2024, 2, 15)
        self.plan.set_installment_due_date(1, new_date)

        inst = self.plan.get_installment(1)
        self.assertEqual(inst.due_date, new_date)

    def test_installment_mark_paid(self):
        """Test Installment mark_paid method"""
        inst = self.plan.installments[0]
        old_updated_at = inst.updated_at

        paid_date = date(2024, 1, 31)
        inst.mark_full_payment(paid_date)

        self.assertEqual(inst.status, PaymentStatus.PAID)
        self.assertEqual(inst.paid_date, paid_date)
        self.assertGreaterEqual(inst.updated_at, old_updated_at)

    def test_installment_mark_unpaid(self):
        """Test Installment mark_unpaid method"""
        inst = self.plan.installments[0]

        # First mark as paid
        inst.mark_full_payment(date(2024, 1, 31))

        # Then mark as unpaid
        inst.mark_unpaid()

        self.assertEqual(inst.status, PaymentStatus.PENDING)
        self.assertIsNone(inst.paid_date)

    def test_installment_set_amount(self):
        """Test Installment set_amount method"""
        inst = self.plan.installments[0]

        inst.set_amount(Decimal("350.00"))

        self.assertEqual(inst.amount, Decimal("350.00"))

    def test_installment_set_amount_invalid(self):
        """Test Installment set_amount with invalid value"""
        inst = self.plan.installments[0]

        with self.assertRaises(ValueError) as context:
            inst.set_amount(Decimal("0"))

        self.assertIn("greater than zero", str(context.exception))


class TestPartialPaymentSerialization(unittest.TestCase):
    """Test serialization with partial payments"""

    def test_backward_compatibility_loading_old_plans(self):
        """Test that plans without amount_paid field load correctly"""
        json_data = json.dumps(
            {
                "merchant_name": "Old Store",
                "total_amount": "200.00",
                "purchase_date": "2024-01-01",
                "installments": [
                    {
                        "installment_number": 1,
                        "amount": "100.00",
                        "due_date": "2024-02-01",
                        "status": "pending",
                        # No amount_paid field - should default to 0
                    },
                    {
                        "installment_number": 2,
                        "amount": "100.00",
                        "due_date": "2024-03-01",
                        "status": "paid",
                        "paid_date": "2024-03-01",
                        # No amount_paid field - should default to 0
                    },
                ],
            }
        )

        plan = InstallmentPlan.from_json(json_data)

        # Check installment 1 defaults
        self.assertEqual(plan.installments[0].amount_paid, Decimal("0"))
        self.assertEqual(plan.installments[0].remaining_amount, Decimal("100.00"))

        # Check installment 2 defaults (even though marked paid)
        # This is OK - we'll update amount_paid when we call mark_paid()
        self.assertEqual(plan.installments[1].amount_paid, Decimal("0"))


if __name__ == "__main__":
    unittest.main()
