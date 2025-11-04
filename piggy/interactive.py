from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from piggy.installment_plan import InstallmentPlan, PaymentStatus
from piggy.menu import (
    MenuInterface, NavigationContext, Menu, Command, CommandResult,
    NavigationAction
)
from piggy.utils.input import get_input, get_decimal_input, get_date_input, get_int_input

PLANS_STORAGE: dict[str, InstallmentPlan] = {}
STORAGE_DIR = Path("data")


def print_heading(heading: str):
    print(f"\n=== {heading} ===\n")


def create_installment_plan(_context: NavigationContext) -> CommandResult:
    print_heading("Create New Installment Plan")

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

    first_payment_date = get_date_input("First payment date", default=purchase_date + timedelta(days=days_between))
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
        PLANS_STORAGE[plan_id] = plan

        return CommandResult(
            message=f"\nInstallment plan created successfully!\nPlan ID: {plan_id}"
        )
    except Exception as e:
        return CommandResult(message=f"Error creating plan: {e}")


def list_installment_plans(_context: NavigationContext) -> CommandResult:
    print_heading("List Installment Plans")

    if not PLANS_STORAGE:
        return CommandResult(message="No installment plans found.")

    for plan_id, plan in PLANS_STORAGE.items():
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

    if not PLANS_STORAGE:
        return CommandResult(message="No installment plans found.")

    print("Available plans:")
    plan_ids = list(PLANS_STORAGE.keys())
    for idx, plan_id in enumerate(plan_ids, 1):
        print(f"{idx}. {plan_id}")

    choice = get_int_input("\nSelect plan number", min_val=1, max_val=len(plan_ids))
    if not choice:
        return CommandResult(message="Invalid selection.")

    plan_id = plan_ids[choice - 1]
    plan = PLANS_STORAGE[plan_id]

    print(f"\n=== {plan.merchant_name} ===")
    print(f"Total Amount: ${plan.total_amount}")
    print(f"Purchase Date: {plan.purchase_date}")
    print(f"Remaining Balance: ${plan.remaining_balance}")
    print(f"Next Payment Due: {plan.next_payment_due or 'N/A'}")
    print(f"\nInstallments:")

    for inst in plan.installments:
        status_symbol = "✓" if inst.status == PaymentStatus.PAID else "○"
        print(f"  {status_symbol} #{inst.installment_number}: ${inst.amount} due {inst.due_date} [{inst.status.value}]")
        if inst.paid_date:
            print(f"     Paid on: {inst.paid_date}")

    context.set_data("selected_plan_id", plan_id)

    return CommandResult(message="\nPress Enter to continue...")


def mark_payment(_context: NavigationContext) -> CommandResult:
    print("\n=== Mark Payment ===\n")

    if not PLANS_STORAGE:
        return CommandResult(message="No installment plans found.")

    print("Available plans:")
    plan_ids = list(PLANS_STORAGE.keys())
    for idx, plan_id in enumerate(plan_ids, 1):
        plan = PLANS_STORAGE[plan_id]
        unpaid_count = len(plan.unpaid_installments)
        paid_count = plan.num_installments - unpaid_count
        print(f"{idx}. {plan_id} ({paid_count} paid, {unpaid_count} unpaid)")

    choice = get_int_input("\nSelect plan number", min_val=1, max_val=len(plan_ids))
    if not choice:
        return CommandResult(message="Invalid selection.")

    plan_id = plan_ids[choice - 1]
    plan = PLANS_STORAGE[plan_id]

    print("\nAll installments:")
    for inst in plan.installments:
        status_symbol = "✓" if inst.status == PaymentStatus.PAID else "○"
        status_text = f" [PAID on {inst.paid_date}]" if inst.status == PaymentStatus.PAID else ""
        print(f"{status_symbol} {inst.installment_number}. Installment #{inst.installment_number}: ${inst.amount} due {inst.due_date}{status_text}")

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
        selected_numbers = [int(num.strip()) for num in installment_input.split(',')]
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

            if not paid_date:
                print(f"Skipping installment #{selected_inst.installment_number} - no date provided.")
                continue

            selected_inst.status = PaymentStatus.PAID
            selected_inst.paid_date = paid_date
            marked_count += 1
            print(f"✓ Installment #{selected_inst.installment_number} marked as paid on {paid_date}")

        if marked_count == 0:
            return CommandResult(message="\nNo installments were marked as paid.")
        elif marked_count == 1:
            return CommandResult(message=f"\n{marked_count} installment marked as paid!")
        else:
            return CommandResult(message=f"\n{marked_count} installments marked as paid!")
    else:
        for selected_inst in selected_installments:
            selected_inst.status = PaymentStatus.PENDING
            selected_inst.paid_date = None
            marked_count += 1
            print(f"○ Installment #{selected_inst.installment_number} marked as unpaid")

        if marked_count == 0:
            return CommandResult(message="\nNo installments were marked as unpaid.")
        elif marked_count == 1:
            return CommandResult(message=f"\n{marked_count} installment marked as unpaid!")
        else:
            return CommandResult(message=f"\n{marked_count} installments marked as unpaid!")


