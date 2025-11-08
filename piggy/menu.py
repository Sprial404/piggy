from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Callable, Optional

from piggy.utils.error_handler import get_error_category, format_error_for_category


class NavigationAction(Enum):
    NONE = auto()
    PUSH = auto()
    POP = auto()
    POP_TO_ROOT = auto()
    REPLACE = auto()
    EXIT = auto()


class NavigationContext:
    def __init__(self):
        self._menu_stack: list['Menu'] = []
        self._shared_data: dict[str, Any] = {}
        self._last_result: Optional['CommandResult'] = None

    def push_menu(self, menu: 'Menu'):
        self._menu_stack.append(menu)

    def pop_menu(self) -> Optional['Menu']:
        if len(self._menu_stack) > 1:
            self._menu_stack.pop()
            return self.get_current_menu()
        return None

    def pop_menu_to_root(self):
        if self._menu_stack:
            self._menu_stack = [self._menu_stack[0]]

    def replace_menu(self, menu: 'Menu'):
        if self._menu_stack:
            self._menu_stack[-1] = menu
        else:
            self._menu_stack.append(menu)

    def get_current_menu(self) -> Optional['Menu']:
        return self._menu_stack[-1] if self._menu_stack else None

    def get_breadcrumb(self) -> str:
        if not self._menu_stack:
            return ""
        return " > ".join(menu.title for menu in self._menu_stack)

    def set_data(self, key: str, value: Any):
        self._shared_data[key] = value

    def get_data(self, key: str, default: Any = None) -> Any:
        return self._shared_data.get(key, default)

    def clear_data(self, *keys: str):
        if keys:
            for key in keys:
                self._shared_data.pop(key, None)
        else:
            self._shared_data.clear()

    def set_last_result(self, result: 'CommandResult'):
        """Store the last command result for access by parent menus."""
        self._last_result = result

    def get_last_return_value(self, default: Any | None = None) -> Any | None:
        """Get the return value from the last executed command."""
        if self._last_result:
            return self._last_result.return_value
        return default

    def clear_last_result(self):
        """Clear the stored last command result."""
        self._last_result = None


@dataclass
class CommandResult:
    action: NavigationAction = NavigationAction.NONE
    target_menu: Optional['Menu'] = None
    message: str | None = None
    return_value: Any | None = None


class BaseCommand(ABC):
    """Base class for a command option in a menu interface."""

    @abstractmethod
    def execute(self, context: NavigationContext) -> CommandResult:
        pass

    @abstractmethod
    def description(self) -> str:
        pass


class Command(BaseCommand):
    def __init__(self, description: str, execute_fn: Callable[[NavigationContext], CommandResult]):
        self._description = description
        self._execute_fn = execute_fn

    def execute(self, context: NavigationContext) -> CommandResult:
        return self._execute_fn(context)

    def description(self) -> str:
        return self._description


class BackCommand(BaseCommand):
    def execute(self, context: NavigationContext) -> CommandResult:
        return CommandResult(NavigationAction.POP)

    def description(self) -> str:
        return "Back"


class ExitCommand(BaseCommand):
    def execute(self, context: NavigationContext) -> CommandResult:
        return CommandResult(NavigationAction.EXIT)

    def description(self) -> str:
        return "Exit"


class SubMenuCommand(BaseCommand):
    def __init__(self, menu: 'Menu'):
        self._menu = menu

    def execute(self, context: NavigationContext) -> CommandResult:
        return CommandResult(
            action=NavigationAction.PUSH,
            target_menu=self._menu,
        )

    def description(self) -> str:
        return self._menu.title


class Menu:
    def __init__(self, title: str):
        self._title = title
        self._commands: dict[str, BaseCommand] = {}

    @property
    def title(self) -> str:
        return self._title

    def add_command(self, key: str, command: BaseCommand):
        if key in self._commands:
            raise KeyError(f'Command "{key}" already exists')
        self._commands[key] = command

    def add_submenu(self, key: str, submenu: 'Menu'):
        self.add_command(key, SubMenuCommand(submenu))

    def add_back_command(self, key: str = "b"):
        self.add_command(key, BackCommand())

    def display(self):
        print(f"{self._title}")

        for key, command in sorted(self._commands.items()):
            print(f"{key}. {command.description()}")

    def handle_input(self, choice: str, context: NavigationContext) -> CommandResult:
        if choice in self._commands:
            command = self._commands[choice]

            try:
                return command.execute(context)
            except KeyboardInterrupt:
                # User cancelled - re-raise to let outer handler deal with it
                raise
            except Exception as e:
                # Categorize and format error appropriately
                category = get_error_category(e)
                error_message = format_error_for_category(e, category)

                # Print traceback to console for unexpected errors
                if category == 'unexpected':
                    print(error_message)
                    # Return simpler message for CommandResult
                    return CommandResult(
                        action=NavigationAction.NONE,
                        message=f"An unexpected error occurred: {type(e).__name__}"
                    )
                else:
                    return CommandResult(
                        action=NavigationAction.NONE,
                        message=error_message
                    )
        else:
            return CommandResult(
                action=NavigationAction.NONE,
                message=f"Command '{choice}' not found."
            )


class MenuInterface:
    def __init__(
        self,
        start_menu: Menu,
        context: NavigationContext | None = None
    ):
        self._context = context if context is not None else NavigationContext()
        self._context.push_menu(start_menu)

    def run(self) -> Any:
        """Run the menu interface loop"""
        final_return_value = None

        while True:
            current_menu = self._context.get_current_menu()
            if not current_menu:
                break

            current_menu.display()
            choice = input("\n> ").strip()
            result = current_menu.handle_input(choice, self._context)

            if not result:
                continue

            self._context.set_last_result(result)

            if result.return_value is not None:
                final_return_value = result.return_value

            if result.message:
                print(f"\n{result.message}")

            match result.action:
                case NavigationAction.EXIT:
                    break
                case NavigationAction.PUSH:
                    if result.target_menu:
                        self._context.push_menu(result.target_menu)
                case NavigationAction.POP:
                    if not self._context.pop_menu():
                        break
                case NavigationAction.POP_TO_ROOT:
                    self._context.pop_menu_to_root()
                case NavigationAction.REPLACE:
                    if result.target_menu:
                        self._context.replace_menu(result.target_menu)
                case NavigationAction.NONE:
                    pass

        return final_return_value
