"""Command-line interface and interactive REPL for PyCalcAgent."""

import argparse
import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from pycalcagent.agent import PyCalcAgent
from pycalcagent.memory import CalculationMemory
from pycalcagent.tracer import default_tracer

console = Console()


def display_history(memory: CalculationMemory) -> None:
    """Render recent calculation history in a formatted table."""
    records = memory.get_recent_history(10)
    if not records:
        console.print("[yellow]No calculation history found.[/yellow]")
        return

    table = Table(title="Recent Calculations", show_lines=True)
    table.add_column("Query", style="cyan", no_wrap=True)
    table.add_column("Executed Python Code", style="green")
    table.add_column("Result", style="bold magenta")

    for rec in records:
        table.add_row(rec.query, rec.python_code.strip(), rec.result)
    console.print(table)


def display_variables(memory: CalculationMemory) -> None:
    """Render saved session variables in a formatted table."""
    vars_dict = memory.list_variables()
    if not vars_dict:
        console.print("[yellow]No saved variables in session memory.[/yellow]")
        return

    table = Table(title="Saved Session Variables", show_lines=True)
    table.add_column("Variable Name", style="bold cyan")
    table.add_column("Value", style="bold green")

    for k, v in vars_dict.items():
        table.add_row(k, str(v))
    console.print(table)


def interactive_repl(agent: PyCalcAgent) -> None:
    """Run an interactive REPL session with PyCalcAgent."""
    console.print(
        Panel(
            "[bold green]Welcome to PyCalcAgent![/bold green]\n"
            "Type a calculation (e.g. [cyan]2 * 4[/cyan] or [cyan]save 2 * 4 as x[/cyan]).\n"
            "Commands: [yellow]/history[/yellow] | [yellow]/vars[/yellow] | [yellow]/clear[/yellow] | [yellow]/exit[/yellow]",
            title="AI in 5 Days Assessment Agent",
        )
    )

    while True:
        try:
            query = console.input("[bold blue]PyCalc > [/bold blue]").strip()
            if not query:
                continue
            if query.lower() in ("/exit", "exit", "quit"):
                console.print("[green]Goodbye![/green]")
                break
            elif query.lower() in ("/history", "history"):
                display_history(agent.memory)
                continue
            elif query.lower() in ("/vars", "vars"):
                display_variables(agent.memory)
                continue
            elif query.lower() in ("/clear", "clear"):
                agent.memory.clear()
                console.print("[green]Session memory cleared.[/green]")
                continue

            response = agent.run(query)
            if response.success:
                console.print(f"[bold green]Result:[/bold green] {response.result_value}")
                console.print(f"[dim]Executed Code:\n{response.executed_code.strip()}[/dim]")
            else:
                console.print(f"[bold red]Error:[/bold red] {response.answer}")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[green]Goodbye![/green]")
            break


def main() -> None:
    """CLI entrypoint for PyCalcAgent."""
    parser = argparse.ArgumentParser(description="PyCalcAgent: AI in 5 Days Assessment Agent")
    parser.add_argument("query", nargs="?", help="Optional single calculation query to execute.")
    parser.add_argument("--history", action="store_true", help="Display calculation history and exit.")
    parser.add_argument("--vars", action="store_true", help="Display saved session variables and exit.")
    parser.add_argument("--clear", action="store_true", help="Clear session memory.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose trace event logging.")

    args = parser.parse_args()
    if args.verbose:
        default_tracer.verbose = True

    memory = CalculationMemory()
    agent = PyCalcAgent(memory=memory)

    if args.clear:
        memory.clear()
        console.print("[green]Session memory cleared.[/green]")
        if not args.query and not args.history and not args.vars:
            return

    if args.history:
        display_history(memory)
        return

    if args.vars:
        display_variables(memory)
        return

    if args.query:
        response = agent.run(args.query)
        if response.success:
            print(response.result_value)
            sys.exit(0)
        else:
            print(response.answer, file=sys.stderr)
            sys.exit(1)
    else:
        interactive_repl(agent)


if __name__ == "__main__":
    main()
