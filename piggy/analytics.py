"""
Business logic for payment analytics and calculations.

This module contains pure business logic functions for analyzing installment plans,
categorizing payments, and calculating statistics.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import TypedDict

from piggy.installment_plan import Installment, InstallmentPlan


@dataclass
class PaymentInfo:
    """Information about a payment installment for display purposes."""

    plan_id: str
    merchant: str
    installment: Installment
    days_until_due: int


class CategorizedPayments(TypedDict):
    """Categorized payment installments by due date."""

    all_unpaid: list[PaymentInfo]
    overdue: list[PaymentInfo]
    due_today: list[PaymentInfo]
    upcoming: list[PaymentInfo]
    future: list[PaymentInfo]


class PaymentStatistics(TypedDict):
    """Summary statistics for payment overview."""

    total_plans: int
    fully_paid_count: int
    total_paid: Decimal
    total_remaining: Decimal
    total_unpaid_installments: int
    overdue_total: Decimal
    due_today_total: Decimal
    time_period_totals: dict[int, Decimal]


def group_payments_by_date(payments: list[PaymentInfo]) -> dict[date, list[PaymentInfo]]:
    """
    Group payments by their due date.

    :param payments: List of PaymentInfo objects to group
    :return: Dictionary mapping due_date -> list of PaymentInfo for that date
    """
    grouped: dict[date, list[PaymentInfo]] = {}
    for payment in payments:
        due_date = payment.installment.due_date
        if due_date not in grouped:
            grouped[due_date] = []
        grouped[due_date].append(payment)

    return dict(sorted(grouped.items()))


def categorize_unpaid_installments(
    plans_dict: dict[str, InstallmentPlan], today: date, upcoming_days: int
) -> CategorizedPayments:
    """
    Categorize unpaid installments by due date.

    :param plans_dict: Dictionary of plan_id -> InstallmentPlan
    :param today: Current date
    :param upcoming_days: Number of days to consider as upcoming
    :return: CategorizedPayments with installments sorted by category
    """
    all_unpaid = []
    for plan_id, plan in plans_dict.items():
        # Cache unpaid_installments to avoid repeated property access
        unpaid = plan.unpaid_installments
        for inst in unpaid:
            all_unpaid.append(
                PaymentInfo(
                    plan_id=plan_id,
                    merchant=plan.merchant_name,
                    installment=inst,
                    days_until_due=(inst.due_date - today).days,
                )
            )

    all_unpaid.sort(key=lambda x: x.installment.due_date)

    overdue = [p for p in all_unpaid if p.days_until_due < 0]
    due_today = [p for p in all_unpaid if p.days_until_due == 0]
    upcoming = [p for p in all_unpaid if 0 < p.days_until_due <= upcoming_days]
    future = [p for p in all_unpaid if p.days_until_due > upcoming_days]

    return CategorizedPayments(
        all_unpaid=all_unpaid, overdue=overdue, due_today=due_today, upcoming=upcoming, future=future
    )


def calculate_payment_statistics(
    plans_dict: dict[str, InstallmentPlan], categorized: CategorizedPayments, time_periods: list[int]
) -> PaymentStatistics:
    """
    Calculate summary statistics for payment overview.

    :param plans_dict: Dictionary of plan_id -> InstallmentPlan
    :param categorized: Categorized payments
    :param time_periods: List of time periods (in days) to calculate totals for
    :return: PaymentStatistics with calculated values
    """
    total_plans = len(plans_dict)

    total_remaining = Decimal(0)
    total_paid = Decimal(0)
    fully_paid_count = 0

    for plan in plans_dict.values():
        total_remaining += plan.remaining_balance
        total_paid += sum((inst.amount for inst in plan.installments if inst.is_paid), start=Decimal(0))
        if plan.is_fully_paid:
            fully_paid_count += 1

    overdue_total = sum((p.installment.amount for p in categorized["overdue"]), start=Decimal(0))
    due_today_total = sum((p.installment.amount for p in categorized["due_today"]), start=Decimal(0))

    time_period_totals = {}
    for days in time_periods:
        period_total = overdue_total + due_today_total
        period_total += sum(
            (p.installment.amount for p in categorized["all_unpaid"] if 0 < p.days_until_due <= days), start=Decimal(0)
        )
        time_period_totals[days] = period_total

    return {
        "total_plans": total_plans,
        "fully_paid_count": fully_paid_count,
        "total_paid": total_paid,
        "total_remaining": total_remaining,
        "total_unpaid_installments": len(categorized["all_unpaid"]),
        "overdue_total": overdue_total,
        "due_today_total": due_today_total,
        "time_period_totals": time_period_totals,
    }


def filter_plans_by_merchant(plans_dict: dict[str, InstallmentPlan], merchant_query: str) -> dict[str, InstallmentPlan]:
    """
    Filter plans by merchant name (case-insensitive partial match).

    :param plans_dict: Dictionary of plan_id -> InstallmentPlan
    :param merchant_query: Search query for merchant name
    :return: Filtered dictionary of plans
    """
    query_lower = merchant_query.lower()
    return {plan_id: plan for plan_id, plan in plans_dict.items() if query_lower in plan.merchant_name.lower()}


def filter_plans_by_status(
    plans_dict: dict[str, InstallmentPlan], fully_paid: bool | None = None, has_overdue: bool | None = None
) -> dict[str, InstallmentPlan]:
    """
    Filter plans by payment status.

    :param plans_dict: Dictionary of plan_id -> InstallmentPlan
    :param fully_paid: If True, only fully paid plans; if False, only unpaid plans; if None, no filter
    :param has_overdue: If True, only plans with overdue payments; if False, only plans without overdue; if None, no filter
    :return: Filtered dictionary of plans
    """
    result = plans_dict

    if fully_paid is not None:
        result = {plan_id: plan for plan_id, plan in result.items() if plan.is_fully_paid == fully_paid}

    if has_overdue is not None:
        result = {plan_id: plan for plan_id, plan in result.items() if plan.has_overdue_payments == has_overdue}

    return result


def filter_plans_by_amount(
    plans_dict: dict[str, InstallmentPlan],
    min_total: Decimal | None = None,
    max_total: Decimal | None = None,
    min_remaining: Decimal | None = None,
    max_remaining: Decimal | None = None,
) -> dict[str, InstallmentPlan]:
    """
    Filter plans by amount ranges.

    :param plans_dict: Dictionary of plan_id -> InstallmentPlan
    :param min_total: Minimum total amount
    :param max_total: Maximum total amount
    :param min_remaining: Minimum remaining balance
    :param max_remaining: Maximum remaining balance
    :return: Filtered dictionary of plans
    """
    result = {}
    for plan_id, plan in plans_dict.items():
        if min_total is not None and plan.total_amount < min_total:
            continue
        if max_total is not None and plan.total_amount > max_total:
            continue
        if min_remaining is not None and plan.remaining_balance < min_remaining:
            continue
        if max_remaining is not None and plan.remaining_balance > max_remaining:
            continue
        result[plan_id] = plan

    return result


def filter_plans_by_date(
    plans_dict: dict[str, InstallmentPlan],
    purchase_after: date | None = None,
    purchase_before: date | None = None,
    next_payment_after: date | None = None,
    next_payment_before: date | None = None,
) -> dict[str, InstallmentPlan]:
    """
    Filter plans by date ranges.

    :param plans_dict: Dictionary of plan_id -> InstallmentPlan
    :param purchase_after: Only plans purchased after this date
    :param purchase_before: Only plans purchased before this date
    :param next_payment_after: Only plans with next payment after this date
    :param next_payment_before: Only plans with next payment before this date
    :return: Filtered dictionary of plans
    """
    result = {}
    for plan_id, plan in plans_dict.items():
        if purchase_after is not None and plan.purchase_date < purchase_after:
            continue
        if purchase_before is not None and plan.purchase_date > purchase_before:
            continue

        next_payment = plan.next_payment_due
        if next_payment_after is not None and (next_payment is None or next_payment < next_payment_after):
            continue
        if next_payment_before is not None and (next_payment is None or next_payment > next_payment_before):
            continue

        result[plan_id] = plan

    return result
