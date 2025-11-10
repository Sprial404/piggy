"""
Business logic for payment analytics and calculations.

This module contains pure business logic functions for analyzing installment plans,
categorizing payments, and calculating statistics. All functions are pure (no I/O)
and testable.
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
