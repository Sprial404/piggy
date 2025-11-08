from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import IntEnum
from typing import Any, Callable, TypedDict

from pydantic import ValidationError

from piggy.installment_plan import InstallmentPlan, PaymentStatus, Installment
from piggy.menu import (
    MenuInterface, NavigationContext, Menu, Command, CommandResult,
    NavigationAction
)
from piggy.plan_manager import PlanManager
from piggy.utils import get_project_root
from piggy.utils.input import (
    get_input, get_decimal_input, get_date_input, get_int_input
)


class PaymentFrequency(IntEnum):
    """Common payment frequencies in days."""
    MONTHLY = 30
    FORTNIGHTLY = 14
    WEEKLY = 7


class ContextKeys:
    """Constants for NavigationContext data keys."""
    PLAN_MANAGER = "plan_manager"
    EDIT_PLAN_ID = "edit_plan_id"


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


@dataclass
class PaymentStatistics:
    """Summary statistics for payment overview."""
    total_plans: int
    fully_paid_count: int
    total_paid: Decimal
    total_remaining: Decimal
    total_unpaid_installments: int
    overdue_total: Decimal
    due_today_total: Decimal
    upcoming_total: Decimal
    next_30_days_total: Decimal


def generate_plan_id(merchant_name: str, purchase_date: date, plan_manager: PlanManager | None = None) -> str:
    """
    Generate a unique plan ID from merchant name and purchase date.

    If a plan with the same merchant and date already exists, appends a counter
    to ensure uniqueness (e.g., merchant_YYYY-MM-DD_2).

    :param merchant_name: Name of the merchant
    :param purchase_date: Date of purchase
    :param plan_manager: Optional PlanManager to check for existing IDs
    :return: Unique plan ID in format: merchant_YYYY-MM-DD or merchant_YYYY-MM-DD_N
    """
    base_id = f"{merchant_name}_{purchase_date.isoformat()}"

    if plan_manager is None:
        return base_id

    plan_id = base_id
    counter = 2

    while plan_manager.get_plan(plan_id) is not None:
        plan_id = f"{base_id}_{counter}"
        counter += 1

    return plan_id


def print_heading(heading: str) -> None:
    print(f"\n=== {heading} ===\n")


def format_currency(amount: Decimal) -> str:
    """
    Format a Decimal amount as currency.

    :param amount: Amount to format
    :return: Formatted currency string with $ prefix and 2 decimal places
    """
    return f"${amount:.2f}"


def create_installment_plan(context: NavigationContext) -> CommandResult:
    print_heading("Create New Installment Plan")
    plan_manager = context.get_data(ContextKeys.PLAN_MANAGER)

    merchant_name = get_input("Merchant name")
    if not merchant_name:
        return CommandResult(message="Merchant name is required.")

    total_amount = get_decimal_input("Total amount")
    purchase_date = get_date_input("Purchase date", default=date.today())
    num_installments = get_int_input("Number of installments", min_val=1, default=4)

    installment_amount = total_amount / num_installments

    print(f"\nEach installment will be: {format_currency(installment_amount)}")

    print("\nPayment frequency:")
    print("1. Monthly")
    print("2. Fortnightly")
    print("3. Weekly")
    print("4. Custom")

    frequency_choice = get_input("Choose frequency", default="2")

    match frequency_choice:
        case "1":
            days_between = PaymentFrequency.MONTHLY
        case "2":
            days_between = PaymentFrequency.FORTNIGHTLY
        case "3":
            days_between = PaymentFrequency.WEEKLY
        case "4":
            days_between = get_int_input("Days between payments", min_val=1)
            if not days_between:
                return CommandResult(message="Valid days between payments is required.")
        case _:
            return CommandResult(message="Invalid frequency choice.")

    first_payment_date = get_date_input(
        "First payment date",
        default=purchase_date + timedelta(days=days_between)
    )
    if not first_payment_date:
        return CommandResult(message="First payment date is required.")

    try:
        plan = InstallmentPlan.build(
            merchant_name=merchant_name,
            total_amount=total_amount,
            purchase_date=purchase_date,
            num_installments=num_installments,
            days_between=days_between,
            first_payment_date=first_payment_date
        )

        plan_id = generate_plan_id(merchant_name, purchase_date, plan_manager)
        plan_manager.add_plan(plan_id, plan)

        return CommandResult(
            message=f"\nInstallment plan created successfully!\nPlan ID: {plan_id}"
        )
    except (ValueError, ValidationError) as e:
        return CommandResult(message=f"Error creating plan: {e}")


