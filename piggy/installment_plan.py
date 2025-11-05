import csv
import json
from datetime import date
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, ValidationInfo, field_validator


class PaymentStatus(StrEnum):
    PENDING = "pending"
    PAID = "paid"
    OVERDUE = "overdue"
    FAILED = "failed"


class Installment(BaseModel):
    installment_number: int = Field(ge=1)
    amount: Decimal = Field(gt=0)
    due_date: date
    status: PaymentStatus = PaymentStatus.PENDING
    paid_date: Optional[date] = None

    # noinspection PyNestedDecorators
    @field_validator('paid_date', mode='after')
    @classmethod
    def ensure_paid_date(cls, value: Optional[date], info: ValidationInfo) -> Optional[date]:
        if value is not None and info.data.get('status') != PaymentStatus.PAID:
            raise ValueError("paid_date can only be set when status is PAID")
        return value


class InstallmentPlan(BaseModel):
    merchant_name: str
    total_amount: Decimal = Field(gt=0)
    purchase_date: date
    installments: list[Installment] = Field(min_length=1)

    # noinspection PyNestedDecorators
    @field_validator('installments', mode='after')
    @classmethod
    def validate_installments(cls, value: list[Installment], info: ValidationInfo) -> list[Installment]:
        num_installments = len(value)

        if num_installments < 1:
            raise ValueError("Must have at least 1 installment")

        # Verify installment numbers are sequential from 1 to n
        installment_numbers = sorted(inst.installment_number for inst in value)
        expected_numbers = list(range(1, num_installments + 1))
        if installment_numbers != expected_numbers:
            raise ValueError(
                f"Installment numbers must be sequential from 1 to {num_installments}"
            )

        # Verify total of installments matches total_amount
        if 'total_amount' in info.data:
            installment_total = sum(inst.amount for inst in value)
            if installment_total != info.data['total_amount']:
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
        total = Decimal()
        for inst in self.unpaid_installments:
            total += inst.amount
        return total

    @property
    def is_fully_paid(self) -> bool:
        """Check if all installments have been paid"""
        return all(inst.status == PaymentStatus.PAID for inst in self.installments)

    @property
    def next_payment_due(self) -> Optional[date]:
        """Get the next payment due date"""
        unpaid = [
            inst for inst in self.installments
            if inst.status == PaymentStatus.PENDING
        ]
        if not unpaid:
            return None
        return min(inst.due_date for inst in unpaid)

    def get_overdue_installments(self, as_of: Optional[date] = None) -> list[Installment]:
        """
        Get installments that are overdue.

        :param as_of: Date to check against (defaults to today)
        :return: List of overdue installments
        """
        if as_of is None:
            as_of = date.today()

        return [
            inst for inst in self.installments
            if inst.status != PaymentStatus.PAID and inst.due_date < as_of
        ]

    @property
    def has_overdue_payments(self) -> bool:
        """Check if any installments are overdue based on today's date"""
        return len(self.get_overdue_installments()) > 0

    def update_overdue_status(self, as_of: Optional[date] = None) -> int:
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

        lookup = {inst.installment_number: inst for inst in self.installments}
        result = []

        for num in numbers:
            if num not in lookup:
                raise ValueError(f"Installment #{num} does not exist.")
            result.append(lookup[num])

        return result

    @staticmethod
    def build(
        merchant_name: str,
        total_amount: Decimal,
        purchase_date: date,
        num_installments: int,
        days_between: int,
        first_payment_date: date
    ) -> 'InstallmentPlan':
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
                installment_number=i,
                amount=installment_amount,
                due_date=current_date,
                status=PaymentStatus.PENDING
            )
            installments.append(installment)
            current_date += timedelta(days=days_between)

        return InstallmentPlan(
            merchant_name=merchant_name,
            total_amount=total_amount,
            purchase_date=purchase_date,
            installments=installments
        )

    def to_json(self, file_path: Optional[str] = None) -> str:
        """Serialize the installment plan to JSON format"""
        json_data = self.model_dump(mode='json')
        json_str = json.dumps(json_data, indent=2, default=str)
        
        if file_path:
            Path(file_path).write_text(json_str, encoding='utf-8')
        
        return json_str

    @classmethod
    def from_json(cls, json_data: str) -> 'InstallmentPlan':
        """Deserialize an installment plan from JSON string"""
        data = json.loads(json_data)
        return cls.model_validate(data)

    @classmethod
    def from_json_file(cls, file_path: str) -> 'InstallmentPlan':
        """Load an installment plan from a JSON file"""
        json_str = Path(file_path).read_text(encoding='utf-8')
        return cls.from_json(json_str)

    def to_csv(self, file_path: str) -> None:
        """Export installment plan data to CSV format"""
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Write header
            writer.writerow(['Field', 'Value'])
            
            # Write plan metadata
            writer.writerow(['Merchant Name', self.merchant_name])
            writer.writerow(['Total Amount', str(self.total_amount)])
            writer.writerow(['Purchase Date', self.purchase_date.isoformat()])
            writer.writerow(['Number of Installments', self.num_installments])
            writer.writerow(['Remaining Balance', str(self.remaining_balance)])
            writer.writerow(['Is Fully Paid', self.is_fully_paid])
            next_due = self.next_payment_due
            writer.writerow(['Next Payment Due', next_due.isoformat() if next_due else 'None'])
            writer.writerow([])  # Empty row
            
            # Write installments header
            writer.writerow(['Installment Number', 'Amount', 'Due Date', 'Status', 'Paid Date'])
            
            # Write installments
            for inst in self.installments:
                writer.writerow([
                    inst.installment_number,
                    str(inst.amount),
                    inst.due_date.isoformat(),
                    inst.status.value,
                    inst.paid_date.isoformat() if inst.paid_date else ''
                ])
