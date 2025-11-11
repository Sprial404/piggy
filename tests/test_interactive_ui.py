from datetime import date
from decimal import Decimal

import pytest

from piggy.installment_plan import InstallmentPlan, PaymentStatus
from piggy.interactive import (
    get_installment_status_symbol,
    get_plan_status_icon,
)
from piggy.menu import CommandResult, NavigationContext
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
    """Create a plan manager with temporary storage."""
    storage_dir = tmp_path / "test_plans"
    return PlanManager(storage_dir)


@pytest.fixture
def nav_context(plan_manager):
    """Create a navigation context with plan manager."""
    from piggy.interactive import ContextKeys

    context = NavigationContext()
    context.set_data(ContextKeys.PLAN_MANAGER, plan_manager)
    return context


@pytest.mark.unit
class TestStatusIcons:
    """Tests for status icon helper functions."""

    def test_get_installment_status_symbol_paid(self, sample_plan):
        """Test status symbol for paid installment."""
        inst = sample_plan.installments[0]
        inst.mark_full_payment(date(2024, 2, 1))

        symbol = get_installment_status_symbol(inst)
        assert symbol == "✓"

    def test_get_installment_status_symbol_partially_paid(self, sample_plan):
        """Test status symbol for partially paid installment."""
        inst = sample_plan.installments[0]
        inst.mark_partial_payment(Decimal("150.00"), date(2024, 2, 1))

        symbol = get_installment_status_symbol(inst)
        assert symbol == "◐"

    def test_get_installment_status_symbol_unpaid(self, sample_plan):
        """Test status symbol for unpaid installment."""
        inst = sample_plan.installments[0]

        symbol = get_installment_status_symbol(inst)
        assert symbol == "○"

    def test_get_plan_status_icon_fully_paid(self, sample_plan):
        """Test status icon for fully paid plan."""
        for inst in sample_plan.installments:
            inst.mark_full_payment(date(2024, 2, 1))

        icon = get_plan_status_icon(sample_plan)
        assert icon == "✓"

    def test_get_plan_status_icon_unpaid(self, sample_plan):
        """Test status icon for unpaid plan."""
        icon = get_plan_status_icon(sample_plan)
        assert icon == "○"

    @pytest.mark.parametrize(
        "amount_paid,expected_symbol",
        [
            (Decimal("0"), "○"),
            (Decimal("150.00"), "◐"),
            (Decimal("300.00"), "✓"),
        ],
    )
    def test_installment_symbols_parametrized(self, sample_plan, amount_paid, expected_symbol):
        """Test installment symbols with various payment amounts."""
        inst = sample_plan.installments[0]
        if amount_paid > 0:
            if amount_paid == inst.amount:
                inst.mark_full_payment(date(2024, 2, 1))
            else:
                inst.mark_partial_payment(amount_paid, date(2024, 2, 1))

        symbol = get_installment_status_symbol(inst)
        assert symbol == expected_symbol


@pytest.mark.ui
class TestMarkPaymentUI:
    """Tests for mark_payment interactive function."""

    def test_mark_payment_full_amount(self, mocker, nav_context, sample_plan):
        """Test marking payment with full amount."""
        from piggy.interactive import ContextKeys, mark_payment

        nav_context.get_data(ContextKeys.PLAN_MANAGER).add_plan("test_plan", sample_plan)

        mocker.patch("piggy.interactive.print_heading")
        mocker.patch("piggy.interactive.select_plan", return_value=("test_plan", sample_plan))
        mocker.patch("piggy.interactive._display_installments")
        mocker.patch("piggy.interactive.get_input", side_effect=["1", "1"])
        mocker.patch("piggy.interactive.get_decimal_input", return_value=Decimal("300.00"))
        mocker.patch("piggy.interactive.get_date_input", return_value=date(2024, 2, 1))

        result = mark_payment(nav_context)

        assert isinstance(result, CommandResult)
        assert "marked as paid" in result.message.lower()
        assert sample_plan.installments[0].status == PaymentStatus.PAID

    def test_mark_payment_partial_amount(self, mocker, nav_context, sample_plan):
        """Test marking payment with partial amount."""
        from piggy.interactive import ContextKeys, mark_payment

        nav_context.get_data(ContextKeys.PLAN_MANAGER).add_plan("test_plan", sample_plan)

        mocker.patch("piggy.interactive.print_heading")
        mocker.patch("piggy.interactive.select_plan", return_value=("test_plan", sample_plan))
        mocker.patch("piggy.interactive._display_installments")
        mocker.patch("piggy.interactive.get_input", side_effect=["1", "1"])
        mocker.patch("piggy.interactive.get_decimal_input", return_value=Decimal("150.00"))
        mocker.patch("piggy.interactive.get_date_input", return_value=date(2024, 2, 1))

        result = mark_payment(nav_context)
        assert "partial payment" in result.message.lower()
        assert sample_plan.installments[0].is_partially_paid
        assert sample_plan.installments[0].amount_paid == Decimal("150.00")

    def test_mark_payment_no_plan_selected(self, mocker, nav_context):
        """Test mark payment when no plan is selected."""
        from piggy.interactive import mark_payment

        mocker.patch("piggy.interactive.print_heading")
        mocker.patch("piggy.interactive.select_plan", return_value=None)

        result = mark_payment(nav_context)

        assert "no plan selected" in result.message.lower()

    def test_mark_payment_already_paid(self, mocker, nav_context, sample_plan):
        """Test marking payment on already paid installment."""
        from piggy.interactive import ContextKeys, mark_payment

        # Mark installment as paid
        sample_plan.installments[0].mark_full_payment(date(2024, 1, 15))
        nav_context.get_data(ContextKeys.PLAN_MANAGER).add_plan("test_plan", sample_plan)

        mocker.patch("piggy.interactive.print_heading")
        mocker.patch("piggy.interactive.select_plan", return_value=("test_plan", sample_plan))
        mocker.patch("piggy.interactive._display_installments")
        mocker.patch("piggy.interactive.get_input", side_effect=["1", "1"])

        result = mark_payment(nav_context)

        assert "already fully paid" in result.message.lower()