def list_installment_plans(context: NavigationContext) -> CommandResult:
    print_heading("List Installment Plans")
    plan_manager = context.get_data(ContextKeys.PLAN_MANAGER)

    if not plan_manager.has_plans():
        return CommandResult(message="No installment plans found.")

    for plan_id, plan in plan_manager.list_plans().items():
        print(f"\nPlan ID: {plan_id}")
        print(f"  Merchant: {plan.merchant_name}")
        print(f"  Total: {format_currency(plan.total_amount)}")
        print(f"  Remaining: {format_currency(plan.remaining_balance)}")
        print(f"  Installments: {len(plan.unpaid_installments)}/{plan.num_installments} remaining")
        print(f"  Next due: {plan.next_payment_due or 'N/A'}")
        print(f"  Status: {'Fully Paid' if plan.is_fully_paid else 'Active'}")

    return CommandResult(message="\nPress Enter to continue...")


def view_plan_details(context: NavigationContext) -> CommandResult:
    print("\n=== View Plan Details ===\n")

    result = select_plan(context)
    if not result:
        return CommandResult(message="No plan selected.")

    plan_id, plan = result

    print(f"\n=== {plan.merchant_name} ===")
    print(f"Total Amount: {format_currency(plan.total_amount)}")
    print(f"Purchase Date: {plan.purchase_date}")
    print(f"Remaining Balance: {format_currency(plan.remaining_balance)}")
    print(f"Next Payment Due: {plan.next_payment_due or 'N/A'}")
    print(f"\nInstallments:")

    for inst in plan.installments:
        print(format_installment_line(inst, show_status=True))
        if inst.paid_date:
            print(f"     Paid on: {inst.paid_date}")

    return CommandResult(message="\nPress Enter to continue...")


def format_installment_line(
    inst: Installment,
    show_status: bool = False,
    show_paid_date_inline: bool = False,
    indent: str = "  "
) -> str:
    """
    Format an installment as a display line.

    :param inst: Installment to format
    :param show_status: Include status value in brackets
    :param show_paid_date_inline: Include paid date inline (vs separate line)
    :param indent: Indentation string
    :return: Formatted installment line
    """
    status_symbol = "✓" if inst.status == PaymentStatus.PAID else "○"
    line = f"{indent}{status_symbol} #{inst.installment_number}: {format_currency(inst.amount)} due {inst.due_date}"

    if show_status:
        line += f" [{inst.status.value}]"

    if show_paid_date_inline and inst.status == PaymentStatus.PAID and inst.paid_date:
        line += f" [PAID on {inst.paid_date}]"

    return line


def _display_installments(plan: InstallmentPlan) -> None:
    """
    Display all installments with their current status.

    :param plan: InstallmentPlan to display
    """
    print("\nAll installments:")
    for inst in plan.installments:
        status_symbol = "✓" if inst.status == PaymentStatus.PAID else "○"
        status_text = f" [PAID on {inst.paid_date}]" if inst.status == PaymentStatus.PAID else ""
        print(f"{status_symbol} {inst.installment_number}. Installment #{inst.installment_number}: "
              f"{format_currency(inst.amount)} due {inst.due_date}{status_text}")


