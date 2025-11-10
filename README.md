# Piggy - Installment Plan Tracker

A Python CLI application for tracking and managing installment payment plans. Keep track of your payment schedules, mark payments as paid/unpaid, and export your data to various formats.

## Features

- **Create Installment Plans** - Set up payment plans with flexible frequencies (monthly, fortnightly, weekly, custom)
- **Track Payments** - Mark installments as paid or unpaid with automatic status updates
- **Overview Dashboard** - View payment statistics, overdue payments, and upcoming due dates
- **Payment Timeline** - See totals due in 7, 15, 30, and 60 day windows
- **Edit Plans** - Modify merchant names, installment amounts, and due dates
- **Data Export** - Export plans to CSV format for analysis
- **Data Persistence** - Save and load plans from JSON files
- **Automatic Overdue Detection** - Plans automatically update overdue status

## Installation

### Prerequisites

- Python 3.13 or higher
- pip (Python package installer)

### Setup

1. Clone the repository:
    ```bash
    git clone https://github.com/Sprial404/piggy.git
    cd piggy
    ```

2. Create and activate a virtual environment:
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    ```

3. Install dependencies:
    ```bash
    pip install -r requirements.txt

    # For development (includes linting/formatting tools):
    pip install -r requirements-dev.txt
    ```

## Usage

### Running the Application

```bash
python -m piggy.interactive
```

### Main Menu Options

- **Overview** - View dashboard with payment statistics and timelines
- **Create New Plan** - Create a new installment payment plan
- **List All Plans** - View all stored payment plans
- **View Plan Details** - See detailed information for a specific plan
- **Mark Payment** - Mark installments as paid or unpaid
- **Edit Plan** - Modify plan details (merchant name, amounts, dates)
- **Data Management** - Save, load, and export plan data
- **Save and Exit** - Save all changes and exit
- **Exit** - Exit (with confirmation if unsaved changes)

### Configuration

#### Custom Data Directory

Set the `PIGGY_DATA_DIR` environment variable to use a custom storage location:

```bash
export PIGGY_DATA_DIR=/path/to/custom/directory
python -m piggy.interactive
```

Default storage location: `<project-root>/data/`

## Development

### Running Tests

```bash
# Run all tests
python -m unittest tests/test_serialization.py

# Run a specific test
python -m unittest tests.test_serialization.TestInstallmentPlanSerialization.test_json_serialization_to_string
```

### Code Quality Tools

```bash
# Format code with Black
black piggy/ tests/

# Lint code with Ruff
ruff check piggy/ tests/

# Auto-fix linting issues
ruff check --fix piggy/ tests/

# Install pre-commit hooks (one-time setup)
pre-commit install

# Run all pre-commit hooks manually
pre-commit run --all-files
```

See `STYLE_GUIDE.md` for detailed code style guidelines.

### Project Structure

```
piggy/
├── analytics.py          # Business logic for payment analysis
├── installment_plan.py   # Core domain models (InstallmentPlan, Installment)
├── interactive.py        # Main CLI application and menu commands
├── menu.py              # Menu navigation framework
├── plan_manager.py      # Plan storage and persistence
└── utils/
    ├── csv_writer.py    # CSV export utilities
    ├── helpers.py       # General helper functions
    └── input.py         # Type-safe input functions
tests/
└── test_serialization.py # Comprehensive test suite
```

### Architecture

- **Domain Models** (`installment_plan.py`) - Pydantic models with validation
- **Business Logic** (`analytics.py`) - Pure functions for calculations and categorization
- **Menu System** (`menu.py`) - Stack-based navigation with command pattern
- **Data Persistence** (`plan_manager.py`) - File-based storage with JSON serialization

### Code Style

- Type hints throughout (Python 3.13+ syntax)
- Dataclasses for stable domain concepts
- TypedDict for flexible analytics results
- Pure functions for business logic
- Separation of concerns (UI, logic, data)

## Examples

### Creating a Plan

```
Merchant name: Best Buy
Total amount: 1200.00
Purchase date: 2024-01-01
Number of installments [4]: 4
Payment frequency:
1. Monthly
2. Fortnightly
3. Weekly
4. Custom
Choose frequency [2]: 1
```

### Viewing Overview

```
=== Overview ===

Summary Statistics
--------------------------------------------------
Total Plans: 3 (1 fully paid, 2 active)
Total Paid: $800.00
Total Remaining: $1,600.00
Total Unpaid Installments: 8

Payment Timeline
--------------------------------------------------
Due in Next 7 Days: $400.00
Due in Next 15 Days: $800.00
Due in Next 30 Days: $1,200.00
Due in Next 60 Days: $1,600.00
```

## Data Format

Plans are stored as JSON files in the data directory:
- Filename format: `<merchant>_<date>.json`
- Includes all installment details, timestamps, and status

## License

[To be added]

## Contributing

[To be added]

## Authors

- Sprial404
