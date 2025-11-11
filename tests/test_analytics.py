"""
Pytest tests for analytics module.
"""

from datetime import date
from decimal import Decimal

import pytest

from piggy.analytics import (
    filter_plans_by_amount,
    filter_plans_by_merchant,
    filter_plans_by_status,
)
from piggy.installment_plan import InstallmentPlan, PaymentStatus


@pytest.fixture
def sample_plans():
    """Fixture providing sample plans for testing."""
    return {
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


@pytest.mark.unit
class TestFilterPlansByMerchant:
    """Tests for merchant name filtering."""

    def test_exact_match(self, sample_plans):
        """Test exact merchant name match."""
        result = filter_plans_by_merchant(sample_plans, "Apple Store")
        assert len(result) == 1
        assert "plan1" in result

    def test_partial_match(self, sample_plans):
        """Test partial merchant name match."""
        result = filter_plans_by_merchant(sample_plans, "Buy")
        assert len(result) == 1
        assert "plan2" in result

    def test_case_insensitive(self, sample_plans):
        """Test case-insensitive matching."""
        result = filter_plans_by_merchant(sample_plans, "apple")
        assert len(result) == 1
        assert "plan1" in result

    def test_no_match(self, sample_plans):
        """Test no matching merchants."""
        result = filter_plans_by_merchant(sample_plans, "Nonexistent Store")
        assert len(result) == 0

    def test_multiple_matches(self, sample_plans):
        """Test query matching multiple merchants."""
        result = filter_plans_by_merchant(sample_plans, "A")
        assert len(result) == 2
        assert "plan1" in result
        assert "plan3" in result

    def test_empty_query(self, sample_plans):
        """Test empty query returns all plans."""
        result = filter_plans_by_merchant(sample_plans, "")
        assert len(result) == 3


@pytest.fixture
def plans_with_status():
    """Fixture providing plans with different payment statuses."""
    plans = {
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

    for inst in plans["plan1"].installments:
        inst.mark_full_payment(date(2024, 2, 1))

    for inst in plans["plan2"].installments:
        inst.status = PaymentStatus.OVERDUE

    return plans


@pytest.mark.unit
class TestFilterPlansByStatus:
    """Tests for payment status filtering."""

    def test_filter_fully_paid_true(self, plans_with_status):
        """Test filtering for fully paid plans."""
        result = filter_plans_by_status(plans_with_status, fully_paid=True)
        assert len(result) == 1
        assert "plan1" in result

    def test_filter_fully_paid_false(self, plans_with_status):
        """Test filtering for unpaid plans."""
        result = filter_plans_by_status(plans_with_status, fully_paid=False)
        assert len(result) == 2
        assert "plan2" in result
        assert "plan3" in result

    def test_filter_has_overdue_true(self, plans_with_status):
        """Test filtering for plans with overdue payments."""
        result = filter_plans_by_status(plans_with_status, has_overdue=True)
        assert len(result) == 2
        assert "plan2" in result
        assert "plan3" in result

    def test_filter_has_overdue_false(self, plans_with_status):
        """Test filtering for plans without overdue payments."""
        result = filter_plans_by_status(plans_with_status, has_overdue=False)
        assert len(result) == 1
        assert "plan1" in result

    def test_filter_combined(self, plans_with_status):
        """Test combining fully_paid and has_overdue filters."""
        result = filter_plans_by_status(plans_with_status, fully_paid=False, has_overdue=False)
        assert len(result) == 0

    def test_no_filters(self, plans_with_status):
        """Test with no filters returns all plans."""
        result = filter_plans_by_status(plans_with_status)
        assert len(result) == 3


@pytest.fixture
def plans_with_amounts():
    """Fixture providing plans with different amounts."""
    plans = {
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

    plans["plan2"].installments[0].mark_full_payment(date(2024, 2, 1))

    return plans


@pytest.mark.unit
class TestFilterPlansByAmount:
    """Tests for amount range filtering."""

    def test_filter_min_total(self, plans_with_amounts):
        """Test filtering by minimum total amount."""
        result = filter_plans_by_amount(plans_with_amounts, min_total=Decimal("1000.00"))
        assert len(result) == 2
        assert "plan2" in result
        assert "plan3" in result

    def test_filter_max_total(self, plans_with_amounts):
        """Test filtering by maximum total amount."""
        result = filter_plans_by_amount(plans_with_amounts, max_total=Decimal("1000.00"))
        assert len(result) == 2
        assert "plan1" in result
        assert "plan2" in result

    def test_filter_total_range(self, plans_with_amounts):
        """Test filtering by total amount range."""
        result = filter_plans_by_amount(plans_with_amounts, min_total=Decimal("600.00"), max_total=Decimal("1200.00"))
        assert len(result) == 1
        assert "plan2" in result

    @pytest.mark.parametrize(
        "min_remaining,expected_plan",
        [
            (Decimal("1000.00"), "plan3"),
            (Decimal("750.00"), "plan2"),
        ],
    )
    def test_filter_min_remaining_parametrized(self, plans_with_amounts, min_remaining, expected_plan):
        """Test filtering by minimum remaining balance with different values."""
        result = filter_plans_by_amount(plans_with_amounts, min_remaining=min_remaining)
        assert expected_plan in result

    def test_filter_remaining_range(self, plans_with_amounts):
        """Test filtering by remaining balance range."""
        result = filter_plans_by_amount(
            plans_with_amounts, min_remaining=Decimal("500.00"), max_remaining=Decimal("800.00")
        )
        assert len(result) == 2
        assert "plan1" in result
        assert "plan2" in result


@pytest.mark.ui
def test_search_filter_plans_integration(mocker):
    """Example UI test showing how to test interactive functions with mocking."""
    pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
