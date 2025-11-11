import json
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field, ValidationInfo, field_validator


class PaymentStatus(StrEnum):
    """
    Status of an installment payment.

    PENDING: Payment not yet due or awaiting payment
    PAID: Payment successfully completed
    OVERDUE: Payment past due date but not yet paid
    """

    PENDING = "pending"
    PAID = "paid"
    OVERDUE = "overdue"


class Installment(BaseModel):
    installment_number: int = Field(ge=1)
    amount: Decimal = Field(gt=0)
    due_date: date
    status: PaymentStatus = PaymentStatus.PENDING
    paid_date: date | None = None
    amount_paid: Decimal = Field(default=Decimal(0), ge=0)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # noinspection PyNestedDecorators
    # PyCharm incorrectly flags Pydantic's @field_validator + @classmethod pattern as an issue
    # This is the standard Pydantic pattern for field validators
    @field_validator("paid_date", mode="after")
    @classmethod
    def ensure_paid_date(cls, value: date | None, info: ValidationInfo) -> date | None:
        if value is not None and info.data.get("status") != PaymentStatus.PAID:
            raise ValueError("paid_date can only be set when status is PAID")
        return value

    # noinspection PyNestedDecorators
    @field_validator("amount_paid", mode="after")
    @classmethod
    def validate_amount_paid(cls, value: Decimal, info: ValidationInfo) -> Decimal:
        if "amount" in info.data and value > info.data["amount"]:
            raise ValueError("amount_paid cannot exceed installment amount")
        return value

    @property
    def is_paid(self) -> bool:
        """Check if this installment has been paid."""
        return self.status == PaymentStatus.PAID

    @property
    def is_pending(self) -> bool:
        """Check if this installment is pending payment."""
        return self.status == PaymentStatus.PENDING

    @property
    def is_overdue(self) -> bool:
        """Check if this installment is overdue."""
        return self.status == PaymentStatus.OVERDUE

    @property
    def remaining_amount(self) -> Decimal:
        """Calculate remaining amount to be paid."""
        return self.amount - self.amount_paid

    @property
    def is_partially_paid(self) -> bool:
        """Check if this installment is partially paid."""
        return 0 < self.amount_paid < self.amount

    @property
    def is_unpaid(self) -> bool:
        """Check if this installment is completely unpaid (no payments made)."""
        return self.status == PaymentStatus.PENDING and self.amount_paid == 0

    def set_amount(self, new_amount: Decimal) -> None:
        """Set installment amount."""
        if new_amount <= 0:
            raise ValueError("Amount must be greater than zero.")
        self.amount = new_amount
        self.updated_at = datetime.now()

    def set_due_date(self, new_due_date: date) -> None:
        """Set due date."""
        self.due_date = new_due_date
        self.updated_at = datetime.now()

    def set_status(self, new_status: PaymentStatus) -> None:
        """Set payment status."""
        self.status = new_status
        self.updated_at = datetime.now()

    def set_paid_date(self, new_paid_date: date | None) -> None:
        """Set paid date."""
        self.paid_date = new_paid_date
        self.updated_at = datetime.now()

    def set_amount_paid(self, new_amount_paid: Decimal) -> None:
        """
        Set the amount paid directly.

        If the new amount paid equals the full installment amount, the installment
        is automatically marked as PAID with the current date.

        :param new_amount_paid: New amount paid value
        :raises ValueError: If amount_paid exceeds installment amount or is negative
        """
        if new_amount_paid < 0:
            raise ValueError("Amount paid cannot be negative.")
        if new_amount_paid > self.amount:
            raise ValueError(f"Amount paid cannot exceed installment amount of {self.amount}.")
        self.amount_paid = new_amount_paid

        if self.amount_paid == self.amount:
            self.status = PaymentStatus.PAID
            if not self.paid_date:
                self.paid_date = date.today()
        elif self.status == PaymentStatus.PAID:
            self.status = PaymentStatus.PENDING
            self.paid_date = None

        self.updated_at = datetime.now()

    def mark_full_payment(self, paid_date: date) -> None:
        """Mark as paid with date."""
        self.status = PaymentStatus.PAID
        self.paid_date = paid_date
        self.amount_paid = self.amount
        self.updated_at = datetime.now()

    def mark_unpaid(self) -> None:
        """Mark as pending (unpaid) and clear paid date."""
        self.status = PaymentStatus.PENDING
        self.paid_date = None
        self.amount_paid = Decimal(0)
        self.updated_at = datetime.now()

    def mark_partial_payment(self, amount: Decimal, payment_date: date) -> None:
        """
        Record a partial payment by adding it to the amount already paid.

        This method accumulates payments. The amount is added to the existing
        amount_paid. If the total reaches the full installment amount, the
        installment is automatically marked as PAID.

        :param amount: Amount being paid (to be added to existing amount paid).
        :param payment_date: Date of payment
        :raises ValueError: If amount exceeds remaining balance
        """
        new_total_paid = self.amount_paid + amount
        if new_total_paid > self.amount:
            raise ValueError(f"Payment of {amount} would exceed remaining balance of {self.remaining_amount}")

        self.amount_paid = new_total_paid

        if self.amount_paid == self.amount:
            self.status = PaymentStatus.PAID
            self.paid_date = payment_date

        self.updated_at = datetime.now()


