from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

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


@dataclass
class PaymentInfo:
    """Information about a payment installment for display purposes."""
    plan_id: str
    merchant: str
    installment: Installment
    days_until_due: int


@dataclass
class CategorizedPayments:
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
    total_paid: float
    total_remaining: float
    total_unpaid_installments: int
    overdue_total: float
    due_today_total: float
    upcoming_total: float
    next_30_days_total: float


def print_heading(heading: str):
    print(f"\n=== {heading} ===\n")


def create_installment_plan(context: NavigationContext) -> CommandResult:
    print_heading("Create New Installment Plan")
    plan_manager = context.get_data("plan_manager")

    merchant_name = get_input("Merchant name")
    if not merchant_name:
        return CommandResult(message="Merchant name is required.")

    total_amount = get_decimal_input("Total amount")
    if not total_amount or total_amount <= 0:
        return CommandResult(message="Valid total amount is required.")

    purchase_date = get_date_input("Purchase date", default=date.today())
    if not purchase_date:
        return CommandResult(message="Purchase date is required.")

    num_installments = get_int_input("Number of installments", min_val=1)
    if not num_installments or num_installments < 1:
        return CommandResult(message="Valid number of installments is required.")

    installment_amount = total_amount / num_installments

    print(f"\nEach installment will be: ${installment_amount:.2f}")

    print("\nPayment frequency:")
    print("1. Monthly")
    print("2. Fortnightly")
    print("3. Weekly")
    print("4. Custom")

    frequency_choice = get_input("Choose frequency", default="2")

    match frequency_choice:
        case "1":
            days_between = 30
        case "2":
            days_between = 14
        case "3":
            days_between = 7
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

        plan_id = f"{merchant_name}_{purchase_date.isoformat()}"
        plan_manager.add_plan(plan_id, plan)

        return CommandResult(
            message=f"\nInstallment plan created successfully!\nPlan ID: {plan_id}"
        )
    except Exception as e:
        return CommandResult(message=f"Error creating plan: {e}")


def list_installment_plans(context: NavigationContext) -> CommandResult:
    print_heading("List Installment Plans")
    plan_manager = context.get_data("plan_manager")

    if not plan_manager.has_plans():
        return CommandResult(message="No installment plans found.")

    for plan_id, plan in plan_manager.list_plans().items():
        print(f"\nPlan ID: {plan_id}")
        print(f"  Merchant: {plan.merchant_name}")
        print(f"  Total: ${plan.total_amount}")
        print(f"  Remaining: ${plan.remaining_balance}")
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
    print(f"Total Amount: ${plan.total_amount}")
    print(f"Purchase Date: {plan.purchase_date}")
    print(f"Remaining Balance: ${plan.remaining_balance}")
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
    line = f"{indent}{status_symbol} #{inst.installment_number}: ${inst.amount} due {inst.due_date}"

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
        print(f"{status_symbol} {inst.installment_number}. Installment #{inst.installment_number}: ${inst.amount} due {inst.due_date}{status_text}")