@pytest.mark.ui
class TestSearchFilterPlansUI:
    """Tests for search_filter_plans interactive function."""

    def test_search_by_merchant(self, mocker, nav_context):
        """Test filtering plans by merchant name."""
        from piggy.interactive import ContextKeys, search_filter_plans

        plan_manager = nav_context.get_data(ContextKeys.PLAN_MANAGER)
        plan1 = InstallmentPlan.build(
            merchant_name="Apple Store",
            total_amount=Decimal("1200.00"),
            purchase_date=date(2024, 1, 1),
            num_installments=4,
            days_between=30,
            first_payment_date=date(2024, 2, 1),
        )
        plan2 = InstallmentPlan.build(
            merchant_name="Best Buy",
            total_amount=Decimal("900.00"),
            purchase_date=date(2024, 1, 1),
            num_installments=3,
            days_between=30,
            first_payment_date=date(2024, 2, 1),
        )
        plan_manager.add_plan("plan1", plan1)
        plan_manager.add_plan("plan2", plan2)

        mocker.patch("piggy.interactive.print_heading")
        mocker.patch("piggy.interactive.print")
        mocker.patch("piggy.interactive.get_input", side_effect=["1", "Apple"])

        result = search_filter_plans(nav_context)

        assert "1 of 2" in result.message

    def test_filter_no_results(self, mocker, nav_context):
        """Test filtering with no matching results."""
        from piggy.interactive import ContextKeys, search_filter_plans

        plan_manager = nav_context.get_data(ContextKeys.PLAN_MANAGER)
        plan1 = InstallmentPlan.build(
            merchant_name="Apple Store",
            total_amount=Decimal("1200.00"),
            purchase_date=date(2024, 1, 1),
            num_installments=4,
            days_between=30,
            first_payment_date=date(2024, 2, 1),
        )
        plan_manager.add_plan("plan1", plan1)

        mocker.patch("piggy.interactive.print_heading")
        mocker.patch("piggy.interactive.print")
        mocker.patch("piggy.interactive.get_input", side_effect=["1", "Nonexistent"])

        result = search_filter_plans(nav_context)

        assert "no plans match" in result.message.lower()

    def test_show_all_plans(self, mocker, nav_context):
        """Test showing all plans without filtering."""
        from piggy.interactive import ContextKeys, search_filter_plans

        plan_manager = nav_context.get_data(ContextKeys.PLAN_MANAGER)
        plan1 = InstallmentPlan.build(
            merchant_name="Store 1",
            total_amount=Decimal("1000.00"),
            purchase_date=date(2024, 1, 1),
            num_installments=4,
            days_between=30,
            first_payment_date=date(2024, 2, 1),
        )
        plan_manager.add_plan("plan1", plan1)

        mocker.patch("piggy.interactive.print_heading")
        mocker.patch("piggy.interactive.print")
        mocker.patch("piggy.interactive.get_input", return_value="5")

        result = search_filter_plans(nav_context)

        assert "1 of 1" in result.message


@pytest.mark.unit
@pytest.mark.parametrize(
    "status,expected",
    [
        (PaymentStatus.PAID, True),
        (PaymentStatus.PENDING, False),
        (PaymentStatus.OVERDUE, False),
    ],
)
def test_installment_is_paid_parametrized(sample_plan, status, expected):
    """Test installment is_paid property with various statuses."""
    inst = sample_plan.installments[0]
    inst.status = status
    if status == PaymentStatus.PAID:
        inst.paid_date = date(2024, 2, 1)
        inst.amount_paid = inst.amount

    assert inst.is_paid == expected


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