def select_installment(plan: InstallmentPlan) -> Installment | None:
    """
    Display installments and prompt user to select one.

    :param plan: InstallmentPlan to select from
    :return: Selected Installment or None if cancelled
    """
    print("\nInstallments:")
    for inst in plan.installments:
        print(format_installment_line(inst))

    inst_num = get_int_input("\nSelect installment number to edit", min_val=1, max_val=plan.num_installments)
    if not inst_num:
        return None

    return plan.installments[inst_num - 1]


def _parse_installment_numbers(input_str: str) -> list[int]:
    """
    Parse comma-separated installment numbers from user input.

    :param input_str: User input string (e.g., "1,2,3" or "1")
    :return: List of installment numbers
    :raises ValueError: If input contains invalid numbers
    """
    return [int(num.strip()) for num in input_str.split(',')]


def _format_marking_result(count: int, action: str) -> str:
    """
    Format the result message for marking installments.

    :param count: Number of installments marked
    :param action: Action performed ("paid" or "unpaid")
    :return: Formatted message string
    """
    if count == 0:
        return f"\nNo installments were marked as {action}."
    elif count == 1:
        return f"\n{count} installment marked as {action}!"
    else:
        return f"\n{count} installments marked as {action}!"


def mark_payment(context: NavigationContext) -> CommandResult:
    print("\n=== Mark Payment ===\n")

    result = select_plan(context)
    if not result:
        return CommandResult(message="No plan selected.")

    plan_id, plan = result
    _display_installments(plan)

    print("\nWhat would you like to do?")
    print("1. Mark as paid")
    print("2. Mark as unpaid")
    action = get_input("Choose action", default="1")
    if action not in ["1", "2"]:
        return CommandResult(message="Invalid action selected.")

    mark_as_paid = (action == "1")

    print("\nYou can select multiple installments (e.g., '1,2,3' or just '1')")
    if mark_as_paid:
        installment_input = get_input("Select installment number(s) to mark as paid")
    else:
        installment_input = get_input("Select installment number(s) to mark as unpaid")

    if not installment_input:
        return CommandResult(message="No installments selected.")

    try:
        selected_numbers = _parse_installment_numbers(installment_input)
    except ValueError:
        return CommandResult(message="Invalid input. Please use comma-separated numbers.")

    try:
        selected_installments = plan.get_installments(selected_numbers)
    except ValueError as e:
        return CommandResult(message=str(e))

    for inst in selected_installments:
        if mark_as_paid and inst.status == PaymentStatus.PAID:
            print(f"Note: Installment #{inst.installment_number} is already marked as paid.")
        elif not mark_as_paid and inst.status != PaymentStatus.PAID:
            print(f"Note: Installment #{inst.installment_number} is already marked as unpaid.")

    marked_count = 0
    if mark_as_paid:
        for selected_inst in selected_installments:
            paid_date = get_date_input(
                f"Payment date for installment #{selected_inst.installment_number}",
                default=selected_inst.due_date
            )

            selected_inst.mark_paid(paid_date)
            marked_count += 1

            print(f"✓ Installment #{selected_inst.installment_number} marked as paid on {paid_date}")

        plan.updated_at = datetime.now()
        return CommandResult(message=_format_marking_result(marked_count, "paid"))
    else:
        for selected_inst in selected_installments:
            selected_inst.mark_unpaid()
            marked_count += 1

            print(f"○ Installment #{selected_inst.installment_number} marked as unpaid")

        plan.updated_at = datetime.now()
        return CommandResult(message=_format_marking_result(marked_count, "unpaid"))


