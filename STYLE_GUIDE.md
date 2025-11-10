# Style Guide

This document outlines the code style conventions used in the Piggy project.

## Automated Tools

We use automated tools to enforce consistent code style:

- **Black** - Code formatter (line length: 120 characters)
- **Ruff** - Fast Python linter
- **Pre-commit hooks** - Automatic checks before commits

### Setup

Install development dependencies:
```bash
pip install -r requirements-dev.txt
```

Install pre-commit hooks:
```bash
pre-commit install
```

### Running Tools Manually

Format code with Black:
```bash
black piggy/ tests/
```

Lint code with Ruff:
```bash
ruff check piggy/ tests/
```

Auto-fix issues:
```bash
ruff check --fix piggy/ tests/
```

Run all pre-commit hooks:
```bash
pre-commit run --all-files
```

## Python Version

- **Target:** Python 3.13+
- Use modern Python 3.13 type hint syntax

## Code Style Principles

### Type Annotations

**Always use type hints:**
```python
def calculate_total(amounts: list[Decimal]) -> Decimal:
    return sum(amounts, start=Decimal(0))
```

**Modern syntax (Python 3.13+):**
- Use `str | None` instead of `Optional[str]`
- Use `list[Type]` instead of `List[Type]`
- Use `dict[K, V]` instead of `Dict[K, V]`

### Comments

**Only add comments for complex logic:**
```python
# Good - explains non-obvious behavior
# PyCharm incorrectly flags Pydantic's @field_validator + @classmethod pattern
# noinspection PyNestedDecorators

# Bad - restates what code does
# Set the total amount to the sum of installments
total_amount = sum(installments)
```

**Prefer self-documenting code:**
- Use descriptive variable/function names
- Extract complex expressions into named variables
- Break down long functions

### Docstrings

Follow the existing docstring style with `:param` and `:return` tags:

```python
def calculate_statistics(plans: dict[str, InstallmentPlan]) -> PaymentStatistics:
    """
    Calculate summary statistics for payment overview.

    :param plans: Dictionary of plan_id -> InstallmentPlan
    :return: PaymentStatistics with calculated values
    """
    ...
```

### Function Organization

**Prefer composition over inheritance:**
- Use shallow inheritance hierarchies
- Favor composition and delegation

**Extract functions when the name adds clarity:**
```python
# Good - function name explains the logic
def is_payment_overdue(payment: Installment, today: date) -> bool:
    return payment.due_date < today and not payment.is_paid

# Don't extract if it reduces readability
# Bad - forces reader to jump to implementation
def check_status():  # vague name, simple logic
    return status == PaymentStatus.PAID
```

### Data Structures

**Use appropriate types:**

- **Dataclass** - For stable domain concepts with fixed fields
  ```python
  @dataclass
  class PaymentInfo:
      plan_id: str
      merchant: str
      installment: Installment
  ```

- **TypedDict** - For flexible results that may change frequently
  ```python
  class PaymentStatistics(TypedDict):
      total_plans: int
      total_paid: Decimal
      time_period_totals: dict[int, Decimal]
  ```

- **Pydantic BaseModel** - For validated domain models
  ```python
  class InstallmentPlan(BaseModel):
      merchant_name: str
      total_amount: Decimal = Field(gt=0)
  ```

### Functional Programming

**Strive for pure functions:**
```python
# Good - pure function
def categorize_payments(payments: list[Payment], cutoff: date) -> CategorizedPayments:
    overdue = [p for p in payments if p.due_date < cutoff]
    return {"overdue": overdue, ...}

# Avoid - side effects mixed with logic
def categorize_payments(payments: list[Payment]):
    global overdue_payments
    overdue_payments = [p for p in payments if ...]
    print(f"Found {len(overdue_payments)} overdue")  # I/O in logic
```

**Push side effects to boundaries:**
- Keep business logic pure (in `analytics.py`)
- Handle I/O at application boundaries (in `interactive.py`)

### Code Organization

**Module structure:**
- `piggy/` - Application code
  - `analytics.py` - Pure business logic
  - `installment_plan.py` - Domain models
  - `interactive.py` - UI and command handlers
  - `menu.py` - Menu framework
  - `plan_manager.py` - Data persistence
  - `utils/` - Utility functions

**Import order (handled by Ruff):**
1. Standard library imports
2. Third-party imports
3. Local application imports

### Naming Conventions

- **Functions/variables:** `snake_case`
- **Classes:** `PascalCase`
- **Constants:** `UPPER_SNAKE_CASE`
- **Private/internal:** Prefix with `_` (e.g., `_helper_function`)

### Line Length

- **Maximum:** 120 characters (enforced by Black)
- Break long lines naturally at function calls, list comprehensions

### Testing

**Test organization:**
- One test file per module (e.g., `test_installment_plan.py`)
- Use descriptive test names: `test_marking_installment_paid_updates_status`
- Group related tests in classes

**Test style:**
```python
def test_remaining_balance_calculation(self):
    """Test remaining_balance property calculates correctly."""
    plan = create_test_plan()  # helper function
    plan.mark_installment_paid(1, date.today())

    expected = Decimal("800.00")
    self.assertEqual(plan.remaining_balance, expected)
```

## Language

**Use clear, concise language:**
- Avoid extraneous adjectives
- No overly emotive language
- Be direct and professional

**Variable names:**
```python
# Good
installment_count = len(installments)
overdue_payments = [p for p in payments if p.is_overdue]

# Avoid
num = len(installments)  # too vague
the_really_important_overdue_payment_list = [...]  # verbose
```

## Pre-commit Hooks

The pre-commit configuration runs automatically before each commit:

1. **Black** - Formats code
2. **Ruff** - Lints and auto-fixes issues
3. **Trailing whitespace** - Removes trailing spaces
4. **End of file fixer** - Ensures newline at end
5. **YAML/JSON/TOML checks** - Validates config files
6. **Large files check** - Prevents committing large files

To skip hooks (not recommended):
```bash
git commit --no-verify
```

## Additional Guidelines

### Error Handling

Use specific exceptions:
```python
# Good
try:
    plan = plan_manager.get_plan(plan_id)
except KeyError:
    return CommandResult(message=f"Plan {plan_id} not found")

# Avoid
except Exception:  # too broad
    pass
```

### Magic Numbers

Extract to named constants:
```python
# Good
DAYS_IN_WEEK = 7
next_week = today + timedelta(days=DAYS_IN_WEEK)

# Avoid
next_week = today + timedelta(days=7)  # what does 7 mean?
```

### Decimal for Currency

Always use `Decimal` for financial calculations:
```python
# Good
from decimal import Decimal
total = Decimal("100.00") + Decimal("50.00")

# Never
total = 100.00 + 50.00  # float rounding errors
```

## Questions or Suggestions?

If you have questions about the style guide or suggestions for improvements, please open an issue or discussion.