class InstallmentPlan(BaseModel):
    merchant_name: str
    total_amount: Decimal = Field(gt=0)
    purchase_date: date
    installments: list[Installment] = Field(min_length=1)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # noinspection PyNestedDecorators
    # PyCharm incorrectly flags Pydantic's @field_validator + @classmethod pattern as an issue
    # This is the standard Pydantic pattern for field validators
    @field_validator("installments", mode="after")
    @classmethod
    def validate_installments(cls, value: list[Installment], info: ValidationInfo) -> list[Installment]:
        num_installments = len(value)

        if num_installments < 1:
            raise ValueError("Must have at least 1 installment")

        # Verify installment numbers are sequential from 1 to n
        installment_numbers = {inst.installment_number for inst in value}
        expected_numbers = set(range(1, num_installments + 1))
        if installment_numbers != expected_numbers:
            raise ValueError(f"Installment numbers must be sequential from 1 to {num_installments}")

        # Verify total of installments matches total_amount
        if "total_amount" in info.data:
            installment_total = sum(inst.amount for inst in value)
            if installment_total != info.data["total_amount"]:
                raise ValueError(
                    f"Sum of installments ({installment_total}) must equal total_amount ({info.data['total_amount']})"
                )

        return value

    @property
    def unpaid_installments(self):
        """Return list of unpaid installments"""
        return [inst for inst in self.installments if inst.status != PaymentStatus.PAID]

    @property
    def num_installments(self) -> int:
        """Get the total number of installments"""
        return len(self.installments)

    @property
    def remaining_balance(self) -> Decimal:
        """Calculate the remaining balance from unpaid installments"""
        return sum((inst.remaining_amount for inst in self.unpaid_installments), start=Decimal(0))

    @property
    def is_fully_paid(self) -> bool:
        """Check if all installments have been paid"""
        return all(inst.status == PaymentStatus.PAID for inst in self.installments)

    @property
    def next_payment_due(self) -> date | None:
        """Get the next payment due date"""
        unpaid = [inst for inst in self.installments if inst.status == PaymentStatus.PENDING]
        if not unpaid:
            return None
        return min(inst.due_date for inst in unpaid)

    def get_overdue_installments(self, as_of: date | None = None) -> list[Installment]:
        """
        Get installments that are overdue.

        :param as_of: Date to check against (defaults to today)
        :return: List of overdue installments
        """
        if as_of is None:
            as_of = date.today()

        return [inst for inst in self.installments if inst.status != PaymentStatus.PAID and inst.due_date < as_of]

    @property
    def has_overdue_payments(self) -> bool:
        """Check if any installments are overdue based on today's date"""
        return len(self.get_overdue_installments()) > 0

    def update_overdue_status(self, as_of: date | None = None) -> int:
        """
        Update status to OVERDUE for unpaid installments past their due date.

        :param as_of: Date to check against (defaults to today)
        :return: Number of installments updated to OVERDUE status
        """
        if as_of is None:
            as_of = date.today()

        updated_count = 0
        for inst in self.installments:
            if inst.status == PaymentStatus.PENDING and inst.due_date < as_of:
                inst.status = PaymentStatus.OVERDUE
                updated_count += 1

        if updated_count > 0:
            self.updated_at = datetime.now()

        return updated_count

    def get_installments(self, numbers: list[int] | None = None) -> list[Installment]:
        """
        Get installments by installment number.

        :param numbers: List of installment numbers (not list indices) to retrieve. If None, returns all installments.
        :return: List of Installment objects
        :raises ValueError: If any installment number does not exist
        """
        if numbers is None:
            return self.installments

        result = []
        num_installments = len(self.installments)

        for num in numbers:
            if num < 1 or num > num_installments:
                raise ValueError(f"Installment #{num} does not exist.")
            result.append(self.installments[num - 1])

        return result

    def get_installment(self, number: int) -> Installment:
        """
        Get a single installment by installment number.

        :param number: Installment number (not list index) to retrieve
        :return: Installment object
        :raises ValueError: If installment number does not exist
        """
        if number < 1 or number > len(self.installments):
            raise ValueError(f"Installment #{number} does not exist.")
        return self.installments[number - 1]

    def set_merchant_name(self, new_name: str) -> None:
        """Set merchant name."""
        self.merchant_name = new_name
        self.updated_at = datetime.now()

    def set_installment_amount(self, number: int, new_amount: Decimal) -> None:
        """
        Set installment amount and recalculate plan total.

        :param number: Installment number to update
        :param new_amount: New installment amount
        :raises ValueError: If installment number does not exist or amount is invalid
        """
        installment = self.get_installment(number)
        old_amount = installment.amount
        installment.set_amount(new_amount)
        self.total_amount = self.total_amount - old_amount + new_amount
        self.updated_at = datetime.now()

    def set_installment_due_date(self, number: int, new_due_date: date) -> None:
        """
        Set installment due date.

        :param number: Installment number to update
        :param new_due_date: New due date
        :raises ValueError: If installment number does not exist
        """
        installment = self.get_installment(number)
        installment.set_due_date(new_due_date)
        self.updated_at = datetime.now()

    def set_installment_paid_date(self, number: int, new_paid_date: date) -> None:
        """
        Set installment paid date.

        :param number: Installment number to update
        :param new_paid_date: New paid date
        :raises ValueError: If installment number does not exist or installment is not paid
        """
        installment = self.get_installment(number)
        if not installment.is_paid:
            raise ValueError(f"Installment #{number} is not marked as paid.")
        installment.set_paid_date(new_paid_date)
        self.updated_at = datetime.now()

    def mark_installment_paid(self, number: int, paid_date: date) -> None:
        """
        Mark installment as paid.

        :param number: Installment number to mark as paid
        :param paid_date: Date the payment was made
        :raises ValueError: If installment number does not exist
        """
        installment = self.get_installment(number)
        installment.mark_full_payment(paid_date)
        self.updated_at = datetime.now()

    def mark_installment_unpaid(self, number: int) -> None:
        """
        Mark installment as unpaid.

        :param number: Installment number to mark as unpaid
        :raises ValueError: If installment number does not exist
        """
        installment = self.get_installment(number)
        installment.mark_unpaid()
        self.updated_at = datetime.now()

    @staticmethod
    def build(
        merchant_name: str,
        total_amount: Decimal,
        purchase_date: date,
        num_installments: int,
        days_between: int,
        first_payment_date: date,
    ) -> "InstallmentPlan":
        """
        Build an installment plan with calculated installments.

        Creates an InstallmentPlan with evenly divided payments scheduled at
        regular intervals.

        :param merchant_name: Name of the merchant
        :param total_amount: Total purchase amount
        :param purchase_date: Date of purchase
        :param num_installments: Number of installment payments
        :param days_between: Days between each payment
        :param first_payment_date: Date of first payment
        :return: Validated InstallmentPlan instance
        :raises ValueError: If validation fails
        """
        from datetime import timedelta

        installment_amount = total_amount / num_installments
        installments = []
        current_date = first_payment_date

        for i in range(1, num_installments + 1):
            installment = Installment(
                installment_number=i, amount=installment_amount, due_date=current_date, status=PaymentStatus.PENDING
            )
            installments.append(installment)
            current_date += timedelta(days=days_between)

        return InstallmentPlan(
            merchant_name=merchant_name,
            total_amount=total_amount,
            purchase_date=purchase_date,
            installments=installments,
        )

    def to_json(self, file_path: str | None = None) -> str:
        """
        Serialize the installment plan to JSON format.

        :param file_path: Optional file path to save JSON
        :return: JSON string representation
        :raises ValueError: If file_path is an existing directory
        :raises OSError: If file write fails or parent directory cannot be created
        """
        from piggy.utils.helpers import ensure_directory

        json_data = self.model_dump(mode="json")
        json_str = json.dumps(json_data, indent=2, default=str)

        if file_path:
            validated_path = ensure_directory(file_path)
            validated_path.write_text(json_str, encoding="utf-8")

        return json_str

    @classmethod
    def from_json(cls, json_data: str) -> "InstallmentPlan":
        """Deserialize an installment plan from JSON string"""
        data = json.loads(json_data)
        return cls.model_validate(data)

    @classmethod
    def from_json_file(cls, file_path: str) -> "InstallmentPlan":
        """Load an installment plan from a JSON file"""
        json_str = Path(file_path).read_text(encoding="utf-8")
        return cls.from_json(json_str)

    def to_csv(self, file_path: str) -> str:
        """
        Export installment plan data to CSV format (flattened structure).

        Creates one row per installment with plan-level data repeated.
        Includes all timestamps and computed properties for data analysis.

        :param file_path: File path to save CSV
        :return: CSV content as string
        :raises ValueError: If file_path is an existing directory
        :raises OSError: If file write fails or parent directory cannot be created
        """
        from piggy.utils.csv_writer import format_value, write_csv_from_dicts
        from piggy.utils.helpers import ensure_directory

        # Validate path before processing
        ensure_directory(file_path)

        headers = [
            "merchant_name",
            "total_amount",
            "purchase_date",
            "created_at",
            "updated_at",
            "installment_number",
            "amount",
            "due_date",
            "status",
            "paid_date",
            "amount_paid",
            "remaining_amount",
            "is_paid",
            "is_pending",
            "is_overdue",
            "is_partially_paid",
        ]

        rows = [
            {
                "merchant_name": self.merchant_name,
                "total_amount": format_value(self.total_amount),
                "purchase_date": format_value(self.purchase_date),
                "created_at": format_value(self.created_at),
                "updated_at": format_value(self.updated_at),
                "installment_number": inst.installment_number,
                "amount": format_value(inst.amount),
                "due_date": format_value(inst.due_date),
                "status": inst.status.value,
                "paid_date": format_value(inst.paid_date),
                "amount_paid": format_value(inst.amount_paid),
                "remaining_amount": format_value(inst.remaining_amount),
                "is_paid": inst.is_paid,
                "is_pending": inst.is_pending,
                "is_overdue": inst.is_overdue,
                "is_partially_paid": inst.is_partially_paid,
            }
            for inst in self.installments
        ]

        return write_csv_from_dicts(headers, rows, file_path)
