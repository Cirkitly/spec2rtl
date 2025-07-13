from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.rule import Rule
from rich.theme import Theme
from rich.syntax import Syntax
from rich.markdown import Markdown

# Define a custom theme for consistent styling
custom_theme = Theme({
    "info": "dim cyan",
    "warning": "magenta",
    "danger": "bold red",
    "success": "bold green",
    "prompt": "bold cyan",
    "path": "bright_blue"
})

# Initialize the console with our theme
console = Console(theme=custom_theme)

def print_header():
    """Prints the application header."""
    console.print(Rule("[bold magenta]Spec2Test: AI-Powered Verilog Verification Copilot[/bold magenta]", style="magenta"))
    console.print()

def print_step(message: str):
    """Prints a formatted step message."""
    console.print(f"[bold bright_green]>[/bold bright_green] [info]{message}[/info]")

def print_success(message: str):
    """Prints a success message panel."""
    console.print(Panel(message, title="[success]Success[/success]", border_style="success", expand=False, padding=(1, 2)))

def print_code(code: str, language: str, title: str):
    """Prints syntax-highlighted code in a panel."""
    syntax = Syntax(code, language, theme="monokai", line_numbers=True)
    panel = Panel(syntax, title=f"[info]{title}[/info]", border_style="info")
    console.print(panel)

def print_plan(plan_text: str):
    """Prints a markdown-formatted plan in a panel."""
    markdown = Markdown(plan_text)
    panel = Panel(markdown, title="[info]Proposed Generation Plan[/info]", border_style="info", expand=False, padding=(1,2))
    console.print(panel)

def print_critique(critique_text: str):
    """Prints a markdown-formatted critique in a panel."""
    markdown = Markdown(critique_text)
    panel = Panel(markdown, title="[warning]AI Self-Critique[/warning]", border_style="warning", expand=False, padding=(1,2))
    console.print(panel)

def prompt_for_input(prompt_text: str, default: str) -> str:
    """Prompts the user for text input."""
    return Prompt.ask(f"[prompt]{prompt_text}[/prompt]", default=default, console=console)

def prompt_for_choice(prompt_text: str, choices: list) -> int:
    """Prompts the user to choose from a list of options."""
    return IntPrompt.ask(
        f"[prompt]{prompt_text}[/prompt]",
        choices=[str(i) for i in range(1, len(choices) + 1)],
        show_choices=False,
        console=console
    )

def prompt_for_confirmation(prompt_text: str, default: bool = True) -> bool:
    """Prompts the user for a yes/no confirmation."""
    return Confirm.ask(f"[prompt]{prompt_text}[/prompt]", default=default, console=console)

def status(message: str):
    """Returns a status spinner context manager."""
    return console.status(f"[bold green]{message}[/bold green]", spinner="dots")