def overview(_context: NavigationContext) -> CommandResult:
    print("\n=== Overview ===\n")

    if not PLANS_STORAGE:
        return CommandResult(message="No installment plans found.")

    today = date.today()
    upcoming_days = 30

    total_plans = len(PLANS_STORAGE)
    total_remaining = sum(plan.remaining_balance for plan in PLANS_STORAGE.values())
    total_paid = sum(
        sum(inst.amount for inst in plan.installments if inst.status == PaymentStatus.PAID)
        for plan in PLANS_STORAGE.values()
    )
    fully_paid_count = sum(1 for plan in PLANS_STORAGE.values() if plan.is_fully_paid)

    all_unpaid = []
    for plan_id, plan in PLANS_STORAGE.items():
        for inst in plan.unpaid_installments:
            all_unpaid.append({
                'plan_id': plan_id,
                'merchant': plan.merchant_name,
                'installment': inst,
                'days_until_due': (inst.due_date - today).days
            })

    all_unpaid.sort(key=lambda x: x['installment'].due_date)

    overdue = [p for p in all_unpaid if p['days_until_due'] < 0]
    due_today = [p for p in all_unpaid if p['days_until_due'] == 0]
    upcoming = [p for p in all_unpaid if 0 < p['days_until_due'] <= upcoming_days]
    future = [p for p in all_unpaid if p['days_until_due'] > upcoming_days]

    overdue_total = sum(p['installment'].amount for p in overdue)
    due_today_total = sum(p['installment'].amount for p in due_today)
    upcoming_total = sum(p['installment'].amount for p in upcoming)
    next_30_days_total = overdue_total + due_today_total + upcoming_total

    print("Summary Statistics")
    print("-" * 50)
    print(f"Total Plans: {total_plans} ({fully_paid_count} fully paid, {total_plans - fully_paid_count} active)")
    print(f"Total Paid: ${total_paid:.2f}")
    print(f"Total Remaining: ${total_remaining:.2f}")
    print(f"Total Unpaid Installments: {len(all_unpaid)}")
    print(f"Total Due in Next {upcoming_days} Days: ${next_30_days_total:.2f}")
    print()

    if overdue:
        print(f"⚠️  OVERDUE PAYMENTS ({len(overdue)})")
        print("-" * 50)
        for p in overdue:
            inst = p['installment']
            days_overdue = abs(p['days_until_due'])
            print(f"  {p['merchant']} - Installment #{inst.installment_number}")
            print(f"    ${inst.amount:.2f} - Due: {inst.due_date} ({days_overdue} days overdue)")
        print()

    if due_today:
        print(f"🔔 DUE TODAY ({len(due_today)})")
        print("-" * 50)
        for p in due_today:
            inst = p['installment']
            print(f"  {p['merchant']} - Installment #{inst.installment_number}")
            print(f"    ${inst.amount:.2f} - Due: {inst.due_date}")
        print()

    if upcoming:
        print(f"📅 UPCOMING (Next {upcoming_days} Days) ({len(upcoming)})")
        print("-" * 50)
        for p in upcoming:
            inst = p['installment']
            days_str = f"in {p['days_until_due']} day" + ("s" if p['days_until_due'] > 1 else "")
            print(f"  {p['merchant']} - Installment #{inst.installment_number}")
            print(f"    ${inst.amount:.2f} - Due: {inst.due_date} ({days_str})")
        print()

    if all_unpaid:
        next_payment = all_unpaid[0]
        inst = next_payment['installment']
        print("Next Payment Due")
        print("-" * 50)
        print(f"  {next_payment['merchant']} - Installment #{inst.installment_number}")
        print(f"  ${inst.amount:.2f} - Due: {inst.due_date}")
        if next_payment['days_until_due'] < 0:
            print(f"  Status: {abs(next_payment['days_until_due'])} days overdue")
        elif next_payment['days_until_due'] == 0:
            print(f"  Status: Due today")
        else:
            print(f"  Status: Due in {next_payment['days_until_due']} days")
        print()

    if future:
        future_total = sum(p['installment'].amount for p in future)
        print(f"Future Payments (Beyond {upcoming_days} Days)")
        print("-" * 50)
        print(f"  Count: {len(future)}")
        print(f"  Total: ${future_total:.2f}")
        print()

    return CommandResult(message="Press Enter to continue...")


