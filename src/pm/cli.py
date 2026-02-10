"""Main CLI application for PM tool"""

import click
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from . import __version__
from .db import get_db_manager, init_database
from .models import Project
from .utils import (
    Config,
    format_datetime,
    get_project_name_from_path,
    is_git_repo,
    validate_priority,
    validate_status,
    PROJECT_STATUSES,
)

console = Console()


@click.group()
@click.version_option(version=__version__)
@click.pass_context
def cli(ctx):
    """PM - Project Management CLI Tool

    A language-agnostic tool for managing project goals, todos, and priorities.
    """
    ctx.ensure_object(dict)
    ctx.obj["config"] = Config()
    ctx.obj["db"] = get_db_manager()


@cli.command()
@click.option("--workspace", "-w", type=click.Path(exists=True), help="Workspace directory to scan")
@click.option("--db-path", type=click.Path(), help="Custom database path")
@click.pass_context
def init(ctx, workspace: Optional[str], db_path: Optional[str]):
    """Initialize PM database and scan workspace for projects"""

    config = ctx.obj["config"]

    # Initialize database
    db_manager = init_database(db_path)

    console.print("\n[bold green]✓[/bold green] Database initialized at:", db_manager.db_path)
    console.print("[bold green]✓[/bold green] Config file created at:", config.config_path)

    # Scan workspace
    if workspace is None:
        workspace = config.get("workspace_path")

    workspace_path = Path(workspace).expanduser().resolve()

    if not workspace_path.exists():
        console.print(f"\n[bold red]Error:[/bold red] Workspace path does not exist: {workspace_path}")
        return

    console.print(f"\n[bold]Scanning workspace:[/bold] {workspace_path}")

    # Find all potential projects (directories with common project markers)
    projects_found = []

    for item in workspace_path.iterdir():
        if not item.is_dir() or item.name.startswith("."):
            continue

        # Check for project markers
        is_project = any([
            (item / "CLAUDE.md").exists(),
            (item / "README.md").exists(),
            (item / "package.json").exists(),
            (item / "requirements.txt").exists(),
            (item / "pyproject.toml").exists(),
            (item / "Cargo.toml").exists(),
            (item / "go.mod").exists(),
            (item / "pom.xml").exists(),
            (item / "project.yml").exists(),
            is_git_repo(item),
        ])

        if is_project:
            projects_found.append(item)

    # Add projects to database
    added_count = 0
    skipped_count = 0

    with db_manager.get_session() as session:
        for project_path in projects_found:
            project_name = get_project_name_from_path(project_path)

            # Check if project already exists
            existing = session.query(Project).filter_by(name=project_name).first()
            if existing:
                skipped_count += 1
                continue

            # Create new project
            has_git = is_git_repo(project_path)

            project = Project(
                name=project_name,
                path=str(project_path),
                has_git=has_git,
                status="active",
                priority=config.get("default_priority", 50),
            )

            session.add(project)
            added_count += 1

        session.commit()

    console.print(f"\n[bold green]✓[/bold green] Found {len(projects_found)} projects")
    console.print(f"  • Added: {added_count}")
    console.print(f"  • Skipped (already exists): {skipped_count}")

    console.print("\n[bold cyan]Next steps:[/bold cyan]")
    console.print("  • Run [bold]pm projects[/bold] to view all projects")
    console.print("  • Run [bold]pm project show <name>[/bold] for project details")
    console.print("  • Run [bold]pm goal add <project> \"Goal title\"[/bold] to add goals")


@cli.group()
def project():
    """Manage projects"""
    pass


@project.command("list")
@click.option("--status", type=click.Choice(PROJECT_STATUSES), help="Filter by status")
@click.option("--sort", type=click.Choice(["priority", "activity", "name"]), default="priority", help="Sort order")
@click.pass_context
def project_list(ctx, status: Optional[str], sort: str):
    """List all projects"""

    db_manager = ctx.obj["db"]

    with db_manager.get_session() as session:
        query = session.query(Project)

        if status:
            query = query.filter(Project.status == status)

        # Apply sorting
        if sort == "priority":
            query = query.order_by(Project.priority.desc())
        elif sort == "activity":
            query = query.order_by(Project.last_activity_at.desc().nullslast())
        else:  # name
            query = query.order_by(Project.name)

        projects = query.all()

        # Extract data while session is active
        project_data = [
            {
                "name": proj.name,
                "status": proj.status,
                "priority": proj.priority,
                "has_git": proj.has_git,
                "last_activity_at": proj.last_activity_at,
                "path": proj.path,
            }
            for proj in projects
        ]

    if not project_data:
        console.print("\n[yellow]No projects found. Run 'pm init' to scan your workspace.[/yellow]")
        return

    # Create table
    table = Table(
        title=f"Projects ({len(project_data)})",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
    )

    table.add_column("Name", style="bold")
    table.add_column("Status")
    table.add_column("Priority", justify="center")
    table.add_column("Git", justify="center")
    table.add_column("Last Activity")
    table.add_column("Path", style="dim")

    for proj in project_data:
        status_color = {
            "active": "green",
            "paused": "yellow",
            "archived": "dim",
            "completed": "blue",
        }.get(proj["status"], "white")

        git_icon = "✓" if proj["has_git"] else "✗"
        activity = format_datetime(proj["last_activity_at"]) if proj["last_activity_at"] else "Never"

        table.add_row(
            proj["name"],
            f"[{status_color}]{proj['status']}[/{status_color}]",
            str(proj["priority"]),
            git_icon,
            activity,
            proj["path"],
        )

    console.print()
    console.print(table)


