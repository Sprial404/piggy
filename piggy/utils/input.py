from datetime import date
from decimal import Decimal, InvalidOperation
from typing import overload


@overload
def get_input(prompt: str, default: str) -> str: ...


@overload
def get_input(prompt: str, default: None = None) -> str | None: ...


def get_input(prompt: str, default: str | None = None) -> str | None:
    """
    Get user input with an optional default value.

    :param prompt: The prompt to display to the user.
    :param default: The default value to return if the user enters nothing. If provided,
                    it will be shown in brackets after the prompt.
    :return: The user's input, or the default value if empty input is provided, or None
             if no default is set and the user enters nothing.
    """
    if default:
        user_input = input(f"{prompt} [{default}]: ").strip()
        return user_input if user_input else default

    user_input = input(f"{prompt}: ").strip()
    return user_input if user_input else None


@overload
def get_decimal_input(prompt: str, default: Decimal) -> Decimal: ...


@overload
def get_decimal_input(prompt: str, default: None = None) -> Decimal | None: ...


def get_decimal_input(prompt: str, default: Decimal | None = None) -> Decimal | None:
    """
    Get decimal input from the user with optional default value.

    :param prompt: The prompt to display to the user.
    :param default: The default decimal value to return if the user enters nothing. If provided,
                    it will be shown in brackets after the prompt.
    :return: The user's decimal input, or the default value if empty input is provided,
             or None otherwise.
    """
    while True:
        try:
            if default is not None:
                value = input(f"{prompt} [{default}]: ").strip()
            else:
                value = input(f"{prompt}: ").strip()

            if not value:
                return default

            return Decimal(value)
        except InvalidOperation:
            print("Invalid number. Please try again.")


@overload
def get_date_input(prompt: str, default: date) -> date: ...


@overload
def get_date_input(prompt: str, default: None = None) -> date | None: ...


def get_date_input(prompt: str, default: date | None = None) -> date | None:
    """
    Get date input in ISO 8601 format from the user with optional default value.
b
    :param prompt: The prompt to display to the user.
    :param default: The default date to return if the user enters nothing. If provided,
                    it will be shown in brackets after the prompt in ISO 8601 format.
    :return: The user's date input, or the default value if empty
             input is provided, or None if no default is set and the user enters nothing.
    """
    while True:
        try:
            if default:
                value = input(f"{prompt} (YYYY-MM-DD) [{default}]: ").strip()
                if not value:
                    return default
            else:
                value = input(f"{prompt} (YYYY-MM-DD): ").strip()
                if not value:
                    return None
            return date.fromisoformat(value)
        except ValueError:
            print("Invalid date format. Please use YYYY-MM-DD.")


@overload
def get_int_input(
        prompt: str,
        default: int,
        min_val: int | None = None,
        max_val: int | None = None
) -> int: ...


@overload
def get_int_input(
        prompt: str,
        default: None = None,
        min_val: int | None = None,
        max_val: int | None = None
) -> int | None: ...


def get_int_input(
        prompt: str,
        default: int | None = None,
        min_val: int | None = None,
        max_val: int | None = None
) -> int | None:
    """
    Get an integer input from the user with validation or an optional default value.

    :param prompt: The prompt to display to the user.
    :param default: The default integer to return if the user enters nothing. If provided,
                    it will be shown in brackets after the prompt.
    :param min_val: The minimum acceptable value (inclusive). If provided, if the user enters an
                    integer value below this, they will be prompted again.
    :param max_val: The maximum acceptable value (inclusive). If provided, if the user enters an
                     integer value above this, they will be prompted again.
    :return: The user's input as an integer, or the default value entered if the user enters nothing,
             or None otherwise.
    """
    if default is not None:
        if min_val is not None and default < min_val:
            raise ValueError(f"Default value {default} is less than the minimum value {min_val}.")

        if max_val is not None and default > max_val:
            raise ValueError(f"Default value {default} is greater than the maximum value {max_val}.")

    while True:
        try:
            if default:
                value = input(f"{prompt} ({default}): ").strip()
            else:
                value = input(f"{prompt}: ").strip()

            if not value:
                return default

            int_val = int(value)

            if min_val is not None and int_val < min_val:
                print(f"Value must be at least {min_val}.")
                continue
            if max_val is not None and int_val > max_val:
                print(f"Value must be at most {max_val}.")
                continue

            return int_val
        except ValueError:
            print("Invalid number. Please enter a valid integer.")