def save_plans(_context: NavigationContext) -> CommandResult:
    print("\n=== Save Plans ===\n")

    if not PLANS_STORAGE:
        return CommandResult(message="No installment plans to save.")

    STORAGE_DIR.mkdir(exist_ok=True)

    saved_count = 0
    for plan_id, plan in PLANS_STORAGE.items():
        try:
            file_path = STORAGE_DIR / f"{plan_id}.json"
            plan.to_json(str(file_path))
            saved_count += 1
        except Exception as e:
            print(f"Error saving {plan_id}: {e}")

    return CommandResult(message=f"\nSaved {saved_count} plan(s) to {STORAGE_DIR}")


def load_plans(_context: NavigationContext) -> CommandResult:
    print("\n=== Load Plans ===\n")

    if not STORAGE_DIR.exists():
        return CommandResult(message="No saved plans found.")

    json_files = list(STORAGE_DIR.glob("*.json"))
    if not json_files:
        return CommandResult(message="No saved plans found.")

    loaded_count = 0
    for file_path in json_files:
        try:
            plan = InstallmentPlan.from_json_file(str(file_path))
            plan_id = file_path.stem
            PLANS_STORAGE[plan_id] = plan
            loaded_count += 1
        except Exception as e:
            print(f"Error loading {file_path.name}: {e}")

    return CommandResult(message=f"\nLoaded {loaded_count} plan(s) from {STORAGE_DIR}")


def export_plan_csv(_context: NavigationContext) -> CommandResult:
    print("\n=== Export Plan to CSV ===\n")

    if not PLANS_STORAGE:
        return CommandResult(message="No installment plans found.")

    print("Available plans:")
    plan_ids = list(PLANS_STORAGE.keys())
    for idx, plan_id in enumerate(plan_ids, 1):
        print(f"{idx}. {plan_id}")

    choice = get_int_input("\nSelect plan number", min_val=1, max_val=len(plan_ids))
    if not choice:
        return CommandResult(message="Invalid selection.")

    plan_id = plan_ids[choice - 1]
    plan = PLANS_STORAGE[plan_id]

    STORAGE_DIR.mkdir(exist_ok=True)

    csv_path = STORAGE_DIR / f"{plan_id}.csv"
    try:
        plan.to_csv(str(csv_path))
        return CommandResult(message=f"\nPlan exported to {csv_path}")
    except Exception as e:
        return CommandResult(message=f"Error exporting plan: {e}")


def select_plan(_context: NavigationContext, prompt: str = "Select plan number") -> Optional[tuple[str, InstallmentPlan]]:
    if not PLANS_STORAGE:
        print("No installment plans found.")
        return None

    print("Available plans:")
    plan_ids = list(PLANS_STORAGE.keys())
    for idx, plan_id in enumerate(plan_ids, 1):
        plan = PLANS_STORAGE[plan_id]
        print(f"{idx}. {plan_id} - ${plan.total_amount} ({plan.merchant_name})")

    choice = get_int_input(f"\n{prompt}", min_val=1, max_val=len(plan_ids))
    if not choice:
        return None

    plan_id = plan_ids[choice - 1]
    return plan_id, PLANS_STORAGE[plan_id]


def edit_merchant_name(context: NavigationContext) -> CommandResult:
    print("\n=== Edit Merchant Name ===\n")

    plan_id = context.get_data("edit_plan_id")
    if not plan_id or plan_id not in PLANS_STORAGE:
        return CommandResult(message="No plan selected.")

    plan = PLANS_STORAGE[plan_id]

    print(f"\nCurrent merchant name: {plan.merchant_name}")
    new_name = get_input("New merchant name")

    if not new_name:
        return CommandResult(message="Merchant name cannot be empty.")

    plan.merchant_name = new_name

    new_plan_id = f"{new_name}_{plan.purchase_date.isoformat()}"
    if new_plan_id != plan_id:
        PLANS_STORAGE[new_plan_id] = PLANS_STORAGE.pop(plan_id)
        context.set_data("edit_plan_id", new_plan_id)

    return CommandResult(message=f"\nMerchant name updated to: {new_name}")