def _calculate_payment_statistics(
    plans_dict: dict[str, InstallmentPlan],
    categorized: CategorizedPayments
) -> PaymentStatistics:
    """
    Calculate summary statistics for payment overview.

    :param plans_dict: Dictionary of plan_id -> InstallmentPlan
    :param categorized: Categorized payments
    :return: PaymentStatistics with calculated values
    """
    total_plans = len(plans_dict)
    total_remaining = sum((plan.remaining_balance for plan in plans_dict.values()), start=Decimal(0))
    total_paid = sum(
        (sum((inst.amount for inst in plan.installments if inst.status == PaymentStatus.PAID), start=Decimal(0))
         for plan in plans_dict.values()),
        start=Decimal(0)
    )
    fully_paid_count = sum(1 for plan in plans_dict.values() if plan.is_fully_paid)

    overdue_total = sum((p.installment.amount for p in categorized['overdue']), start=Decimal(0))
    due_today_total = sum((p.installment.amount for p in categorized['due_today']), start=Decimal(0))
    upcoming_total = sum((p.installment.amount for p in categorized['upcoming']), start=Decimal(0))
    next_30_days_total = overdue_total + due_today_total + upcoming_total

    return PaymentStatistics(
        total_plans=total_plans,
        fully_paid_count=fully_paid_count,
        total_paid=total_paid,
        total_remaining=total_remaining,
        total_unpaid_installments=len(categorized['all_unpaid']),
        overdue_total=overdue_total,
        due_today_total=due_today_total,
        upcoming_total=upcoming_total,
        next_30_days_total=next_30_days_total
    )