@project.command("add")
@click.argument("path", type=click.Path(exists=True))
@click.option("--name", help="Project name (default: directory name)")
@click.option("--priority", type=int, default=50, help="Priority (0-100)")
@click.option("--status", type=click.Choice(PROJECT_STATUSES), default="active", help="Project status")
@click.pass_context
def project_add(ctx, path: str, name: Optional[str], priority: int, status: str):
    """Add a new project"""

    db_manager = ctx.obj["db"]
    path = Path(path).expanduser().resolve()

    if name is None:
        name = get_project_name_from_path(path)

    priority = validate_priority(priority)

    with db_manager.get_session() as session:
        # Check if project already exists
        existing = session.query(Project).filter_by(name=name).first()
        if existing:
            console.print(f"\n[bold red]Error:[/bold red] Project '{name}' already exists")
            return

        # Create project
        has_git = is_git_repo(path)

        project = Project(
            name=name,
            path=str(path),
            has_git=has_git,
            status=status,
            priority=priority,
        )

        session.add(project)
        session.commit()

        console.print(f"\n[bold green]✓[/bold green] Added project: [bold]{name}[/bold]")
        console.print(f"  Path: {path}")
        console.print(f"  Status: {status}")
        console.print(f"  Priority: {priority}")
        console.print(f"  Git repository: {'Yes' if has_git else 'No'}")


@project.command("update")
@click.argument("name")
@click.option("--status", type=click.Choice(PROJECT_STATUSES), help="Update status")
@click.option("--priority", type=int, help="Update priority (0-100)")
@click.pass_context
def project_update(ctx, name: str, status: Optional[str], priority: Optional[int]):
    """Update project properties"""

    db_manager = ctx.obj["db"]

    with db_manager.get_session() as session:
        project = session.query(Project).filter_by(name=name).first()

        if not project:
            console.print(f"\n[bold red]Error:[/bold red] Project '{name}' not found")
            return

        updated_fields = []

        if status:
            project.status = status
            updated_fields.append(f"status → {status}")

        if priority is not None:
            project.priority = validate_priority(priority)
            updated_fields.append(f"priority → {project.priority}")

        if not updated_fields:
            console.print("\n[yellow]No updates specified[/yellow]")
            return

        session.commit()

        console.print(f"\n[bold green]✓[/bold green] Updated project: [bold]{name}[/bold]")
        for field in updated_fields:
            console.print(f"  • {field}")


@project.command("show")
@click.argument("name")
@click.pass_context
def project_show(ctx, name: str):
    """Show detailed project information"""

    db_manager = ctx.obj["db"]

    with db_manager.get_session() as session:
        project = session.query(Project).filter_by(name=name).first()

        if not project:
            console.print(f"\n[bold red]Error:[/bold red] Project '{name}' not found")
            return

        # Count related items
        goals_count = len(project.goals)
        todos_open = sum(1 for t in project.todos if t.status in ["open", "in_progress"])
        todos_total = len(project.todos)
        commits_count = len(project.commits)

        # Create info panel
        info = f"""[bold]Name:[/bold] {project.name}
[bold]Path:[/bold] {project.path}
[bold]Status:[/bold] {project.status}
[bold]Priority:[/bold] {project.priority}
[bold]Git Repository:[/bold] {'Yes' if project.has_git else 'No'}
[bold]Last Activity:[/bold] {format_datetime(project.last_activity_at)}

[bold cyan]Statistics:[/bold cyan]
  • Goals: {goals_count}
  • Todos: {todos_open} open / {todos_total} total
  • Commits: {commits_count}

[bold]Created:[/bold] {format_datetime(project.created_at)}
[bold]Updated:[/bold] {format_datetime(project.updated_at)}"""

        if project.description:
            info = f"{info}\n\n[bold]Description:[/bold]\n{project.description}"

        panel = Panel(
            info,
            title=f"[bold]Project: {project.name}[/bold]",
            border_style="cyan",
            box=box.ROUNDED,
        )

        console.print()
        console.print(panel)


# Alias 'projects' to 'project list'
@cli.command("projects")
@click.option("--status", type=click.Choice(PROJECT_STATUSES), help="Filter by status")
@click.option("--sort", type=click.Choice(["priority", "activity", "name"]), default="priority", help="Sort order")
@click.pass_context
def projects_alias(ctx, status: Optional[str], sort: str):
    """List all projects (alias for 'project list')"""
    ctx.invoke(project_list, status=status, sort=sort)


def main():
    """Entry point for the CLI"""
    cli(obj={})


if __name__ == "__main__":
    main()