def edit_installment_amount(context: NavigationContext) -> CommandResult:
    print("\n=== Edit Installment Amount ===\n")

    plan_id = context.get_data("edit_plan_id")
    if not plan_id or plan_id not in PLANS_STORAGE:
        return CommandResult(message="No plan selected.")

    plan = PLANS_STORAGE[plan_id]

    print("\nInstallments:")
    for inst in plan.installments:
        status_symbol = "✓" if inst.status == PaymentStatus.PAID else "○"
        print(f"  {status_symbol} #{inst.installment_number}: ${inst.amount} due {inst.due_date}")

    inst_num = get_int_input("\nSelect installment number to edit", min_val=1, max_val=plan.num_installments)
    if not inst_num:
        return CommandResult(message="Invalid selection.")

    selected_inst = plan.installments[inst_num - 1]

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
        message=f"\nInstallment #{inst_num} amount updated to ${new_amount}\nNew total: ${plan.total_amount}"
    )


def edit_installment_due_date(context: NavigationContext) -> CommandResult:
    """Edit the due date of a specific installment"""
    print("\n=== Edit Installment Due Date ===\n")

    plan_id = context.get_data("edit_plan_id")
    if not plan_id or plan_id not in PLANS_STORAGE:
        return CommandResult(message="No plan selected.")

    plan = PLANS_STORAGE[plan_id]

    print("\nInstallments:")
    for inst in plan.installments:
        status_symbol = "✓" if inst.status == PaymentStatus.PAID else "○"
        print(f"  {status_symbol} #{inst.installment_number}: ${inst.amount} due {inst.due_date}")

    inst_num = get_int_input("\nSelect installment number to edit", min_val=1, max_val=plan.num_installments)
    if not inst_num:
        return CommandResult(message="Invalid selection.")

    selected_inst = plan.installments[inst_num - 1]

    print(f"\nCurrent due date: {selected_inst.due_date}")
    new_due_date = get_date_input("New due date")

    if not new_due_date:
        return CommandResult(message="Due date is required.")

    selected_inst.due_date = new_due_date

    return CommandResult(message=f"\nInstallment #{inst_num} due date updated to {new_due_date}")


def edit_installment_paid_date(context: NavigationContext) -> CommandResult:
    print("\n=== Edit Installment Paid Date ===\n")

    plan_id = context.get_data("edit_plan_id")
    if not plan_id or plan_id not in PLANS_STORAGE:
        return CommandResult(message="No plan selected.")

    plan = PLANS_STORAGE[plan_id]

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

    plan_id = context.get_data("edit_plan_id")
    if not plan_id or plan_id not in PLANS_STORAGE:
        return CommandResult(message="No plan selected.")

    plan = PLANS_STORAGE[plan_id]

    print(f"\nPlan: {plan.merchant_name}")
    print(f"Total: ${plan.total_amount}")
    print(f"Remaining: ${plan.remaining_balance}")

    confirm = get_input("\nAre you sure you want to delete this plan? (yes/no)", default="no")

    if confirm.lower() != 'yes':
        return CommandResult(message="Deletion cancelled.")

    del PLANS_STORAGE[plan_id]

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


def save_and_exit(_context: NavigationContext) -> CommandResult:
    if PLANS_STORAGE:
        STORAGE_DIR.mkdir(exist_ok=True)
        saved_count = 0
        for plan_id, plan in PLANS_STORAGE.items():
            try:
                file_path = STORAGE_DIR / f"{plan_id}.json"
                plan.to_json(str(file_path))
                saved_count += 1
            except Exception as e:
                print(f"Error saving {plan_id}: {e}")

        print(f"\nSaved {saved_count} plan(s) to {STORAGE_DIR}")

    return CommandResult(action=NavigationAction.EXIT)


def exit_without_saving(_context: NavigationContext) -> CommandResult:
    return CommandResult(action=NavigationAction.EXIT)


def main():
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

    if STORAGE_DIR.exists() and any(STORAGE_DIR.glob("*.json")):
        print("Loading saved plans...")
        load_plans(NavigationContext())
        print()

    MenuInterface(main_menu).run()

    print("\nThank you for using Installment Plan Tracker!")


if __name__ == '__main__':
    main()
