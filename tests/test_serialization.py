"""
Pytest tests for InstallmentPlan serialization and validation.
"""

import json
from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from piggy.installment_plan import Installment, InstallmentPlan, PaymentStatus


@pytest.fixture
def sample_plan():
    """Create a sample plan with mixed payment statuses."""
    return InstallmentPlan(
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


@pytest.fixture
def computed_properties_plan():
    """Create a plan for testing computed properties."""
    return InstallmentPlan(
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


@pytest.fixture
def modifiable_plan():
    """Create a plan for testing setters."""
    return InstallmentPlan(
        merchant_name="Test Store",
        total_amount=Decimal("600.00"),
        purchase_date=date(2024, 1, 1),
        installments=[
            Installment(installment_number=1, amount=Decimal("300.00"), due_date=date(2024, 2, 1)),
            Installment(installment_number=2, amount=Decimal("300.00"), due_date=date(2024, 3, 1)),
        ],
    )


@pytest.mark.unit
class TestInstallmentPlanSerialization:
    """Tests for JSON and CSV serialization."""

    def test_json_serialization_to_string(self, sample_plan):
        """Test JSON serialization to string."""
        json_str = sample_plan.to_json()

        parsed = json.loads(json_str)
        assert isinstance(parsed, dict)
        assert parsed["merchant_name"] == "Tech Store"
        assert parsed["total_amount"] == "1200.00"
        assert len(parsed["installments"]) == 3

    def test_json_serialization_to_file(self, sample_plan, tmp_path):
        """Test JSON serialization to file."""
        tmp_file = tmp_path / "test_plan.json"

        result = sample_plan.to_json(str(tmp_file))

        assert tmp_file.exists()
        file_content = tmp_file.read_text()
        assert result == file_content

        parsed = json.loads(file_content)
        assert parsed["merchant_name"] == "Tech Store"

    def test_json_deserialization_from_string(self, sample_plan):
        """Test JSON deserialization from string."""
        json_str = sample_plan.to_json()
        restored_plan = InstallmentPlan.from_json(json_str)

        assert restored_plan.merchant_name == sample_plan.merchant_name
        assert restored_plan.total_amount == sample_plan.total_amount
        assert restored_plan.purchase_date == sample_plan.purchase_date
        assert len(restored_plan.installments) == len(sample_plan.installments)

        original_inst = sample_plan.installments[0]
        restored_inst = restored_plan.installments[0]
        assert restored_inst.installment_number == original_inst.installment_number
        assert restored_inst.amount == original_inst.amount
        assert restored_inst.due_date == original_inst.due_date
        assert restored_inst.status == original_inst.status
        assert restored_inst.paid_date == original_inst.paid_date

    def test_json_deserialization_from_file(self, sample_plan, tmp_path):
        """Test JSON deserialization from file."""
        tmp_file = tmp_path / "test_plan.json"

        sample_plan.to_json(str(tmp_file))
        restored_plan = InstallmentPlan.from_json_file(str(tmp_file))

        assert restored_plan.merchant_name == sample_plan.merchant_name
        assert restored_plan.total_amount == sample_plan.total_amount
        assert restored_plan.remaining_balance == sample_plan.remaining_balance

    def test_csv_export(self, sample_plan, tmp_path):
        """Test CSV export functionality."""
        tmp_file = tmp_path / "test_plan.csv"

        sample_plan.to_csv(str(tmp_file))

        assert tmp_file.exists()
        content = tmp_file.read_text()
        lines = content.strip().split("\n")

        expected_headers = "merchant_name,total_amount,purchase_date,created_at,updated_at,installment_number,amount,due_date,status,paid_date,amount_paid,remaining_amount,is_paid,is_pending,is_overdue,is_partially_paid"
        assert lines[0] == expected_headers
        assert "Tech Store" in content
        assert "1200.00" in content
        assert len(lines) == 4

    def test_roundtrip_json_integrity(self, sample_plan):
        """Test that data survives JSON roundtrip without loss."""
        json_str = sample_plan.to_json()
        restored_plan = InstallmentPlan.from_json(json_str)

        assert restored_plan.remaining_balance == sample_plan.remaining_balance
        assert restored_plan.is_fully_paid == sample_plan.is_fully_paid
        assert restored_plan.next_payment_due == sample_plan.next_payment_due
        assert restored_plan.num_installments == sample_plan.num_installments


@pytest.mark.unit
class TestInstallmentPlanValidation:
    """Test domain model validation and negative cases."""

    def test_invalid_json_deserialization(self):
        """Test deserialization with invalid JSON."""
        with pytest.raises(json.JSONDecodeError):
            InstallmentPlan.from_json("not valid json {")

    def test_missing_required_fields(self):
        """Test deserialization with missing required fields."""
        invalid_json = json.dumps({"merchant_name": "Test"})

        with pytest.raises(ValidationError):
            InstallmentPlan.from_json(invalid_json)

    def test_negative_total_amount(self):
        """Test that negative total_amount is rejected."""
        with pytest.raises(ValidationError):
            InstallmentPlan(
                merchant_name="Test",
                total_amount=Decimal("-100.00"),
                purchase_date=date(2024, 1, 1),
                installments=[Installment(installment_number=1, amount=Decimal("-100.00"), due_date=date(2024, 2, 1))],
            )

    def test_zero_total_amount(self):
        """Test that zero total_amount is rejected."""
        with pytest.raises(ValidationError):
            InstallmentPlan(
                merchant_name="Test", total_amount=Decimal("0"), purchase_date=date(2024, 1, 1), installments=[]
            )

    def test_empty_installments_list(self):
        """Test that empty installments list is rejected."""
        with pytest.raises(ValidationError):
            InstallmentPlan(
                merchant_name="Test", total_amount=Decimal("100.00"), purchase_date=date(2024, 1, 1), installments=[]
            )

    def test_installment_total_mismatch(self):
        """Test that installment totals must match plan total."""
        with pytest.raises(ValidationError, match="must equal total_amount"):
            InstallmentPlan(
                merchant_name="Test",
                total_amount=Decimal("1000.00"),
                purchase_date=date(2024, 1, 1),
                installments=[
                    Installment(installment_number=1, amount=Decimal("300.00"), due_date=date(2024, 2, 1)),
                    Installment(installment_number=2, amount=Decimal("300.00"), due_date=date(2024, 3, 1)),
                ],
            )

    def test_non_sequential_installment_numbers(self):
        """Test that installment numbers must be sequential."""
        with pytest.raises(ValidationError, match="sequential"):
            InstallmentPlan(
                merchant_name="Test",
                total_amount=Decimal("600.00"),
                purchase_date=date(2024, 1, 1),
                installments=[
                    Installment(installment_number=1, amount=Decimal("300.00"), due_date=date(2024, 2, 1)),
                    Installment(installment_number=3, amount=Decimal("300.00"), due_date=date(2024, 3, 1)),  # Skip 2
                ],
            )

    def test_paid_date_without_paid_status(self):
        """Test that paid_date can only be set when status is PAID."""
        with pytest.raises(ValidationError, match="paid_date can only be set when status is PAID"):
            Installment(
                installment_number=1,
                amount=Decimal("100.00"),
                due_date=date(2024, 2, 1),
                status=PaymentStatus.PENDING,
                paid_date=date(2024, 1, 31),  # Should fail
            )

    def test_file_not_found(self):
        """Test loading from non-existent file."""
        with pytest.raises(FileNotFoundError):
            InstallmentPlan.from_json_file("/nonexistent/path/file.json")

    def test_negative_installment_amount(self):
        """Test that negative installment amount is rejected."""
        with pytest.raises(ValidationError):
            Installment(installment_number=1, amount=Decimal("-50.00"), due_date=date(2024, 2, 1))


@pytest.mark.unit
class TestInstallmentPlanComputedProperties:
    """Test computed properties and business logic."""

    def test_remaining_balance(self, computed_properties_plan):
        """Test remaining_balance calculation."""
        # 400 (paid) should not count, 400 + 400 (unpaid) = 800
        assert computed_properties_plan.remaining_balance == Decimal("800.00")

    def test_is_fully_paid_false(self, computed_properties_plan):
        """Test is_fully_paid when plan is not fully paid."""
        assert computed_properties_plan.is_fully_paid is False

    def test_is_fully_paid_true(self, computed_properties_plan):
        """Test is_fully_paid when all installments are paid."""
        for inst in computed_properties_plan.installments:
            inst.status = PaymentStatus.PAID
            inst.paid_date = date(2024, 1, 1)

        assert computed_properties_plan.is_fully_paid is True

    def test_next_payment_due(self, computed_properties_plan):
        """Test next_payment_due property."""
        # Should return the earliest PENDING due date (2024-02-15)
        assert computed_properties_plan.next_payment_due == date(2024, 2, 15)

    def test_next_payment_due_when_fully_paid(self, computed_properties_plan):
        """Test next_payment_due returns None when fully paid."""
        for inst in computed_properties_plan.installments:
            inst.status = PaymentStatus.PAID
            inst.paid_date = date(2024, 1, 1)

        assert computed_properties_plan.next_payment_due is None

    def test_unpaid_installments(self, computed_properties_plan):
        """Test unpaid_installments property."""
        unpaid = computed_properties_plan.unpaid_installments

        assert len(unpaid) == 2
        assert unpaid[0].installment_number == 2
        assert unpaid[1].installment_number == 3

    def test_num_installments(self, computed_properties_plan):
        """Test num_installments property."""
        assert computed_properties_plan.num_installments == 3

    def test_get_installment(self, computed_properties_plan):
        """Test get_installment method."""
        inst = computed_properties_plan.get_installment(2)
        assert inst.installment_number == 2
        assert inst.amount == Decimal("400.00")

    def test_get_installment_invalid_number(self, computed_properties_plan):
        """Test get_installment with invalid number."""
        with pytest.raises(ValueError, match="does not exist"):
            computed_properties_plan.get_installment(99)

    def test_get_installments_multiple(self, computed_properties_plan):
        """Test get_installments with multiple numbers."""
        installments = computed_properties_plan.get_installments([1, 3])

        assert len(installments) == 2
        assert installments[0].installment_number == 1
        assert installments[1].installment_number == 3

    def test_get_installments_all(self, computed_properties_plan):
        """Test get_installments with None returns all."""
        installments = computed_properties_plan.get_installments(None)

        assert len(installments) == 3

    def test_installment_is_paid(self, computed_properties_plan):
        """Test Installment is_paid property."""
        assert computed_properties_plan.installments[0].is_paid is True
        assert computed_properties_plan.installments[1].is_paid is False

    def test_installment_is_pending(self, computed_properties_plan):
        """Test Installment is_pending property."""
        assert computed_properties_plan.installments[0].is_pending is False
        assert computed_properties_plan.installments[1].is_pending is True

    def test_installment_is_overdue(self, computed_properties_plan):
        """Test Installment is_overdue property."""
        assert computed_properties_plan.installments[0].is_overdue is False
        assert computed_properties_plan.installments[2].is_overdue is True

    def test_get_overdue_installments(self, computed_properties_plan):
        """Test get_overdue_installments method."""
        overdue = computed_properties_plan.get_overdue_installments(as_of=date(2024, 3, 20))

        # Installments 2 and 3 should be overdue
        assert len(overdue) == 2

    def test_has_overdue_payments(self, computed_properties_plan):
        """Test has_overdue_payments property."""
        assert computed_properties_plan.has_overdue_payments is True

    def test_update_overdue_status(self):
        """Test update_overdue_status method."""
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

        assert updated_count == 2
        assert plan.installments[0].status == PaymentStatus.OVERDUE
        assert plan.installments[1].status == PaymentStatus.OVERDUE
        assert plan.installments[2].status == PaymentStatus.PENDING


@pytest.mark.unit
class TestInstallmentPlanSetters:
    """Test setter methods and timestamp updates."""

    def test_mark_installment_paid(self, modifiable_plan):
        """Test mark_installment_paid method."""
        paid_date = date(2024, 1, 31)
        modifiable_plan.mark_installment_paid(1, paid_date)

        inst = modifiable_plan.get_installment(1)
        assert inst.status == PaymentStatus.PAID
        assert inst.paid_date == paid_date

    def test_mark_installment_unpaid(self, modifiable_plan):
        """Test mark_installment_unpaid method."""
        # First mark as paid
        modifiable_plan.mark_installment_paid(1, date(2024, 1, 31))

        # Then mark as unpaid
        modifiable_plan.mark_installment_unpaid(1)

        inst = modifiable_plan.get_installment(1)
        assert inst.status == PaymentStatus.PENDING
        assert inst.paid_date is None

    def test_set_merchant_name(self, modifiable_plan):
        """Test set_merchant_name method."""
        old_updated_at = modifiable_plan.updated_at

        modifiable_plan.set_merchant_name("New Store")

        assert modifiable_plan.merchant_name == "New Store"
        assert modifiable_plan.updated_at >= old_updated_at

    def test_set_installment_amount(self, modifiable_plan):
        """Test set_installment_amount method."""
        modifiable_plan.set_installment_amount(1, Decimal("350.00"))

        inst = modifiable_plan.get_installment(1)
        assert inst.amount == Decimal("350.00")
        # Total should be recalculated: 350 + 300 = 650
        assert modifiable_plan.total_amount == Decimal("650.00")

    def test_set_installment_due_date(self, modifiable_plan):
        """Test set_installment_due_date method."""
        new_date = date(2024, 2, 15)
        modifiable_plan.set_installment_due_date(1, new_date)

        inst = modifiable_plan.get_installment(1)
        assert inst.due_date == new_date

    def test_installment_mark_paid(self, modifiable_plan):
        """Test Installment mark_paid method."""
        inst = modifiable_plan.installments[0]
        old_updated_at = inst.updated_at

        paid_date = date(2024, 1, 31)
        inst.mark_full_payment(paid_date)

        assert inst.status == PaymentStatus.PAID
        assert inst.paid_date == paid_date
        assert inst.updated_at >= old_updated_at

    def test_installment_mark_unpaid(self, modifiable_plan):
        """Test Installment mark_unpaid method."""
        inst = modifiable_plan.installments[0]

        # First mark as paid
        inst.mark_full_payment(date(2024, 1, 31))

        # Then mark as unpaid
        inst.mark_unpaid()

        assert inst.status == PaymentStatus.PENDING
        assert inst.paid_date is None

    def test_installment_set_amount(self, modifiable_plan):
        """Test Installment set_amount method."""
        inst = modifiable_plan.installments[0]

        inst.set_amount(Decimal("350.00"))

        assert inst.amount == Decimal("350.00")

    def test_installment_set_amount_invalid(self, modifiable_plan):
        """Test Installment set_amount with invalid value."""
        inst = modifiable_plan.installments[0]

        with pytest.raises(ValueError, match="greater than zero"):
            inst.set_amount(Decimal("0"))


@pytest.mark.unit
class TestPartialPaymentSerialization:
    """Test serialization with partial payments."""

    def test_backward_compatibility_loading_old_plans(self):
        """Test that plans without amount_paid field load correctly."""
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
        assert plan.installments[0].amount_paid == Decimal("0")
        assert plan.installments[0].remaining_amount == Decimal("100.00")

        # Check installment 2 defaults (even though marked paid)
        # This is OK - we'll update amount_paid when we call mark_paid()
        assert plan.installments[1].amount_paid == Decimal("0")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