def _categorize_unpaid_installments(
    plans_dict: dict[str, InstallmentPlan],
    today: date,
    upcoming_days: int
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
        for inst in plan.unpaid_installments:
            all_unpaid.append(PaymentInfo(
                plan_id=plan_id,
                merchant=plan.merchant_name,
                installment=inst,
                days_until_due=(inst.due_date - today).days
            ))

    all_unpaid.sort(key=lambda x: x.installment.due_date)

    overdue = [p for p in all_unpaid if p.days_until_due < 0]
    due_today = [p for p in all_unpaid if p.days_until_due == 0]
    upcoming = [p for p in all_unpaid if 0 < p.days_until_due <= upcoming_days]
    future = [p for p in all_unpaid if p.days_until_due > upcoming_days]

    return CategorizedPayments(
        all_unpaid=all_unpaid,
        overdue=overdue,
        due_today=due_today,
        upcoming=upcoming,
        future=future
    )


def _display_payment_overview(
    stats: PaymentStatistics,
    categorized: CategorizedPayments,
    upcoming_days: int
) -> None:
    """
    Display payment overview information.

    :param stats: Payment statistics
    :param categorized: Categorized payments
    :param upcoming_days: Number of days considered as upcoming
    """
    print("Summary Statistics")
    print("-" * 50)
    active_count = stats.total_plans - stats.fully_paid_count
    print(f"Total Plans: {stats.total_plans} ({stats.fully_paid_count} fully paid, {active_count} active)")
    print(f"Total Paid: {format_currency(stats.total_paid)}")
    print(f"Total Remaining: {format_currency(stats.total_remaining)}")
    print(f"Total Unpaid Installments: {stats.total_unpaid_installments}")
    print(f"Total Due in Next {upcoming_days} Days: {format_currency(stats.next_30_days_total)}")
    print()

    if categorized['overdue']:
        print(f"⚠️  OVERDUE PAYMENTS ({len(categorized['overdue'])})")
        print("-" * 50)
        for p in categorized['overdue']:
            inst = p.installment
            days_overdue = abs(p.days_until_due)
            print(f"  {p.merchant} - Installment #{inst.installment_number}")
            print(f"    {format_currency(inst.amount)} - Due: {inst.due_date} ({days_overdue} days overdue)")
        print()

    if categorized['due_today']:
        print(f"🔔 DUE TODAY ({len(categorized['due_today'])})")
        print("-" * 50)
        for p in categorized['due_today']:
            inst = p.installment
            print(f"  {p.merchant} - Installment #{inst.installment_number}")
            print(f"    {format_currency(inst.amount)} - Due: {inst.due_date}")
        print()

    if categorized['upcoming']:
        print(f"📅 UPCOMING (Next {upcoming_days} Days) ({len(categorized['upcoming'])})")
        print("-" * 50)
        for p in categorized['upcoming']:
            inst = p.installment
            days_str = f"in {p.days_until_due} day" + ("s" if p.days_until_due > 1 else "")
            print(f"  {p.merchant} - Installment #{inst.installment_number}")
            print(f"    {format_currency(inst.amount)} - Due: {inst.due_date} ({days_str})")
        print()

    if categorized['all_unpaid']:
        next_payment = categorized['all_unpaid'][0]
        inst = next_payment.installment
        print("Next Payment Due")
        print("-" * 50)
        print(f"  {next_payment.merchant} - Installment #{inst.installment_number}")
        print(f"  {format_currency(inst.amount)} - Due: {inst.due_date}")
        if next_payment.days_until_due < 0:
            print(f"  Status: {abs(next_payment.days_until_due)} days overdue")
        elif next_payment.days_until_due == 0:
            print(f"  Status: Due today")
        else:
            print(f"  Status: Due in {next_payment.days_until_due} days")
        print()

    if categorized['future']:
        future_total = sum(p.installment.amount for p in categorized['future'])
        print(f"Future Payments (Beyond {upcoming_days} Days)")
        print("-" * 50)
        print(f"  Count: {len(categorized['future'])}")
        print(f"  Total: {format_currency(future_total)}")
        print()


def overview(context: NavigationContext) -> CommandResult:
    print("\n=== Overview ===\n")
    plan_manager = context.get_data(ContextKeys.PLAN_MANAGER)

    if not plan_manager.has_plans():
        return CommandResult(message="No installment plans found.")

    today = date.today()
    upcoming_days = 30
    plans_dict = plan_manager.list_plans()

    for plan in plans_dict.values():
        plan.update_overdue_status(today)

    categorized = _categorize_unpaid_installments(plans_dict, today, upcoming_days)
    stats = _calculate_payment_statistics(plans_dict, categorized)
    _display_payment_overview(stats, categorized, upcoming_days)

    return CommandResult(message="Press Enter to continue...")


def _save_all_plans(plan_manager: PlanManager) -> tuple[int, list[str]]:
    """
    Save all plans and print any errors.

    :param plan_manager: PlanManager instance
    :return: Tuple of (saved_count, errors)
    """
    if not plan_manager.has_plans():
        return 0, []

    saved_count, errors = plan_manager.save_all()
    for error in errors:
        print(error)

    return saved_count, errors


def save_plans(context: NavigationContext) -> CommandResult:
    print("\n=== Save Plans ===\n")
    plan_manager = context.get_data(ContextKeys.PLAN_MANAGER)

    saved_count, _ = _save_all_plans(plan_manager)

    if saved_count == 0:
        return CommandResult(message="No installment plans to save.")

    return CommandResult(
        message=f"\nSaved {saved_count} plan(s) to {plan_manager.storage_dir}"
    )


def load_plans(context: NavigationContext) -> CommandResult:
    print("\n=== Load Plans ===\n")
    plan_manager = context.get_data(ContextKeys.PLAN_MANAGER)

    loaded_count, errors = plan_manager.load_all()

    if loaded_count == 0 and not errors:
        return CommandResult(message="No saved plans found.")

    for error in errors:
        print(error)

    return CommandResult(
        message=f"\nLoaded {loaded_count} plan(s) from {plan_manager.storage_dir}"
    )


def export_plan_csv(context: NavigationContext) -> CommandResult:
    print("\n=== Export Plan to CSV ===\n")

    result = select_plan(context)
    if not result:
        return CommandResult(message="No plan selected.")

    plan_id, plan = result
    plan_manager = context.get_data(ContextKeys.PLAN_MANAGER)

    plan_manager.storage_dir.mkdir(exist_ok=True)

    csv_path = plan_manager.get_plan_file_path(plan_id, "csv")
    try:
        plan.to_csv(str(csv_path))
        return CommandResult(message=f"\nPlan exported to {csv_path}")
    except (OSError, IOError) as e:
        return CommandResult(message=f"Error exporting plan: {e}")


def select_plan(
    context: NavigationContext,
    prompt: str = "Select plan number"
) -> tuple[str, InstallmentPlan] | None:
    plan_manager = context.get_data(ContextKeys.PLAN_MANAGER)

    if not plan_manager.has_plans():
        print("No installment plans found.")
        return None

    print("Available plans:")
    plans_dict = plan_manager.list_plans()
    plan_ids = list(plans_dict.keys())
    for idx, plan_id in enumerate(plan_ids, 1):
        plan = plans_dict[plan_id]
        print(f"{idx}. {plan_id} - {format_currency(plan.total_amount)} ({plan.merchant_name})")

    choice = get_int_input(f"\n{prompt}", min_val=1, max_val=len(plan_ids))
    if not choice:
        return None

    plan_id = plan_ids[choice - 1]
    return plan_id, plan_manager.get_plan(plan_id)


def edit_merchant_name(context: NavigationContext) -> CommandResult:
    print("\n=== Edit Merchant Name ===\n")
    plan_manager = context.get_data(ContextKeys.PLAN_MANAGER)

    plan_id = context.get_data(ContextKeys.EDIT_PLAN_ID)
    plan = plan_manager.get_plan(plan_id) if plan_id else None

    if not plan:
        return CommandResult(message="No plan selected.")

    print(f"\nCurrent merchant name: {plan.merchant_name}")
    new_name = get_input("New merchant name")

    if not new_name:
        return CommandResult(message="Merchant name cannot be empty.")

    plan.set_merchant_name(new_name)

    new_plan_id = generate_plan_id(new_name, plan.purchase_date, plan_manager)
    if new_plan_id != plan_id:
        plan_manager.remove_plan(plan_id)
        plan_manager.add_plan(new_plan_id, plan)
        context.set_data(ContextKeys.EDIT_PLAN_ID, new_plan_id)

    return CommandResult(message=f"\nMerchant name updated to: {new_name}")


def _edit_installment_field(
    context: NavigationContext,
    heading: str,
    field_name: str,
    get_current_value: Callable[[Installment], Any],
    prompt_new_value: Callable[[], Any],
    validate_value: Callable[[Any], tuple[bool, str]],
    apply_update: Callable[[InstallmentPlan, Installment, Any], str],
    warn_if_paid: bool = False,
    select_installment_fn: Callable[[InstallmentPlan], Installment | None] | None = None
) -> CommandResult:
    """
    Generic helper for editing installment fields.

    :param context: Navigation context
    :param heading: Heading to display
    :param field_name: Name of field being edited (for messages)
    :param get_current_value: Function(installment) -> current value
    :param prompt_new_value: Function() -> new value from user input
    :param validate_value: Function(value) -> (is_valid, error_message)
    :param apply_update: Function(plan, installment, new_value) -> success_message
    :param warn_if_paid: Whether to warn if installment is already paid
    :param select_installment_fn: Optional function(plan) -> installment for custom selection logic
    :return: CommandResult
    """
    print(f"\n=== {heading} ===\n")
    plan_manager = context.get_data(ContextKeys.PLAN_MANAGER)

    plan_id = context.get_data(ContextKeys.EDIT_PLAN_ID)
    plan = plan_manager.get_plan(plan_id) if plan_id else None

    if not plan:
        return CommandResult(message="No plan selected.")

    selector = select_installment_fn if select_installment_fn else select_installment
    selected_inst = selector(plan)
    if not selected_inst:
        return CommandResult(message="Invalid selection.")

    if warn_if_paid and selected_inst.status == PaymentStatus.PAID:
        print("\nWarning: This installment has already been paid.")
        confirm = get_input("Continue editing? (y/n)", default="n")
        if confirm.lower() != 'y':
            return CommandResult(message="Edit cancelled.")

    current_value = get_current_value(selected_inst)
    print(f"\nCurrent {field_name}: {current_value}")

    new_value = prompt_new_value()

    is_valid, error_msg = validate_value(new_value)
    if not is_valid:
        return CommandResult(message=error_msg)

    success_msg = apply_update(plan, selected_inst, new_value)

    return CommandResult(message=success_msg)


def edit_installment_amount(context: NavigationContext) -> CommandResult:
    def apply_amount_update(plan, installment, new_amount):
        plan.set_installment_amount(installment.installment_number, new_amount)
        return f"\nInstallment #{installment.installment_number} amount updated to {format_currency(new_amount)}"\
               f"\nNew total: {format_currency(plan.total_amount)}"

    return _edit_installment_field(
        context=context,
        heading="Edit Installment Amount",
        field_name="amount",
        get_current_value=lambda inst: format_currency(inst.amount),
        prompt_new_value=lambda: get_decimal_input("New amount"),
        validate_value=lambda val: (True, "") if val and val > 0 else (False, "Valid amount is required."),
        apply_update=apply_amount_update,
        warn_if_paid=True
    )


def edit_installment_due_date(context: NavigationContext) -> CommandResult:
    """Edit the due date of a specific installment"""
    def apply_due_date_update(plan, installment, new_due_date):
        plan.set_installment_due_date(installment.installment_number, new_due_date)
        return f"\nInstallment #{installment.installment_number} due date updated to {new_due_date}"

    return _edit_installment_field(
        context=context,
        heading="Edit Installment Due Date",
        field_name="due date",
        get_current_value=lambda inst: inst.due_date,
        prompt_new_value=lambda: get_date_input("New due date"),
        validate_value=lambda val: (True, "") if val else (False, "Due date is required."),
        apply_update=apply_due_date_update,
        warn_if_paid=False
    )


def _select_paid_installment(plan: InstallmentPlan) -> Installment | None:
    """Select from paid installments only, showing paid dates."""
    paid_installments = [inst for inst in plan.installments if inst.status == PaymentStatus.PAID]

    if not paid_installments:
        print("No paid installments to edit.")
        return None

    print("Paid installments:")
    for inst in paid_installments:
        print(f"  {inst.installment_number}. Installment #{inst.installment_number}: {format_currency(inst.amount)}"
              f" - Paid on {inst.paid_date}")

    inst_num = get_int_input("\nSelect installment number to edit", min_val=1, max_val=plan.num_installments)
    if not inst_num:
        return None

    selected_inst = plan.installments[inst_num - 1]

    if selected_inst.status != PaymentStatus.PAID:
        print(f"Installment #{inst_num} is not marked as paid.")
        return None

    return selected_inst


def edit_installment_paid_date(context: NavigationContext) -> CommandResult:
    def apply_paid_date_update(plan, installment, new_paid_date):
        plan.set_installment_paid_date(installment.installment_number, new_paid_date)
        return f"\nInstallment #{installment.installment_number} paid date updated to {new_paid_date}"

    return _edit_installment_field(
        context=context,
        heading="Edit Installment Paid Date",
        field_name="paid date",
        get_current_value=lambda inst: inst.paid_date or "Not set",
        prompt_new_value=lambda: get_date_input("New paid date", default=None),
        validate_value=lambda val: (True, "") if val else (False, "Paid date is required."),
        apply_update=apply_paid_date_update,
        warn_if_paid=False,
        select_installment_fn=_select_paid_installment
    )


def delete_plan(context: NavigationContext) -> CommandResult:
    print("\n=== Delete Plan ===\n")
    plan_manager = context.get_data(ContextKeys.PLAN_MANAGER)

    plan_id = context.get_data(ContextKeys.EDIT_PLAN_ID)
    plan = plan_manager.get_plan(plan_id) if plan_id else None

    if not plan:
        return CommandResult(message="No plan selected.")

    print(f"\nPlan: {plan.merchant_name}")
    print(f"Total: {format_currency(plan.total_amount)}")
    print(f"Remaining: {format_currency(plan.remaining_balance)}")

    confirm = get_input(
        "\nAre you sure you want to delete this plan? (yes/no)",
        default="no"
    )

    if confirm.lower() != 'yes':
        return CommandResult(message="Deletion cancelled.")

    plan_manager.remove_plan(plan_id)
    context.clear_data("edit_plan_id")

    return CommandResult(
        action=NavigationAction.POP,
        message=f"\nPlan '{plan_id}' deleted successfully."
    )


def edit_plan_menu(context: NavigationContext) -> CommandResult:
    print("\n=== Edit Plan ===\n")

    result = select_plan(context, "Select plan to edit")
    if not result:
        return CommandResult(message="No plan selected.")

    plan_id, plan = result

    context.set_data(ContextKeys.EDIT_PLAN_ID, plan_id)

    print(f"\nEditing plan: {plan.merchant_name}")
    print(f"Total: {format_currency(plan.total_amount)}")
    print(f"Remaining: {format_currency(plan.remaining_balance)}")
    print()

    edit_menu = Menu(f"Edit: {plan.merchant_name}")
    edit_menu.add_command("1", Command("Edit Merchant Name", edit_merchant_name))
    edit_menu.add_command("2", Command("Edit Installment Amount", edit_installment_amount))
    edit_menu.add_command("3", Command("Edit Installment Due Date", edit_installment_due_date))
    edit_menu.add_command("4", Command("Edit Installment Paid Date", edit_installment_paid_date))
    edit_menu.add_command("5", Command("Delete Plan", delete_plan))
    edit_menu.add_back_command()

    return CommandResult(
        action=NavigationAction.PUSH,
        target_menu=edit_menu
    )


def save_and_exit(context: NavigationContext) -> CommandResult:
    plan_manager = context.get_data(ContextKeys.PLAN_MANAGER)

    saved_count, _ = _save_all_plans(plan_manager)
    if saved_count > 0:
        print(f"\nSaved {saved_count} plan(s) to {plan_manager.storage_dir}")

    return CommandResult(action=NavigationAction.EXIT)


def exit_without_saving(_context: NavigationContext) -> CommandResult:
    return CommandResult(action=NavigationAction.EXIT)


def main() -> None:
    project_dir = get_project_root()
    storage_dir = project_dir / "data"

    plan_manager = PlanManager(storage_dir)

    context = NavigationContext()
    context.set_data(ContextKeys.PLAN_MANAGER, plan_manager)

    main_menu = Menu("Installment Plan Tracker")
    main_menu.add_command("o", Command("Overview", overview))
    main_menu.add_command("1", Command("Create New Plan", create_installment_plan))
    main_menu.add_command("2", Command("List All Plans", list_installment_plans))
    main_menu.add_command("3", Command("View Plan Details", view_plan_details))
    main_menu.add_command("4", Command("Mark Payment", mark_payment))
    main_menu.add_command("5", Command("Edit Plan", edit_plan_menu))

    data_menu = Menu("Data Management")
    data_menu.add_command("1", Command("Save Plans", save_plans))
    data_menu.add_command("2", Command("Load Plans", load_plans))
    data_menu.add_command("3", Command("Export Plan to CSV", export_plan_csv))
    data_menu.add_back_command()

    main_menu.add_submenu("6", data_menu)
    main_menu.add_command("e", Command("Save and Exit", save_and_exit))
    main_menu.add_command("q", Command("Exit without Saving", exit_without_saving))

    loaded_count, errors = plan_manager.load_all()
    if loaded_count > 0:
        print(f"Loaded {loaded_count} saved plan(s)")
    if errors:
        print("Errors occurred while loading plans:")
        for error in errors:
            print(f"  - {error}")
    if loaded_count > 0 or errors:
        print()

    if loaded_count > 0:
        today = date.today()
        for plan in plan_manager.list_plans().values():
            plan.update_overdue_status(today)

    MenuInterface(main_menu, context).run()

    print("\nThank you for using Installment Plan Tracker!")


if __name__ == '__main__':
    main()
