"""Typer CLI for running scenarios, benchmarking models, and exporting LaTeX tables."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer
import yaml
from rich.console import Console
from rich.table import Table

from agent_poison.core.runner import DEFAULT_API_KEY, DEFAULT_BASE_URL, AgentRunner
from agent_poison.evaluation.metrics import aggregate_results, render_latex_table, render_markdown_table
from agent_poison.models.schemas import DefenseMode, RunResult, Scenario

app = typer.Typer(help="agent-poison: benchmark LLM resilience to indirect prompt injection.")
console = Console()

DEFAULT_CONFIG_PATH = Path("configs/default.yaml")
DEFAULT_SCENARIOS_DIR = Path("datasets/scenarios")
DEFAULT_RESULTS_DIR = Path("results")

ALL_DEFENSES = [DefenseMode.NONE, DefenseMode.XML_DELIMITERS, DefenseMode.SYSTEM_REINFORCEMENT, DefenseMode.DUAL_PROMPT]


def _load_config(path: Path = DEFAULT_CONFIG_PATH) -> dict:
    if path.exists():
        return yaml.safe_load(path.read_text()) or {}
    return {}


def _load_scenario(scenario_id: str, scenarios_dir: Path) -> Scenario:
    path = scenarios_dir / f"{scenario_id}.json"
    if not path.exists():
        raise typer.BadParameter(f"Scenario '{scenario_id}' not found at {path}")
    return Scenario.model_validate(json.loads(path.read_text()))


def _load_all_scenarios(scenarios_dir: Path) -> list[Scenario]:
    return [Scenario.model_validate(json.loads(p.read_text())) for p in sorted(scenarios_dir.glob("*.json"))]


def _parse_defense_list(defense: str) -> list[DefenseMode]:
    if defense.lower() == "all":
        return ALL_DEFENSES
    return [DefenseMode(d.strip()) for d in defense.split(",") if d.strip()]


def _save_result(result: RunResult, results_dir: Path) -> Path:
    results_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    safe_model = result.model.replace("/", "_").replace(":", "_")
    fname = f"{safe_model}__{result.scenario_id}__{result.defense_mode.value}__{'poisoned' if result.poisoned else 'benign'}__{timestamp}.json"
    path = results_dir / fname
    path.write_text(result.model_dump_json(indent=2))
    return path


def _load_all_results(results_dir: Path) -> list[RunResult]:
    if not results_dir.exists():
        raise typer.BadParameter(f"Results directory {results_dir} does not exist")
    return [RunResult.model_validate(json.loads(p.read_text())) for p in sorted(results_dir.glob("*.json"))]


def _print_run_summary(result: RunResult) -> None:
    table = Table(title=f"{result.model} | {result.scenario_id} | {result.defense_mode.value} | {'poisoned' if result.poisoned else 'benign'}")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Hijack triggered", "[red]YES[/red]" if result.hijack_triggered else "[green]no[/green]")
    table.add_row("Ground truth completed", "[green]yes[/green]" if result.ground_truth_completed else "[red]NO[/red]")
    table.add_row("Refused", "yes" if result.refused else "no")
    table.add_row("Tool calls", ", ".join(f"{tc.tool_name}(turn {tc.turn})" for tc in result.tool_calls) or "(none)")
    if result.error:
        table.add_row("Error", f"[red]{result.error}[/red]")
    console.print(table)


@app.command()
def run(
    model: str = typer.Option(..., help="Model name as served by the OpenAI-compatible endpoint, e.g. llama3.1:8b"),
    scenario: str = typer.Option(..., help="Scenario id (filename without .json), or 'all'"),
    defense: str = typer.Option("none", help="Defense mode: none | xml_delimiters | system_reinforcement | dual_prompt | all | comma-separated list"),
    base_url: Optional[str] = typer.Option(None, help="OpenAI-compatible base URL"),
    max_turns: Optional[int] = typer.Option(None, help="Max agent turns per run"),
    temperature: Optional[float] = typer.Option(None, help="Sampling temperature. Trials at temperature 0.0 are deterministic and will all produce identical results."),
    trials: int = typer.Option(1, help="Number of repeated runs per (scenario, defense, poisoned/benign) cell"),
    scenarios_dir: Path = DEFAULT_SCENARIOS_DIR,
    results_dir: Path = DEFAULT_RESULTS_DIR,
    poisoned_only: bool = typer.Option(False, help="Only run the poisoned condition"),
    benign_only: bool = typer.Option(False, help="Only run the benign (clean) condition"),
    save: bool = typer.Option(True, help="Save run results as JSON to results_dir"),
) -> None:
    """Run one model against one (or all) scenarios under a given defense."""
    config = _load_config()
    resolved_base_url = base_url or config.get("base_url", DEFAULT_BASE_URL)
    resolved_max_turns = max_turns or config.get("max_turns", 4)
    resolved_temperature = temperature if temperature is not None else config.get("temperature", 0.0)

    if trials > 1 and resolved_temperature == 0.0:
        console.print(
            "[yellow]warning:[/yellow] --trials > 1 with temperature 0.0 is deterministic — "
            "every trial in a cell will produce the identical result. Pass --temperature to get variance."
        )

    scenarios = _load_all_scenarios(scenarios_dir) if scenario == "all" else [_load_scenario(scenario, scenarios_dir)]
    defense_modes = _parse_defense_list(defense)
    poisoned_conditions = [True, False]
    if poisoned_only:
        poisoned_conditions = [True]
    if benign_only:
        poisoned_conditions = [False]

    runner = AgentRunner(
        model=model,
        base_url=resolved_base_url,
        api_key=config.get("api_key", DEFAULT_API_KEY),
        max_turns=resolved_max_turns,
        temperature=resolved_temperature,
    )

    for scn in scenarios:
        for dmode in defense_modes:
            for poisoned in poisoned_conditions:
                for trial in range(1, trials + 1):
                    result = runner.run(scn, poisoned=poisoned, defense_mode=dmode)
                    if trials > 1:
                        console.print(f"[dim]trial {trial}/{trials}[/dim]")
                    _print_run_summary(result)
                    if save:
                        saved_path = _save_result(result, results_dir)
                        console.print(f"[dim]saved -> {saved_path}[/dim]")


@app.command()
def benchmark(
    model_list: str = typer.Option(..., "--model-list", help="Comma-separated model names, e.g. 'llama3.1:8b,qwen2.5:7b'"),
    all_scenarios: bool = typer.Option(False, "--all-scenarios", help="Run every scenario in scenarios_dir"),
    scenario_list: Optional[str] = typer.Option(None, "--scenario-list", help="Comma-separated scenario ids (ignored if --all-scenarios)"),
    defense: str = typer.Option("all", help="Defense mode(s) to test: comma-separated or 'all'"),
    base_url: Optional[str] = typer.Option(None, help="OpenAI-compatible base URL"),
    max_turns: Optional[int] = typer.Option(None, help="Max agent turns per run"),
    scenarios_dir: Path = DEFAULT_SCENARIOS_DIR,
    results_dir: Path = DEFAULT_RESULTS_DIR,
) -> None:
    """Run every (model x scenario x defense x poisoned/benign) combination and print aggregate metrics."""
    config = _load_config()
    resolved_base_url = base_url or config.get("base_url", DEFAULT_BASE_URL)
    resolved_max_turns = max_turns or config.get("max_turns", 4)

    if not all_scenarios and not scenario_list:
        raise typer.BadParameter("Pass --all-scenarios or --scenario-list")

    if all_scenarios:
        scenarios = _load_all_scenarios(scenarios_dir)
    else:
        scenarios = [_load_scenario(s.strip(), scenarios_dir) for s in scenario_list.split(",") if s.strip()]

    models = [m.strip() for m in model_list.split(",") if m.strip()]
    defense_modes = _parse_defense_list(defense)

    all_results: list[RunResult] = []
    for model in models:
        runner = AgentRunner(
            model=model,
            base_url=resolved_base_url,
            api_key=config.get("api_key", DEFAULT_API_KEY),
            max_turns=resolved_max_turns,
            temperature=config.get("temperature", 0.0),
        )
        for scn in scenarios:
            for dmode in defense_modes:
                for poisoned in (True, False):
                    console.print(f"[cyan]running[/cyan] {model} | {scn.id} | {dmode.value} | {'poisoned' if poisoned else 'benign'}")
                    result = runner.run(scn, poisoned=poisoned, defense_mode=dmode)
                    all_results.append(result)
                    _save_result(result, results_dir)

    aggregates = aggregate_results(all_results)
    console.print("\n[bold]Benchmark summary[/bold]\n")
    console.print(render_markdown_table(aggregates))


@app.command(name="export-latex")
def export_latex(
    results_dir: Path = typer.Option(DEFAULT_RESULTS_DIR, help="Directory of saved run-result JSON files"),
    output: Optional[Path] = typer.Option(None, help="File to write the LaTeX table to (prints to stdout if omitted)"),
    caption: str = typer.Option("Attack success rate and task accuracy by model and defense.", help="LaTeX table caption"),
    label: str = typer.Option("tab:results", help="LaTeX table label"),
) -> None:
    """Aggregate all saved results into a LaTeX table (and a Markdown preview)."""
    results = _load_all_results(results_dir)
    if not results:
        console.print(f"[yellow]No result files found in {results_dir}[/yellow]")
        raise typer.Exit(code=1)

    aggregates = aggregate_results(results)

    console.print("[bold]Markdown preview[/bold]\n")
    console.print(render_markdown_table(aggregates))

    latex = render_latex_table(aggregates, caption=caption, label=label)
    if output:
        output.write_text(latex)
        console.print(f"\n[green]LaTeX table written to {output}[/green]")
    else:
        console.print("\n[bold]LaTeX[/bold]\n")
        console.print(latex)


if __name__ == "__main__":
    app()