def select_installment(plan: InstallmentPlan) -> Optional[Installment]:
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

            selected_inst.status = PaymentStatus.PAID
            selected_inst.paid_date = paid_date
            marked_count += 1

            print(f"✓ Installment #{selected_inst.installment_number} marked as paid on {paid_date}")

        return CommandResult(message=_format_marking_result(marked_count, "paid"))
    else:
        for selected_inst in selected_installments:
            selected_inst.status = PaymentStatus.PENDING
            selected_inst.paid_date = None
            marked_count += 1

            print(f"○ Installment #{selected_inst.installment_number} marked as unpaid")

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
    total_remaining = sum(plan.remaining_balance for plan in plans_dict.values())
    total_paid = sum(
        sum(inst.amount for inst in plan.installments if inst.status == PaymentStatus.PAID)
        for plan in plans_dict.values()
    )
    fully_paid_count = sum(1 for plan in plans_dict.values() if plan.is_fully_paid)

    overdue_total = sum(p.installment.amount for p in categorized.overdue)
    due_today_total = sum(p.installment.amount for p in categorized.due_today)
    upcoming_total = sum(p.installment.amount for p in categorized.upcoming)
    next_30_days_total = overdue_total + due_today_total + upcoming_total

    return PaymentStatistics(
        total_plans=total_plans,
        fully_paid_count=fully_paid_count,
        total_paid=total_paid,
        total_remaining=total_remaining,
        total_unpaid_installments=len(categorized.all_unpaid),
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
    print(f"Total Paid: ${stats.total_paid:.2f}")
    print(f"Total Remaining: ${stats.total_remaining:.2f}")
    print(f"Total Unpaid Installments: {stats.total_unpaid_installments}")
    print(f"Total Due in Next {upcoming_days} Days: ${stats.next_30_days_total:.2f}")
    print()

    if categorized.overdue:
        print(f"⚠️  OVERDUE PAYMENTS ({len(categorized.overdue)})")
        print("-" * 50)
        for p in categorized.overdue:
            inst = p.installment
            days_overdue = abs(p.days_until_due)
            print(f"  {p.merchant} - Installment #{inst.installment_number}")
            print(f"    ${inst.amount:.2f} - Due: {inst.due_date} ({days_overdue} days overdue)")
        print()

    if categorized.due_today:
        print(f"🔔 DUE TODAY ({len(categorized.due_today)})")
        print("-" * 50)
        for p in categorized.due_today:
            inst = p.installment
            print(f"  {p.merchant} - Installment #{inst.installment_number}")
            print(f"    ${inst.amount:.2f} - Due: {inst.due_date}")
        print()

    if categorized.upcoming:
        print(f"📅 UPCOMING (Next {upcoming_days} Days) ({len(categorized.upcoming)})")
        print("-" * 50)
        for p in categorized.upcoming:
            inst = p.installment
            days_str = f"in {p.days_until_due} day" + ("s" if p.days_until_due > 1 else "")
            print(f"  {p.merchant} - Installment #{inst.installment_number}")
            print(f"    ${inst.amount:.2f} - Due: {inst.due_date} ({days_str})")
        print()

    if categorized.all_unpaid:
        next_payment = categorized.all_unpaid[0]
        inst = next_payment.installment
        print("Next Payment Due")
        print("-" * 50)
        print(f"  {next_payment.merchant} - Installment #{inst.installment_number}")
        print(f"  ${inst.amount:.2f} - Due: {inst.due_date}")
        if next_payment.days_until_due < 0:
            print(f"  Status: {abs(next_payment.days_until_due)} days overdue")
        elif next_payment.days_until_due == 0:
            print(f"  Status: Due today")
        else:
            print(f"  Status: Due in {next_payment.days_until_due} days")
        print()

    if categorized.future:
        future_total = sum(p.installment.amount for p in categorized.future)
        print(f"Future Payments (Beyond {upcoming_days} Days)")
        print("-" * 50)
        print(f"  Count: {len(categorized.future)}")
        print(f"  Total: ${future_total:.2f}")
        print()


def overview(context: NavigationContext) -> CommandResult:
    print("\n=== Overview ===\n")
    plan_manager = context.get_data("plan_manager")

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
    plan_manager = context.get_data("plan_manager")

    saved_count, _ = _save_all_plans(plan_manager)

    if saved_count == 0:
        return CommandResult(message="No installment plans to save.")

    return CommandResult(
        message=f"\nSaved {saved_count} plan(s) to {plan_manager.storage_dir}"
    )


def load_plans(context: NavigationContext) -> CommandResult:
    print("\n=== Load Plans ===\n")
    plan_manager = context.get_data("plan_manager")

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
    plan_manager = context.get_data("plan_manager")

    plan_manager.storage_dir.mkdir(exist_ok=True)

    csv_path = plan_manager.storage_dir / f"{plan_id}.csv"
    try:
        plan.to_csv(str(csv_path))
        return CommandResult(message=f"\nPlan exported to {csv_path}")
    except Exception as e:
        return CommandResult(message=f"Error exporting plan: {e}")


def select_plan(
    context: NavigationContext,
    prompt: str = "Select plan number"
) -> Optional[tuple[str, InstallmentPlan]]:
    plan_manager = context.get_data("plan_manager")

    if not plan_manager.has_plans():
        print("No installment plans found.")
        return None

    print("Available plans:")
    plans_dict = plan_manager.list_plans()
    plan_ids = list(plans_dict.keys())
    for idx, plan_id in enumerate(plan_ids, 1):
        plan = plans_dict[plan_id]
        print(f"{idx}. {plan_id} - ${plan.total_amount} ({plan.merchant_name})")

    choice = get_int_input(f"\n{prompt}", min_val=1, max_val=len(plan_ids))
    if not choice:
        return None

    plan_id = plan_ids[choice - 1]
    return plan_id, plan_manager.get_plan(plan_id)


def edit_merchant_name(context: NavigationContext) -> CommandResult:
    print("\n=== Edit Merchant Name ===\n")
    plan_manager = context.get_data("plan_manager")

    plan_id = context.get_data("edit_plan_id")
    plan = plan_manager.get_plan(plan_id) if plan_id else None

    if not plan:
        return CommandResult(message="No plan selected.")

    print(f"\nCurrent merchant name: {plan.merchant_name}")
    new_name = get_input("New merchant name")

    if not new_name:
        return CommandResult(message="Merchant name cannot be empty.")

    plan.merchant_name = new_name

    new_plan_id = f"{new_name}_{plan.purchase_date.isoformat()}"
    if new_plan_id != plan_id:
        plan_manager.remove_plan(plan_id)
        plan_manager.add_plan(new_plan_id, plan)
        context.set_data("edit_plan_id", new_plan_id)

    return CommandResult(message=f"\nMerchant name updated to: {new_name}")


def edit_installment_amount(context: NavigationContext) -> CommandResult:
    print("\n=== Edit Installment Amount ===\n")
    plan_manager = context.get_data("plan_manager")

    plan_id = context.get_data("edit_plan_id")
    plan = plan_manager.get_plan(plan_id) if plan_id else None

    if not plan:
        return CommandResult(message="No plan selected.")

    selected_inst = select_installment(plan)
    if not selected_inst:
        return CommandResult(message="Invalid selection.")

    if selected_inst.status == PaymentStatus.PAID:
        print("\nWarning: This installment has already been paid.")
        confirm = get_input("Continue editing? (y/n)", default="n")
        if confirm.lower() != 'y':
            return CommandResult(message="Edit cancelled.")

    print(f"\nCurrent amount: ${selected_inst.amount}")
    new_amount = get_decimal_input("New amount")

    if not new_amount or new_amount <= 0:
        return CommandResult(message="Valid amount is required.")

    old_total = sum(inst.amount for inst in plan.installments)
    difference = new_amount - selected_inst.amount

    selected_inst.amount = new_amount

    plan.total_amount = old_total + difference

    return CommandResult(
        message=f"\nInstallment #{selected_inst.installment_number} amount updated to ${new_amount}\nNew total: ${plan.total_amount}"
    )


def edit_installment_due_date(context: NavigationContext) -> CommandResult:
    """Edit the due date of a specific installment"""
    print("\n=== Edit Installment Due Date ===\n")
    plan_manager = context.get_data("plan_manager")

    plan_id = context.get_data("edit_plan_id")
    plan = plan_manager.get_plan(plan_id) if plan_id else None

    if not plan:
        return CommandResult(message="No plan selected.")

    selected_inst = select_installment(plan)
    if not selected_inst:
        return CommandResult(message="Invalid selection.")

    print(f"\nCurrent due date: {selected_inst.due_date}")
    new_due_date = get_date_input("New due date")

    if not new_due_date:
        return CommandResult(message="Due date is required.")

    selected_inst.due_date = new_due_date

    return CommandResult(message=f"\nInstallment #{selected_inst.installment_number} due date updated to {new_due_date}")


def edit_installment_paid_date(context: NavigationContext) -> CommandResult:
    print("\n=== Edit Installment Paid Date ===\n")
    plan_manager = context.get_data("plan_manager")

    plan_id = context.get_data("edit_plan_id")
    plan = plan_manager.get_plan(plan_id) if plan_id else None

    if not plan:
        return CommandResult(message="No plan selected.")

    paid_installments = [inst for inst in plan.installments if inst.status == PaymentStatus.PAID]

    if not paid_installments:
        return CommandResult(message="No paid installments to edit.")

    print("\nPaid installments:")
    for inst in paid_installments:
        print(f"  {inst.installment_number}. Installment #{inst.installment_number}: ${inst.amount} - Paid on {inst.paid_date}")

    inst_num = get_int_input("\nSelect installment number to edit", min_val=1, max_val=plan.num_installments)
    if not inst_num:
        return CommandResult(message="Invalid selection.")

    selected_inst = plan.installments[inst_num - 1]

    if selected_inst.status != PaymentStatus.PAID:
        return CommandResult(message=f"Installment #{inst_num} is not marked as paid.")

    print(f"\nCurrent paid date: {selected_inst.paid_date}")
    new_paid_date = get_date_input("New paid date", default=selected_inst.paid_date)

    if not new_paid_date:
        return CommandResult(message="Paid date is required.")

    selected_inst.paid_date = new_paid_date

    return CommandResult(message=f"\nInstallment #{inst_num} paid date updated to {new_paid_date}")


def delete_plan(context: NavigationContext) -> CommandResult:
    print("\n=== Delete Plan ===\n")
    plan_manager = context.get_data("plan_manager")

    plan_id = context.get_data("edit_plan_id")
    plan = plan_manager.get_plan(plan_id) if plan_id else None

    if not plan:
        return CommandResult(message="No plan selected.")

    print(f"\nPlan: {plan.merchant_name}")
    print(f"Total: ${plan.total_amount}")
    print(f"Remaining: ${plan.remaining_balance}")

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

    context.set_data("edit_plan_id", plan_id)

    print(f"\nEditing plan: {plan.merchant_name}")
    print(f"Total: ${plan.total_amount}")
    print(f"Remaining: ${plan.remaining_balance}")
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
    plan_manager = context.get_data("plan_manager")

    saved_count, _ = _save_all_plans(plan_manager)
    if saved_count > 0:
        print(f"\nSaved {saved_count} plan(s) to {plan_manager.storage_dir}")

    return CommandResult(action=NavigationAction.EXIT)


def exit_without_saving(_context: NavigationContext) -> CommandResult:
    return CommandResult(action=NavigationAction.EXIT)


def main():
    project_dir = get_project_root()
    storage_dir = project_dir / "data"

    plan_manager = PlanManager(storage_dir)

    context = NavigationContext()
    context.set_data("plan_manager", plan_manager)

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
    for error in errors:
        print(error)
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
