"""Main CLI application for PM tool"""

import click
from pathlib import Path
from typing import Optional
from datetime import datetime, date, timedelta
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from . import __version__
from .db import get_db_manager, init_database
from .models import Project, Goal, Todo, Commit
from .utils import (
    Config,
    format_datetime,
    format_date,
    parse_date,
    get_project_name_from_path,
    is_git_repo,
    validate_priority,
    get_relative_time,
    truncate_string,
    PROJECT_STATUSES,
    GOAL_STATUSES,
    GOAL_CATEGORIES,
    TODO_STATUSES,
    EFFORT_LEVELS,
)
from .priority import PriorityCalculator
from .git_integration import GitScanner
from .metrics import MetricsCalculator
from .claude_md import ClaudeMdParser, ExportImport
import questionary
import json

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
        console.print(
            f"\n[bold red]Error:[/bold red] Workspace path does not exist: {workspace_path}"
        )
        return

    console.print(f"\n[bold]Scanning workspace:[/bold] {workspace_path}")

    # Find all potential projects (directories with common project markers)
    projects_found = []

    for item in workspace_path.iterdir():
        if not item.is_dir() or item.name.startswith("."):
            continue

        # Check for project markers
        is_project = any(
            [
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
            ]
        )

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
    console.print('  • Run [bold]pm goal add <project> "Goal title"[/bold] to add goals')


@cli.group()
def project():
    """Manage projects"""
    pass


@project.command("list")
@click.option("--status", type=click.Choice(PROJECT_STATUSES), help="Filter by status")
@click.option(
    "--sort",
    type=click.Choice(["priority", "activity", "name"]),
    default="priority",
    help="Sort order",
)
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
        activity = (
            format_datetime(proj["last_activity_at"]) if proj["last_activity_at"] else "Never"
        )

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
@click.option(
    "--status", type=click.Choice(PROJECT_STATUSES), default="active", help="Project status"
)
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


@project.command("delete")
@click.argument("name")
@click.option("--force", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def project_delete(ctx, name: str, force: bool):
    """Remove a project from tracking (does not delete files)"""

    db_manager = ctx.obj["db"]

    with db_manager.get_session() as session:
        project = session.query(Project).filter_by(name=name).first()

        if not project:
            console.print(f"\n[bold red]Error:[/bold red] Project '{name}' not found")
            return

        # Count related data
        goals_count = len(project.goals)
        todos_count = len(project.todos)
        commits_count = len(project.commits)

        # Show what will be deleted
        console.print(
            f"\n[bold yellow]⚠ Warning:[/bold yellow] About to delete project: [bold]{name}[/bold]"
        )
        console.print(f"  Path: {project.path}")
        console.print("  This will remove:")
        console.print(f"    • {goals_count} goals")
        console.print(f"    • {todos_count} todos")
        console.print(f"    • {commits_count} commits")
        console.print(
            "\n[dim]Note: This only removes tracking data. Project files remain intact.[/dim]"
        )

        # Confirm deletion
        if not force:
            import questionary

            confirm = questionary.confirm(
                f"Are you sure you want to delete '{name}'?", default=False
            ).ask()

            if not confirm:
                console.print("\n[yellow]Deletion cancelled.[/yellow]")
                return

        # Delete the project (CASCADE will handle related data)
        session.delete(project)
        session.commit()

        console.print(f"\n[bold green]✓[/bold green] Deleted project: [bold]{name}[/bold]")
        console.print(
            f"  Removed {goals_count} goals, {todos_count} todos, {commits_count} commits"
        )


@project.command("clean")
@click.option("--dry-run", is_flag=True, help="Show what would be deleted without deleting")
@click.pass_context
def project_clean(ctx, dry_run: bool):
    """Remove projects whose folders no longer exist"""
    from pathlib import Path

    db_manager = ctx.obj["db"]

    with db_manager.get_session() as session:
        projects = session.query(Project).all()

        # Find projects with missing folders
        missing_projects = []
        for project in projects:
            project_path = Path(project.path)
            if not project_path.exists():
                missing_projects.append(
                    {
                        "name": project.name,
                        "path": project.path,
                        "goals": len(project.goals),
                        "todos": len(project.todos),
                        "commits": len(project.commits),
                        "obj": project,
                    }
                )

        if not missing_projects:
            console.print("\n[bold green]✓[/bold green] All projects have valid paths")
            return

        # Show what will be deleted
        console.print(
            f"\n[bold yellow]Found {len(missing_projects)} projects with missing folders:[/bold yellow]\n"
        )

        for proj in missing_projects:
            console.print(f"  [bold]{proj['name']}[/bold]")
            console.print(f"    Path: {proj['path']} [red](not found)[/red]")
            console.print(
                f"    Data: {proj['goals']} goals, {proj['todos']} todos, {proj['commits']} commits"
            )

        if dry_run:
            console.print(
                "\n[dim]Dry run - nothing deleted. Run without --dry-run to delete.[/dim]"
            )
            return

        # Confirm deletion
        import questionary

        confirm = questionary.confirm(
            f"\nDelete these {len(missing_projects)} projects from tracking?", default=False
        ).ask()

        if not confirm:
            console.print("\n[yellow]Cleanup cancelled.[/yellow]")
            return

        # Delete missing projects
        total_goals = sum(p["goals"] for p in missing_projects)
        total_todos = sum(p["todos"] for p in missing_projects)
        total_commits = sum(p["commits"] for p in missing_projects)

        for proj in missing_projects:
            session.delete(proj["obj"])

        session.commit()

        console.print(f"\n[bold green]✓[/bold green] Cleaned up {len(missing_projects)} projects")
        console.print(
            f"  Removed {total_goals} goals, {total_todos} todos, {total_commits} commits"
        )


# Alias 'projects' to 'project list'
@cli.command("projects")
@click.option("--status", type=click.Choice(PROJECT_STATUSES), help="Filter by status")
@click.option(
    "--sort",
    type=click.Choice(["priority", "activity", "name"]),
    default="priority",
    help="Sort order",
)
@click.pass_context
def projects_alias(ctx, status: Optional[str], sort: str):
    """List all projects (alias for 'project list')"""
    ctx.invoke(project_list, status=status, sort=sort)


# ============================================================================
# Goal Management Commands
# ============================================================================


@cli.group()
def goal():
    """Manage goals"""
    pass


@goal.command("add")
@click.argument("project_name")
@click.argument("title")
@click.option("--description", "-d", help="Goal description")
@click.option(
    "--category", "-c", type=click.Choice(GOAL_CATEGORIES), default="feature", help="Goal category"
)
@click.option("--priority", "-p", type=int, default=50, help="Priority (0-100)")
@click.option("--target", "-t", help="Target date (YYYY-MM-DD)")
@click.pass_context
def goal_add(
    ctx,
    project_name: str,
    title: str,
    description: Optional[str],
    category: str,
    priority: int,
    target: Optional[str],
):
    """Add a new goal to a project"""

    db_manager = ctx.obj["db"]
    priority = validate_priority(priority)

    with db_manager.get_session() as session:
        # Find project
        project = session.query(Project).filter_by(name=project_name).first()
        if not project:
            console.print(f"\n[bold red]Error:[/bold red] Project '{project_name}' not found")
            return

        # Parse target date
        target_date = None
        if target:
            try:
                target_date = parse_date(target)
            except Exception as e:
                console.print(f"\n[bold red]Error:[/bold red] Invalid date format: {e}")
                return

        # Create goal
        goal = Goal(
            project_id=project.id,
            title=title,
            description=description,
            category=category,
            priority=priority,
            target_date=target_date,
            status="active",
        )

        session.add(goal)
        session.commit()

        console.print(f"\n[bold green]✓[/bold green] Added goal to [bold]{project_name}[/bold]")
        console.print(f"  Title: {title}")
        console.print(f"  Category: {category}")
        console.print(f"  Priority: {priority}")
        if target_date:
            console.print(f"  Target: {format_date(target_date)}")


@goal.command("list")
@click.argument("project_name", required=False)
@click.option("--status", type=click.Choice(GOAL_STATUSES), help="Filter by status")
@click.option("--priority-min", type=int, help="Minimum priority")
@click.pass_context
def goal_list(ctx, project_name: Optional[str], status: Optional[str], priority_min: Optional[int]):
    """List goals (all projects or specific project)"""

    db_manager = ctx.obj["db"]

    with db_manager.get_session() as session:
        query = session.query(Goal)

        # Filter by project if specified
        if project_name:
            project = session.query(Project).filter_by(name=project_name).first()
            if not project:
                console.print(f"\n[bold red]Error:[/bold red] Project '{project_name}' not found")
                return
            query = query.filter(Goal.project_id == project.id)

        # Filter by status
        if status:
            query = query.filter(Goal.status == status)

        # Filter by minimum priority
        if priority_min is not None:
            query = query.filter(Goal.priority >= priority_min)

        # Order by priority descending
        query = query.order_by(Goal.priority.desc())

        goals = query.all()

        # Extract data while session is active
        goal_data = [
            {
                "id": g.id,
                "project_name": g.project.name,
                "title": g.title,
                "category": g.category,
                "priority": g.priority,
                "status": g.status,
                "target_date": g.target_date,
                "todo_count": len(g.todos),
            }
            for g in goals
        ]

    if not goal_data:
        console.print("\n[yellow]No goals found.[/yellow]")
        return

    # Create table
    table = Table(
        title=f"Goals ({len(goal_data)})" + (f" - {project_name}" if project_name else ""),
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
    )

    table.add_column("ID", justify="right", style="dim")
    if not project_name:
        table.add_column("Project", style="bold")
    table.add_column("Title")
    table.add_column("Category")
    table.add_column("Priority", justify="center")
    table.add_column("Status")
    table.add_column("Target")
    table.add_column("Todos", justify="center")

    for g in goal_data:
        status_color = {
            "active": "green",
            "completed": "blue",
            "cancelled": "dim",
        }.get(g["status"], "white")

        category_color = {
            "feature": "cyan",
            "bugfix": "red",
            "refactor": "yellow",
            "docs": "blue",
            "ops": "magenta",
        }.get(g["category"], "white")

        row_data = [
            str(g["id"]),
        ]

        if not project_name:
            row_data.append(g["project_name"])

        row_data.extend(
            [
                g["title"],
                f"[{category_color}]{g['category']}[/{category_color}]",
                str(g["priority"]),
                f"[{status_color}]{g['status']}[/{status_color}]",
                format_date(g["target_date"]),
                str(g["todo_count"]),
            ]
        )

        table.add_row(*row_data)

    console.print()
    console.print(table)


@goal.command("show")
@click.argument("goal_id", type=int)
@click.pass_context
def goal_show(ctx, goal_id: int):
    """Show detailed goal information"""

    db_manager = ctx.obj["db"]

    with db_manager.get_session() as session:
        goal = session.query(Goal).filter_by(id=goal_id).first()

        if not goal:
            console.print(f"\n[bold red]Error:[/bold red] Goal #{goal_id} not found")
            return

        # Extract data
        data = {
            "id": goal.id,
            "title": goal.title,
            "description": goal.description,
            "project_name": goal.project.name,
            "category": goal.category,
            "priority": goal.priority,
            "status": goal.status,
            "target_date": goal.target_date,
            "todos_count": len(goal.todos),
            "todos_completed": sum(1 for t in goal.todos if t.status == "completed"),
            "created_at": goal.created_at,
            "updated_at": goal.updated_at,
        }

    # Create info panel
    info = f"""[bold]ID:[/bold] #{data['id']}
[bold]Title:[/bold] {data['title']}
[bold]Project:[/bold] {data['project_name']}
[bold]Category:[/bold] {data['category']}
[bold]Priority:[/bold] {data['priority']}
[bold]Status:[/bold] {data['status']}
[bold]Target Date:[/bold] {format_date(data['target_date'])}

[bold cyan]Progress:[/bold cyan]
  • Todos: {data['todos_completed']} completed / {data['todos_count']} total

[bold]Created:[/bold] {format_datetime(data['created_at'])}
[bold]Updated:[/bold] {format_datetime(data['updated_at'])}"""

    if data["description"]:
        info = f"{info}\n\n[bold]Description:[/bold]\n{data['description']}"

    panel = Panel(
        info,
        title=f"[bold]Goal: {data['title']}[/bold]",
        border_style="cyan",
        box=box.ROUNDED,
    )

    console.print()
    console.print(panel)


@goal.command("update")
@click.argument("goal_id", type=int)
@click.option("--status", type=click.Choice(GOAL_STATUSES), help="Update status")
@click.option("--priority", type=int, help="Update priority (0-100)")
@click.option("--target", help="Update target date (YYYY-MM-DD)")
@click.pass_context
def goal_update(
    ctx, goal_id: int, status: Optional[str], priority: Optional[int], target: Optional[str]
):
    """Update goal properties"""

    db_manager = ctx.obj["db"]

    with db_manager.get_session() as session:
        goal = session.query(Goal).filter_by(id=goal_id).first()

        if not goal:
            console.print(f"\n[bold red]Error:[/bold red] Goal #{goal_id} not found")
            return

        updated_fields = []

        if status:
            goal.status = status
            updated_fields.append(f"status → {status}")

        if priority is not None:
            goal.priority = validate_priority(priority)
            updated_fields.append(f"priority → {goal.priority}")

        if target:
            try:
                goal.target_date = parse_date(target)
                updated_fields.append(f"target → {format_date(goal.target_date)}")
            except Exception as e:
                console.print(f"\n[bold red]Error:[/bold red] Invalid date format: {e}")
                return

        if not updated_fields:
            console.print("\n[yellow]No updates specified[/yellow]")
            return

        session.commit()

        console.print(
            f"\n[bold green]✓[/bold green] Updated goal #{goal_id}: [bold]{goal.title}[/bold]"
        )
        for field in updated_fields:
            console.print(f"  • {field}")


# Alias 'goals' to 'goal list'
@cli.command("goals")
@click.argument("project_name", required=False)
@click.option("--status", type=click.Choice(GOAL_STATUSES), help="Filter by status")
@click.option("--priority-min", type=int, help="Minimum priority")
@click.pass_context
def goals_alias(
    ctx, project_name: Optional[str], status: Optional[str], priority_min: Optional[int]
):
    """List goals (alias for 'goal list')"""
    ctx.invoke(goal_list, project_name=project_name, status=status, priority_min=priority_min)


# ============================================================================
# Todo Management Commands
# ============================================================================


@cli.group()
def todo():
    """Manage todos"""
    pass


@todo.command("add")
@click.argument("project_name")
@click.argument("title")
@click.option("--description", "-d", help="Todo description")
@click.option("--goal", "-g", type=int, help="Link to goal ID")
@click.option("--effort", "-e", type=click.Choice(EFFORT_LEVELS), help="Effort estimate (S/M/L/XL)")
@click.option("--due", help="Due date (YYYY-MM-DD)")
@click.option("--tags", help="Comma-separated tags")
@click.pass_context
def todo_add(
    ctx,
    project_name: str,
    title: str,
    description: Optional[str],
    goal: Optional[int],
    effort: Optional[str],
    due: Optional[str],
    tags: Optional[str],
):
    """Add a new todo to a project"""

    db_manager = ctx.obj["db"]
    config = ctx.obj["config"]

    with db_manager.get_session() as session:
        # Find project
        project = session.query(Project).filter_by(name=project_name).first()
        if not project:
            console.print(f"\n[bold red]Error:[/bold red] Project '{project_name}' not found")
            return

        # Verify goal if specified
        goal_obj = None
        if goal:
            goal_obj = session.query(Goal).filter_by(id=goal, project_id=project.id).first()
            if not goal_obj:
                console.print(
                    f"\n[bold red]Error:[/bold red] Goal #{goal} not found in project '{project_name}'"
                )
                return

        # Parse due date
        due_date = None
        if due:
            try:
                due_date = parse_date(due)
            except Exception as e:
                console.print(f"\n[bold red]Error:[/bold red] Invalid date format: {e}")
                return

        # Parse tags
        tags_dict = None
        if tags:
            tags_dict = {"tags": [tag.strip() for tag in tags.split(",")]}

        # Create todo
        new_todo = Todo(
            project_id=project.id,
            goal_id=goal if goal else None,
            title=title,
            description=description,
            effort_estimate=effort,
            due_date=due_date,
            tags=tags_dict,
            status="open",
        )

        session.add(new_todo)
        session.flush()  # Get the ID

        # Calculate initial priority
        calculator = PriorityCalculator(config)
        new_todo.priority_score = calculator.calculate_priority(new_todo, session)

        session.commit()

        console.print(f"\n[bold green]✓[/bold green] Added todo to [bold]{project_name}[/bold]")
        console.print(f"  Title: {title}")
        console.print(f"  ID: #{new_todo.id}")
        console.print(f"  Priority Score: {new_todo.priority_score:.1f}")
        if goal_obj:
            console.print(f"  Goal: {goal_obj.title}")
        if effort:
            console.print(f"  Effort: {effort}")
        if due_date:
            console.print(f"  Due: {format_date(due_date)}")


@todo.command("list")
@click.argument("project_name", required=False)
@click.option("--status", type=click.Choice(TODO_STATUSES), help="Filter by status")
@click.option("--goal", type=int, help="Filter by goal ID")
@click.option("--next", "show_next", is_flag=True, help="Show top 5 by priority")
@click.option("--blocked", is_flag=True, help="Show only blocked todos")
@click.option("--tag", help="Filter by tag (e.g., 'urgent', 'bug')")
@click.option("--today", is_flag=True, help="Show only today's planned todos")
@click.pass_context
def todo_list(
    ctx,
    project_name: Optional[str],
    status: Optional[str],
    goal: Optional[int],
    show_next: bool,
    blocked: bool,
    tag: Optional[str],
    today: bool,
):
    """List todos (all projects or specific project)"""

    db_manager = ctx.obj["db"]

    with db_manager.get_session() as session:
        query = session.query(Todo)

        # Filter by project if specified
        if project_name:
            project = session.query(Project).filter_by(name=project_name).first()
            if not project:
                console.print(f"\n[bold red]Error:[/bold red] Project '{project_name}' not found")
                return
            query = query.filter(Todo.project_id == project.id)

        # Filter by status
        if status:
            query = query.filter(Todo.status == status)
        elif not blocked:
            # Default to open and in_progress
            query = query.filter(Todo.status.in_(["open", "in_progress"]))

        # Filter by goal
        if goal:
            query = query.filter(Todo.goal_id == goal)

        # Filter by tag
        if tag:
            query = query.filter(Todo.tags.contains(tag))

        # Filter by today
        if today:
            query = query.filter(Todo.tags.contains("today"))

        # Filter by blocked
        if blocked:
            query = query.filter(Todo.status == "blocked")

        # Order by priority descending
        query = query.order_by(Todo.priority_score.desc())

        # Limit for --next
        if show_next:
            query = query.limit(5)

        todos = query.all()

        # Extract data while session is active
        todo_data = [
            {
                "id": t.id,
                "project_name": t.project.name,
                "title": t.title,
                "status": t.status,
                "priority_score": t.priority_score,
                "effort": t.effort_estimate,
                "due_date": t.due_date,
                "goal_title": t.goal.title if t.goal else None,
            }
            for t in todos
        ]

    if not todo_data:
        console.print("\n[yellow]No todos found.[/yellow]")
        return

    # Create table
    title_suffix = ""
    if project_name:
        title_suffix = f" - {project_name}"
    elif show_next:
        title_suffix = " - Top Priority"
    elif blocked:
        title_suffix = " - Blocked"
    elif today:
        title_suffix = " - Today's Plan"
    elif tag:
        title_suffix = f" - #{tag}"

    table = Table(
        title=f"Todos ({len(todo_data)}){title_suffix}",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
    )

    table.add_column("ID", justify="right", style="dim")
    if not project_name:
        table.add_column("Project", style="bold")
    table.add_column("Title")
    table.add_column("Status")
    table.add_column("Priority", justify="center")
    table.add_column("Effort", justify="center")
    table.add_column("Due")
    table.add_column("Goal", style="dim")

    for t in todo_data:
        status_color = {
            "open": "yellow",
            "in_progress": "cyan",
            "blocked": "red",
            "completed": "green",
            "cancelled": "dim",
        }.get(t["status"], "white")

        # Priority color coding
        priority = t["priority_score"]
        if priority >= 80:
            priority_color = "red"
        elif priority >= 60:
            priority_color = "yellow"
        else:
            priority_color = "white"

        row_data = [
            str(t["id"]),
        ]

        if not project_name:
            row_data.append(t["project_name"])

        row_data.extend(
            [
                t["title"],
                f"[{status_color}]{t['status']}[/{status_color}]",
                f"[{priority_color}]{t['priority_score']:.1f}[/{priority_color}]",
                t["effort"] or "-",
                format_date(t["due_date"]),
                t["goal_title"] or "-",
            ]
        )

        table.add_row(*row_data)

    console.print()
    console.print(table)


@todo.command("show")
@click.argument("todo_id", type=int)
@click.pass_context
def todo_show(ctx, todo_id: int):
    """Show detailed todo information"""

    db_manager = ctx.obj["db"]

    with db_manager.get_session() as session:
        todo_obj = session.query(Todo).filter_by(id=todo_id).first()

        if not todo_obj:
            console.print(f"\n[bold red]Error:[/bold red] Todo #{todo_id} not found")
            return

        # Extract data
        commit_shas = todo_obj.tags.get("commit_shas", []) if todo_obj.tags else []
        commits = []
        if commit_shas:
            commits = (
                session.query(Commit)
                .filter(Commit.project_id == todo_obj.project_id, Commit.sha.in_(commit_shas))
                .order_by(Commit.committed_at.desc())
                .all()
            )

        data = {
            "id": todo_obj.id,
            "title": todo_obj.title,
            "description": todo_obj.description,
            "project_name": todo_obj.project.name,
            "goal_title": todo_obj.goal.title if todo_obj.goal else None,
            "status": todo_obj.status,
            "priority_score": todo_obj.priority_score,
            "effort": todo_obj.effort_estimate,
            "due_date": todo_obj.due_date,
            "tags": todo_obj.tags.get("tags", []) if todo_obj.tags else [],
            "blocked_by": todo_obj.blocked_by.get("todo_ids", []) if todo_obj.blocked_by else [],
            "created_at": todo_obj.created_at,
            "updated_at": todo_obj.updated_at,
            "started_at": todo_obj.started_at,
            "completed_at": todo_obj.completed_at,
            "commits": [(c.sha[:7], c.message.split("\n")[0], c.committed_at) for c in commits],
        }

    # Create info panel
    info = f"""[bold]ID:[/bold] #{data['id']}
[bold]Title:[/bold] {data['title']}
[bold]Project:[/bold] {data['project_name']}
[bold]Status:[/bold] {data['status']}
[bold]Priority Score:[/bold] {data['priority_score']:.1f}
"""

    if data["goal_title"]:
        info += f"[bold]Goal:[/bold] {data['goal_title']}\n"

    if data["effort"]:
        info += f"[bold]Effort:[/bold] {data['effort']}\n"

    if data["due_date"]:
        info += f"[bold]Due:[/bold] {format_date(data['due_date'])}\n"

    if data["tags"]:
        info += f"[bold]Tags:[/bold] {', '.join(data['tags'])}\n"

    if data["blocked_by"]:
        info += f"[bold]Blocked By:[/bold] Todos #{', #'.join(map(str, data['blocked_by']))}\n"

    info += f"\n[bold]Created:[/bold] {format_datetime(data['created_at'])}\n"
    info += f"[bold]Updated:[/bold] {format_datetime(data['updated_at'])}\n"

    if data["started_at"]:
        info += f"[bold]Started:[/bold] {format_datetime(data['started_at'])}\n"

    if data["completed_at"]:
        info += f"[bold]Completed:[/bold] {format_datetime(data['completed_at'])}\n"

    if data["commits"]:
        info += "\n[bold cyan]Linked Commits:[/bold cyan]\n"
        for sha, message, commit_date in data["commits"]:
            info += (
                f"  • {sha}: {truncate_string(message, 50)} ({get_relative_time(commit_date)})\n"
            )

    if data["description"]:
        info = f"{info}\n[bold]Description:[/bold]\n{data['description']}"

    panel = Panel(
        info,
        title=f"[bold]Todo: {data['title']}[/bold]",
        border_style="cyan",
        box=box.ROUNDED,
    )

    console.print()
    console.print(panel)


@todo.command("start")
@click.argument("todo_id", type=int)
@click.pass_context
def todo_start(ctx, todo_id: int):
    """Mark todo as in progress"""

    db_manager = ctx.obj["db"]

    with db_manager.get_session() as session:
        todo_obj = session.query(Todo).filter_by(id=todo_id).first()

        if not todo_obj:
            console.print(f"\n[bold red]Error:[/bold red] Todo #{todo_id} not found")
            return

        if todo_obj.status == "completed":
            console.print(
                f"\n[bold yellow]Warning:[/bold yellow] Todo #{todo_id} is already completed"
            )
            return

        todo_obj.status = "in_progress"
        todo_obj.started_at = datetime.utcnow()

        # Recalculate priority (in_progress gets 1.2x boost)
        config = ctx.obj["config"]
        calculator = PriorityCalculator(config)
        todo_obj.priority_score = calculator.calculate_priority(todo_obj, session)

        session.commit()

        console.print(
            f"\n[bold green]✓[/bold green] Started todo #{todo_id}: [bold]{todo_obj.title}[/bold]"
        )
        console.print("  Status: in_progress")
        console.print(f"  Priority Score: {todo_obj.priority_score:.1f}")


@todo.command("complete")
@click.argument("todo_id", type=int)
@click.pass_context
def todo_complete(ctx, todo_id: int):
    """Mark todo as completed"""

    db_manager = ctx.obj["db"]

    with db_manager.get_session() as session:
        todo_obj = session.query(Todo).filter_by(id=todo_id).first()

        if not todo_obj:
            console.print(f"\n[bold red]Error:[/bold red] Todo #{todo_id} not found")
            return

        if todo_obj.status == "completed":
            console.print(
                f"\n[bold yellow]Warning:[/bold yellow] Todo #{todo_id} is already completed"
            )
            return

        todo_obj.status = "completed"
        todo_obj.completed_at = datetime.utcnow()

        session.commit()

        console.print(
            f"\n[bold green]✓[/bold green] Completed todo #{todo_id}: [bold]{todo_obj.title}[/bold]"
        )
        console.print("  🎉 Great work!")


@todo.command("block")
@click.argument("todo_id", type=int)
@click.option("--by", "blocked_by_id", type=int, required=True, help="Todo ID that blocks this one")
@click.pass_context
def todo_block(ctx, todo_id: int, blocked_by_id: int):
    """Mark todo as blocked by another todo"""

    db_manager = ctx.obj["db"]

    with db_manager.get_session() as session:
        todo_obj = session.query(Todo).filter_by(id=todo_id).first()
        blocker = session.query(Todo).filter_by(id=blocked_by_id).first()

        if not todo_obj:
            console.print(f"\n[bold red]Error:[/bold red] Todo #{todo_id} not found")
            return

        if not blocker:
            console.print(f"\n[bold red]Error:[/bold red] Blocker todo #{blocked_by_id} not found")
            return

        # Add to blocked_by list
        blocked_by = todo_obj.blocked_by or {"todo_ids": []}
        if blocked_by_id not in blocked_by.get("todo_ids", []):
            blocked_by.setdefault("todo_ids", []).append(blocked_by_id)
            todo_obj.blocked_by = blocked_by
            todo_obj.status = "blocked"

            # Recalculate priority (blocked gets 0.5x reduction)
            config = ctx.obj["config"]
            calculator = PriorityCalculator(config)
            todo_obj.priority_score = calculator.calculate_priority(todo_obj, session)

            session.commit()

            console.print(
                f"\n[bold yellow]⚠[/bold yellow] Todo #{todo_id} blocked by #{blocked_by_id}"
            )
            console.print("  Status: blocked")
            console.print(f"  Priority Score: {todo_obj.priority_score:.1f}")
        else:
            console.print(
                f"\n[bold yellow]Warning:[/bold yellow] Todo #{todo_id} already blocked by #{blocked_by_id}"
            )


# Alias 'todos' to 'todo list'
@cli.command("todos")
@click.argument("project_name", required=False)
@click.option("--status", type=click.Choice(TODO_STATUSES), help="Filter by status")
@click.option("--goal", type=int, help="Filter by goal ID")
@click.option("--next", "show_next", is_flag=True, help="Show top 5 by priority")
@click.option("--blocked", is_flag=True, help="Show only blocked todos")
@click.option("--tag", help="Filter by tag (e.g., 'urgent', 'bug')")
@click.option("--today", is_flag=True, help="Show only today's planned todos")
@click.pass_context
def todos_alias(
    ctx,
    project_name: Optional[str],
    status: Optional[str],
    goal: Optional[int],
    show_next: bool,
    blocked: bool,
    tag: Optional[str],
    today: bool,
):
    """List todos (alias for 'todo list')"""
    ctx.invoke(
        todo_list,
        project_name=project_name,
        status=status,
        goal=goal,
        show_next=show_next,
        blocked=blocked,
        tag=tag,
        today=today,
    )


# ============================================================================
# Priority Management Commands
# ============================================================================


@cli.command("prioritize")
@click.argument("project_name", required=False)
@click.pass_context
def prioritize(ctx, project_name: Optional[str]):
    """Recalculate priority scores for all todos"""

    db_manager = ctx.obj["db"]
    config = ctx.obj["config"]

    with db_manager.get_session() as session:
        project_id = None

        if project_name:
            project = session.query(Project).filter_by(name=project_name).first()
            if not project:
                console.print(f"\n[bold red]Error:[/bold red] Project '{project_name}' not found")
                return
            project_id = project.id

        calculator = PriorityCalculator(config)

        with console.status("[bold cyan]Recalculating priorities...[/bold cyan]"):
            count = calculator.recalculate_all(session, project_id)

        scope = f"in {project_name}" if project_name else "across all projects"
        console.print(
            f"\n[bold green]✓[/bold green] Recalculated priorities for {count} todos {scope}"
        )


# ============================================================================
# Git Integration Commands
# ============================================================================


@cli.command("sync")
@click.argument("project_name", required=False)
@click.option("--all", "sync_all", is_flag=True, help="Sync all projects with git repos")
@click.option("--limit", type=int, help="Limit commits per project")
@click.pass_context
def sync(ctx, project_name: Optional[str], sync_all: bool, limit: Optional[int]):
    """Sync git commits to database"""

    db_manager = ctx.obj["db"]
    scanner = GitScanner()

    with db_manager.get_session() as session:
        if sync_all or not project_name:
            # Sync all projects
            with console.status("[bold cyan]Syncing git commits...[/bold cyan]"):
                results = scanner.sync_all_projects(session, limit_per_project=limit)

            if not results:
                console.print("\n[yellow]No new commits found[/yellow]")
                return

            # Display results
            table = Table(
                title="Git Sync Results",
                box=box.ROUNDED,
                show_header=True,
                header_style="bold cyan",
            )

            table.add_column("Project", style="bold")
            table.add_column("Commits Added", justify="center")
            table.add_column("Todos Updated", justify="center")

            total_commits = 0
            total_todos = 0

            for project_name, (commits_added, todos_updated) in results.items():
                table.add_row(
                    project_name,
                    str(commits_added),
                    str(todos_updated) if todos_updated > 0 else "-",
                )
                total_commits += commits_added
                total_todos += todos_updated

            console.print()
            console.print(table)
            console.print(
                f"\n[bold green]✓[/bold green] Synced {total_commits} commits, updated {total_todos} todos"
            )

        else:
            # Sync specific project
            project = session.query(Project).filter_by(name=project_name).first()
            if not project:
                console.print(f"\n[bold red]Error:[/bold red] Project '{project_name}' not found")
                return

            if not project.has_git:
                console.print(
                    f"\n[bold yellow]Warning:[/bold yellow] Project '{project_name}' is not a git repository"
                )
                return

            with console.status(f"[bold cyan]Syncing {project_name}...[/bold cyan]"):
                commits_added, todos_updated = scanner.scan_project(project, session, limit)

            console.print(f"\n[bold green]✓[/bold green] Synced [bold]{project_name}[/bold]")
            console.print(f"  • Commits added: {commits_added}")
            if todos_updated > 0:
                console.print(f"  • Todos updated: {todos_updated}")


@cli.command("activity")
@click.argument("project_name")
@click.option("--days", type=int, default=30, help="Number of days to show (default: 30)")
@click.option("--since", help="Show activity since date (YYYY-MM-DD)")
@click.pass_context
def activity(ctx, project_name: str, days: int, since: Optional[str]):
    """Show git activity timeline for a project"""

    db_manager = ctx.obj["db"]
    scanner = GitScanner()

    with db_manager.get_session() as session:
        project = session.query(Project).filter_by(name=project_name).first()
        if not project:
            console.print(f"\n[bold red]Error:[/bold red] Project '{project_name}' not found")
            return

        if not project.has_git:
            console.print(
                f"\n[bold yellow]Warning:[/bold yellow] Project '{project_name}' is not a git repository"
            )
            return

        # Parse since date
        since_date = None
        if since:
            try:
                since_date = parse_date(since)

                days = (datetime.now().date() - since_date).days
            except Exception as e:
                console.print(f"\n[bold red]Error:[/bold red] Invalid date format: {e}")
                return

        # Get activity timeline
        timeline = scanner.get_activity_timeline(project, session, days)

        if not timeline:
            console.print(f"\n[yellow]No activity found in the last {days} days[/yellow]")
            return

        # Get overall stats
        stats = scanner.get_commit_stats(project, session, since=since_date)

        # Display timeline
        table = Table(
            title=f"Activity Timeline - {project_name} (Last {days} days)",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan",
        )

        table.add_column("Date")
        table.add_column("Commits", justify="center")
        table.add_column("Insertions", justify="right", style="green")
        table.add_column("Deletions", justify="right", style="red")
        table.add_column("Net Change", justify="right")

        for day in timeline:
            net_change = day["insertions"] - day["deletions"]
            net_color = "green" if net_change > 0 else "red" if net_change < 0 else "white"

            table.add_row(
                str(day["date"]),
                str(day["commits"]),
                f"+{day['insertions']}",
                f"-{day['deletions']}",
                f"[{net_color}]{net_change:+d}[/{net_color}]",
            )

        console.print()
        console.print(table)

        # Display summary stats
        console.print("\n[bold cyan]Summary:[/bold cyan]")
        console.print(f"  • Total commits: {stats['total_commits']}")
        console.print(f"  • Total insertions: [green]+{stats['total_insertions']}[/green]")
        console.print(f"  • Total deletions: [red]-{stats['total_deletions']}[/red]")
        console.print(f"  • Files changed: {stats['total_files_changed']}")
        console.print(f"  • Unique authors: {stats['unique_authors']}")
        console.print(f"  • Avg insertions/commit: {stats['avg_insertions']:.1f}")


@cli.command("commits")
@click.argument("project_name")
@click.option("--limit", type=int, default=10, help="Number of commits to show (default: 10)")
@click.option("--author", help="Filter by author")
@click.option("--since", help="Show commits since date (YYYY-MM-DD)")
@click.pass_context
def commits(ctx, project_name: str, limit: int, author: Optional[str], since: Optional[str]):
    """Show recent commits for a project"""

    db_manager = ctx.obj["db"]
    scanner = GitScanner()

    with db_manager.get_session() as session:
        project = session.query(Project).filter_by(name=project_name).first()
        if not project:
            console.print(f"\n[bold red]Error:[/bold red] Project '{project_name}' not found")
            return

        if not project.has_git:
            console.print(
                f"\n[bold yellow]Warning:[/bold yellow] Project '{project_name}' is not a git repository"
            )
            return

        # Parse since date
        since_date = None
        if since:
            try:
                since_date = datetime.combine(parse_date(since), datetime.min.time())
            except Exception as e:
                console.print(f"\n[bold red]Error:[/bold red] Invalid date format: {e}")
                return

        # Get recent commits
        recent_commits = scanner.get_recent_commits(project, session, limit, author, since_date)

        if not recent_commits:
            console.print("\n[yellow]No commits found[/yellow]")
            return

        # Display commits
        table = Table(
            title=f"Recent Commits - {project_name}",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan",
        )

        table.add_column("SHA", style="dim", width=7)
        table.add_column("Date")
        table.add_column("Author", style="bold")
        table.add_column("Message")
        table.add_column("Changes", justify="right")
        table.add_column("Todos", justify="center")

        for commit in recent_commits:
            # Extract todo IDs from tags
            todo_ids = commit.tags.get("todo_ids", []) if commit.tags else []
            todos_str = ", ".join(f"#{id}" for id in todo_ids) if todo_ids else "-"

            # Truncate commit message (first line only)
            message_first_line = commit.message.split("\n")[0]
            message = truncate_string(message_first_line, 50)

            # Author (name only, without email)
            author_name = commit.author.split("<")[0].strip()

            # Changes summary
            changes = f"+{commit.insertions}/-{commit.deletions}"

            # Relative time
            time_ago = get_relative_time(commit.committed_at)

            table.add_row(
                commit.sha[:7],
                time_ago,
                author_name,
                message,
                changes,
                todos_str,
            )

        console.print()
        console.print(table)


@cli.command("sync-and-prioritize")
@click.argument("project_name", required=False)
@click.pass_context
def sync_and_prioritize(ctx, project_name: Optional[str]):
    """Sync git commits and recalculate priorities (useful for daily workflow)"""

    # Run sync
    console.print("[bold cyan]Step 1:[/bold cyan] Syncing git commits...")
    ctx.invoke(sync, project_name=project_name, sync_all=not project_name, limit=None)

    console.print("\n[bold cyan]Step 2:[/bold cyan] Recalculating priorities...")
    ctx.invoke(prioritize, project_name=project_name)

    console.print("\n[bold green]✓[/bold green] Sync and prioritization complete!")


# ============================================================================
# Analytics & Metrics Commands
# ============================================================================


@cli.command("metrics")
@click.argument("project_name")
@click.option("--detailed", is_flag=True, help="Show detailed metrics with trends")
@click.pass_context
def metrics(ctx, project_name: str, detailed: bool):
    """Show project metrics and health dashboard"""

    db_manager = ctx.obj["db"]
    calculator = MetricsCalculator()

    with db_manager.get_session() as session:
        project = session.query(Project).filter_by(name=project_name).first()
        if not project:
            console.print(f"\n[bold red]Error:[/bold red] Project '{project_name}' not found")
            return

        # Calculate metrics
        health_score, health_status = calculator.calculate_health_score(project, session)
        velocity = calculator.calculate_velocity(project, session, days=7)
        completion_rate = calculator.calculate_completion_rate(project, session)

        todo_breakdown = calculator.get_todo_breakdown(project, session)
        goal_breakdown = calculator.get_goal_breakdown(project, session)

        overdue = calculator.get_overdue_todos(project, session)
        upcoming = calculator.get_upcoming_deadlines(project, session, days=7)

        # Health score panel with color
        health_color = "green" if health_score >= 60 else "yellow" if health_score >= 40 else "red"
        health_panel = Panel(
            f"[bold {health_color}]{health_score}/100[/bold {health_color}] - {health_status}",
            title="[bold]Health Score[/bold]",
            border_style=health_color,
            box=box.ROUNDED,
        )

        console.print()
        console.print(f"[bold cyan]Metrics Dashboard - {project_name}[/bold cyan]")
        console.print()
        console.print(health_panel)

        # Key metrics table
        metrics_table = Table(
            box=box.ROUNDED,
            show_header=False,
            padding=(0, 2),
        )

        metrics_table.add_column("Metric", style="bold")
        metrics_table.add_column("Value")

        metrics_table.add_row("Velocity (7d)", f"{velocity:.2f} todos/day")
        metrics_table.add_row("Completion Rate", f"{completion_rate:.1f}%")
        metrics_table.add_row(
            "Last Activity",
            format_datetime(project.last_activity_at) if project.last_activity_at else "Never",
        )

        console.print()
        console.print(metrics_table)

        # Todo breakdown
        console.print("\n[bold cyan]Todo Status:[/bold cyan]")
        todo_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
        todo_table.add_column("Status", style="bold")
        todo_table.add_column("Count", justify="right")

        status_colors = {
            "open": "yellow",
            "in_progress": "cyan",
            "blocked": "red",
            "completed": "green",
        }

        for status in ["open", "in_progress", "blocked", "completed"]:
            count = todo_breakdown[status]
            color = status_colors.get(status, "white")
            todo_table.add_row(f"[{color}]{status.replace('_', ' ').title()}[/{color}]", str(count))

        console.print(todo_table)

        # Goal breakdown
        if goal_breakdown["active"] > 0 or goal_breakdown["completed"] > 0:
            console.print("\n[bold cyan]Goals:[/bold cyan]")
            goal_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
            goal_table.add_column("Status", style="bold")
            goal_table.add_column("Count", justify="right")

            goal_table.add_row("[green]Active[/green]", str(goal_breakdown["active"]))
            goal_table.add_row("[blue]Completed[/blue]", str(goal_breakdown["completed"]))

            console.print(goal_table)

        # Warnings
        if overdue:
            console.print(f"\n[bold red]⚠ Overdue:[/bold red] {len(overdue)} todos")
            for todo in overdue[:3]:
                days_overdue = (date.today() - todo.due_date).days
                console.print(f"  • #{todo.id}: {todo.title} ({days_overdue}d overdue)")

        if upcoming:
            console.print(
                f"\n[bold yellow]📅 Upcoming:[/bold yellow] {len(upcoming)} todos in next 7 days"
            )
            for todo in upcoming[:3]:
                days_until = (todo.due_date - date.today()).days
                console.print(f"  • #{todo.id}: {todo.title} (in {days_until}d)")

        # Detailed view
        if detailed:
            console.print("\n[bold cyan]Velocity Trend (4 weeks):[/bold cyan]")
            velocity_trend = calculator.get_velocity_trend(project, session, weeks=4)

            trend_table = Table(box=box.ROUNDED, show_header=True, header_style="bold")
            trend_table.add_column("Week")
            trend_table.add_column("Completed", justify="center")
            trend_table.add_column("Velocity", justify="right")

            for week_data in velocity_trend:
                week_label = f"{week_data['week_start'].strftime('%b %d')}"
                trend_table.add_row(
                    week_label,
                    str(week_data["todos_completed"]),
                    f"{week_data['velocity']:.2f}/day",
                )

            console.print(trend_table)


@cli.command("review")
@click.option("--project", help="Focus on specific project")
@click.pass_context
def review(ctx, project: Optional[str]):
    """Daily standup review - show what needs attention"""

    db_manager = ctx.obj["db"]
    config = ctx.obj["config"]
    calculator = MetricsCalculator()
    scanner = GitScanner()

    console.print("\n[bold cyan]📋 Daily Review[/bold cyan]")
    console.print(f"[dim]{datetime.now().strftime('%A, %B %d, %Y')}[/dim]\n")

    with db_manager.get_session() as session:
        # Determine projects to review
        if project:
            projects = [session.query(Project).filter_by(name=project).first()]
            if not projects[0]:
                console.print(f"[bold red]Error:[/bold red] Project '{project}' not found")
                return
        else:
            # Review active projects
            projects = (
                session.query(Project)
                .filter_by(status="active")
                .order_by(Project.priority.desc())
                .limit(5)
                .all()
            )

        if not projects:
            console.print("[yellow]No active projects found[/yellow]")
            return

        for proj in projects:
            # Calculate health
            health_score, health_status = calculator.calculate_health_score(proj, session)
            health_color = (
                "green" if health_score >= 60 else "yellow" if health_score >= 40 else "red"
            )

            console.print(
                f"[bold]{proj.name}[/bold] - [{health_color}]{health_status} ({health_score:.0f}/100)[/{health_color}]"
            )

            # Recent activity
            if proj.has_git:
                recent_commits = scanner.get_recent_commits(proj, session, limit=3)
                if recent_commits:
                    console.print("  [dim]Recent commits:[/dim]")
                    for commit in recent_commits:
                        msg = commit.message.split("\n")[0]
                        console.print(
                            f"    • {truncate_string(msg, 60)} ({get_relative_time(commit.committed_at)})"
                        )

            # Active todos
            active_todos = (
                session.query(Todo)
                .filter(Todo.project_id == proj.id, Todo.status.in_(["open", "in_progress"]))
                .order_by(Todo.priority_score.desc())
                .limit(3)
                .all()
            )

            if active_todos:
                console.print("  [dim]Top priorities:[/dim]")
                for todo in active_todos:
                    status_icon = "🔵" if todo.status == "in_progress" else "⚪"
                    console.print(
                        f"    {status_icon} #{todo.id}: {todo.title} (priority: {todo.priority_score:.0f})"
                    )

            # Overdue
            overdue = calculator.get_overdue_todos(proj, session)
            if overdue:
                console.print(f"  [bold red]⚠ {len(overdue)} overdue todos[/bold red]")

            # Upcoming deadlines
            upcoming = calculator.get_upcoming_deadlines(proj, session, days=3)
            if upcoming:
                console.print(f"  [bold yellow]📅 {len(upcoming)} due in next 3 days[/bold yellow]")

            console.print()

        # Summary recommendations
        console.print("[bold cyan]💡 Recommendations:[/bold cyan]")

        # Find highest priority todo across all projects
        top_todo = (
            session.query(Todo)
            .filter(Todo.status.in_(["open", "in_progress"]))
            .order_by(Todo.priority_score.desc())
            .first()
        )

        if top_todo:
            console.print(
                f"  • Start with: [bold]#{top_todo.id} - {top_todo.title}[/bold] ({top_todo.project.name})"
            )

        # Find blocked todos
        blocked_count = session.query(Todo).filter(Todo.status == "blocked").count()

        if blocked_count > 0:
            console.print(f"  • Unblock {blocked_count} blocked todos")

        # Sync suggestion
        if config.get("auto_sync_on_review", True):
            console.print("  • Run [bold]pm sync --all[/bold] to update git activity")

        console.print()


@cli.command("report")
@click.argument("project_name")
@click.option(
    "--format", type=click.Choice(["markdown", "html"]), default="markdown", help="Output format"
)
@click.option("--output", type=click.Path(), help="Output file path")
@click.pass_context
def report(ctx, project_name: str, format: str, output: Optional[str]):
    """Generate project report"""

    db_manager = ctx.obj["db"]
    calculator = MetricsCalculator()
    scanner = GitScanner()

    with db_manager.get_session() as session:
        project = session.query(Project).filter_by(name=project_name).first()
        if not project:
            console.print(f"\n[bold red]Error:[/bold red] Project '{project_name}' not found")
            return

        # Gather all data
        health_score, health_status = calculator.calculate_health_score(project, session)
        velocity = calculator.calculate_velocity(project, session, days=7)
        completion_rate = calculator.calculate_completion_rate(project, session)
        todo_breakdown = calculator.get_todo_breakdown(project, session)
        goal_breakdown = calculator.get_goal_breakdown(project, session)
        commit_stats = scanner.get_commit_stats(
            project, session, since=datetime.utcnow() - timedelta(days=30)
        )
        overdue = calculator.get_overdue_todos(project, session)
        velocity_trend = calculator.get_velocity_trend(project, session, weeks=4)

        # Generate report
        if format == "markdown":
            report_content = f"""# Project Report: {project_name}

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Health Score

**{health_score:.1f}/100** - {health_status}

## Key Metrics

- **Velocity (7d):** {velocity:.2f} todos/day
- **Completion Rate:** {completion_rate:.1f}%
- **Last Activity:** {format_datetime(project.last_activity_at) if project.last_activity_at else 'Never'}

## Todo Status

| Status | Count |
|--------|-------|
| Open | {todo_breakdown['open']} |
| In Progress | {todo_breakdown['in_progress']} |
| Blocked | {todo_breakdown['blocked']} |
| Completed | {todo_breakdown['completed']} |
| **Total** | **{sum(todo_breakdown.values())}** |

## Goals

| Status | Count |
|--------|-------|
| Active | {goal_breakdown['active']} |
| Completed | {goal_breakdown['completed']} |
| Cancelled | {goal_breakdown['cancelled']} |

## Git Activity (30 days)

- **Commits:** {commit_stats['total_commits']}
- **Insertions:** +{commit_stats['total_insertions']}
- **Deletions:** -{commit_stats['total_deletions']}
- **Files Changed:** {commit_stats['total_files_changed']}
- **Unique Authors:** {commit_stats['unique_authors']}

## Velocity Trend (4 weeks)

| Week | Completed | Velocity |
|------|-----------|----------|
"""
            for week_data in velocity_trend:
                week_label = week_data["week_start"].strftime("%b %d")
                report_content += f"| {week_label} | {week_data['todos_completed']} | {week_data['velocity']:.2f}/day |\n"

            if overdue:
                report_content += f"\n## ⚠️ Overdue Todos ({len(overdue)})\n\n"
                for todo in overdue:
                    days_overdue = (date.today() - todo.due_date).days
                    report_content += f"- #{todo.id}: {todo.title} ({days_overdue} days overdue)\n"

            report_content += "\n---\n*Generated by PM CLI*\n"

        else:  # HTML format
            report_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Project Report: {project_name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 1200px; margin: 40px auto; padding: 20px; }}
        h1 {{ color: #333; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }}
        h2 {{ color: #666; margin-top: 30px; }}
        .health-score {{ font-size: 2em; color: {'#4CAF50' if health_score >= 60 else '#FFC107' if health_score >= 40 else '#F44336'}; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
        .metric {{ display: inline-block; margin: 10px 20px; }}
        .warning {{ color: #F44336; font-weight: bold; }}
    </style>
</head>
<body>
    <h1>Project Report: {project_name}</h1>
    <p><em>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</em></p>

    <h2>Health Score</h2>
    <div class="health-score">{health_score:.1f}/100 - {health_status}</div>

    <h2>Key Metrics</h2>
    <div class="metric"><strong>Velocity (7d):</strong> {velocity:.2f} todos/day</div>
    <div class="metric"><strong>Completion Rate:</strong> {completion_rate:.1f}%</div>
    <div class="metric"><strong>Last Activity:</strong> {format_datetime(project.last_activity_at) if project.last_activity_at else 'Never'}</div>

    <h2>Todo Status</h2>
    <table>
        <tr><th>Status</th><th>Count</th></tr>
        <tr><td>Open</td><td>{todo_breakdown['open']}</td></tr>
        <tr><td>In Progress</td><td>{todo_breakdown['in_progress']}</td></tr>
        <tr><td>Blocked</td><td>{todo_breakdown['blocked']}</td></tr>
        <tr><td>Completed</td><td>{todo_breakdown['completed']}</td></tr>
        <tr><th>Total</th><th>{sum(todo_breakdown.values())}</th></tr>
    </table>

    <h2>Git Activity (30 days)</h2>
    <table>
        <tr><th>Metric</th><th>Value</th></tr>
        <tr><td>Commits</td><td>{commit_stats['total_commits']}</td></tr>
        <tr><td>Insertions</td><td>+{commit_stats['total_insertions']}</td></tr>
        <tr><td>Deletions</td><td>-{commit_stats['total_deletions']}</td></tr>
        <tr><td>Files Changed</td><td>{commit_stats['total_files_changed']}</td></tr>
        <tr><td>Unique Authors</td><td>{commit_stats['unique_authors']}</td></tr>
    </table>

    <p><em>Generated by PM CLI</em></p>
</body>
</html>"""

        # Output
        if output:
            output_path = Path(output)
            output_path.write_text(report_content)
            console.print(f"\n[bold green]✓[/bold green] Report saved to: {output_path}")
        else:
            console.print("\n" + report_content)


# ============================================================================
# CLAUDE.md Integration Commands
# ============================================================================


@cli.command("import-claude-md")
@click.argument("project_name")
@click.option("--auto-import", is_flag=True, help="Automatically import goals without prompting")
@click.pass_context
def import_claude_md(ctx, project_name: str, auto_import: bool):
    """Parse CLAUDE.md and import metadata and goals"""

    db_manager = ctx.obj["db"]
    parser = ClaudeMdParser()

    with db_manager.get_session() as session:
        project = session.query(Project).filter_by(name=project_name).first()
        if not project:
            console.print(f"\n[bold red]Error:[/bold red] Project '{project_name}' not found")
            return

        # Find CLAUDE.md file
        claude_md_path = Path(project.path) / "CLAUDE.md"
        if not claude_md_path.exists():
            console.print(
                f"\n[bold yellow]Warning:[/bold yellow] No CLAUDE.md found in {project.path}"
            )
            return

        console.print("\n[bold cyan]Parsing CLAUDE.md...[/bold cyan]")

        # Parse file
        data = parser.parse_file(claude_md_path)

        # Update project description if found
        if data.get("description") and not project.description:
            project.description = data["description"]
            console.print("[bold green]✓[/bold green] Updated project description")

        # Update tech stack if found
        if data.get("tech_stack"):
            project.tech_stack = data["tech_stack"]
            console.print(
                f"[bold green]✓[/bold green] Found tech stack: {', '.join(data['tech_stack'][:5])}"
            )

        # Store commands in metadata
        if data.get("commands"):
            if not project.extra_data:
                project.extra_data = {}
            project.extra_data["commands"] = data["commands"]
            console.print(f"[bold green]✓[/bold green] Stored {len(data['commands'])} commands")

        session.commit()

        # Handle goals
        suggested_goals = data.get("goals", [])
        if suggested_goals:
            console.print(f"\n[bold cyan]Found {len(suggested_goals)} potential goals:[/bold cyan]")

            imported_count = 0
            for goal_data in suggested_goals:
                title = goal_data["title"]
                category = goal_data["category"]
                priority = parser.suggest_priority(title)

                # Check if goal already exists
                existing = (
                    session.query(Goal)
                    .filter(Goal.project_id == project.id, Goal.title == title)
                    .first()
                )

                if existing:
                    continue

                if auto_import:
                    should_import = True
                else:
                    # Ask user
                    console.print(f"\n  • {title}")
                    console.print(f"    Category: {category}, Priority: {priority}")

                    should_import = questionary.confirm("Import this goal?", default=True).ask()

                if should_import:
                    goal = Goal(
                        project_id=project.id,
                        title=title,
                        category=category,
                        priority=priority,
                        status="active",
                    )
                    session.add(goal)
                    imported_count += 1

            session.commit()

            console.print(f"\n[bold green]✓[/bold green] Imported {imported_count} goals")
        else:
            console.print("\n[yellow]No goals found in Next Steps/TODO/Roadmap sections[/yellow]")


# ============================================================================
# Interactive Workflow Commands
# ============================================================================


@cli.command("start")
@click.pass_context
def start_workflow(ctx):
    """Interactive workflow: pick project and todo, then start working"""

    db_manager = ctx.obj["db"]

    with db_manager.get_session() as session:
        # Step 1: Pick project
        projects = (
            session.query(Project)
            .filter_by(status="active")
            .order_by(Project.priority.desc())
            .all()
        )

        if not projects:
            console.print("[yellow]No active projects found[/yellow]")
            return

        project_choices = [
            {"name": f"{p.name} (priority: {p.priority})", "value": p.id} for p in projects
        ]

        project_id = questionary.select(
            "Which project do you want to work on?", choices=project_choices
        ).ask()

        if not project_id:
            return

        project = session.query(Project).filter_by(id=project_id).first()

        # Step 2: Pick todo
        todos = (
            session.query(Todo)
            .filter(Todo.project_id == project_id, Todo.status.in_(["open", "in_progress"]))
            .order_by(Todo.priority_score.desc())
            .limit(10)
            .all()
        )

        if not todos:
            console.print(f"\n[yellow]No open todos found in {project.name}[/yellow]")

            # Offer to create a todo
            create_todo = questionary.confirm(
                "Would you like to create a new todo?", default=True
            ).ask()

            if create_todo:
                title = questionary.text("Todo title:").ask()
                if title:
                    ctx.invoke(
                        todo_add,
                        project_name=project.name,
                        title=title,
                        description=None,
                        goal=None,
                        effort=None,
                        due=None,
                        tags=None,
                    )
            return

        todo_choices = [
            {
                "name": f"#{t.id}: {t.title} (priority: {t.priority_score:.0f}, effort: {t.effort_estimate or '?'})",
                "value": t.id,
            }
            for t in todos
        ]

        todo_id = questionary.select(f"Which todo in {project.name}?", choices=todo_choices).ask()

        if not todo_id:
            return

        # Step 3: Start the todo
        ctx.invoke(todo_start, todo_id=todo_id)

        # Step 4: Show what to do
        todo_obj = session.query(Todo).filter_by(id=todo_id).first()

        console.print("\n[bold green]🚀 Ready to work on:[/bold green]")
        console.print(f"  Project: {project.name}")
        console.print(f"  Todo: #{todo_obj.id} - {todo_obj.title}")

        if todo_obj.description:
            console.print(f"\n[dim]Description:[/dim]\n{todo_obj.description}")

        console.print("\n[bold cyan]💡 Tips:[/bold cyan]")
        console.print(f'  • Reference this todo in commits: git commit -m "fix: ... (#{todo_id})"')
        console.print(f"  • When done: [bold]pm todo complete {todo_id}[/bold]")
        console.print(f"  • View details: [bold]pm todo show {todo_id}[/bold]")


@cli.command("plan")
@click.argument("project_name")
@click.pass_context
def plan_workflow(ctx, project_name: str):
    """Interactive goal planning workflow"""

    db_manager = ctx.obj["db"]

    with db_manager.get_session() as session:
        project = session.query(Project).filter_by(name=project_name).first()
        if not project:
            console.print(f"\n[bold red]Error:[/bold red] Project '{project_name}' not found")
            return

        console.print(f"\n[bold cyan]Goal Planning for {project_name}[/bold cyan]\n")

        # Check for CLAUDE.md
        claude_md_path = Path(project.path) / "CLAUDE.md"
        if claude_md_path.exists():
            import_goals = questionary.confirm(
                "Found CLAUDE.md. Import goals from it?", default=True
            ).ask()

            if import_goals:
                ctx.invoke(import_claude_md, project_name=project_name, auto_import=False)
                return

        # Manual goal creation
        console.print("Let's create a new goal.\n")

        title = questionary.text("Goal title:").ask()
        if not title:
            return

        description = questionary.text("Description (optional):").ask()

        category = questionary.select(
            "Category:", choices=["feature", "bugfix", "refactor", "docs", "ops"]
        ).ask()

        priority = questionary.text(
            "Priority (0-100):", default="50", validate=lambda x: x.isdigit() and 0 <= int(x) <= 100
        ).ask()

        has_target = questionary.confirm("Set a target date?", default=False).ask()

        target_date = None
        if has_target:
            target = questionary.text("Target date (YYYY-MM-DD):").ask()
            if target:
                try:
                    target_date = parse_date(target)
                except Exception:
                    console.print("[yellow]Invalid date format, skipping target date[/yellow]")

        # Create goal
        goal = Goal(
            project_id=project.id,
            title=title,
            description=description,
            category=category,
            priority=int(priority),
            target_date=target_date,
            status="active",
        )

        session.add(goal)
        session.commit()

        console.print(f"\n[bold green]✓[/bold green] Created goal: [bold]{title}[/bold]")
        console.print(f"  ID: #{goal.id}")
        console.print(f"  Priority: {priority}")

        # Offer to create todos
        create_todos = questionary.confirm(
            "\nWould you like to create todos for this goal?", default=True
        ).ask()

        if create_todos:
            while True:
                todo_title = questionary.text("Todo title (or press Enter to finish):").ask()

                if not todo_title:
                    break

                ctx.invoke(
                    todo_add,
                    project_name=project_name,
                    title=todo_title,
                    description=None,
                    goal=goal.id,
                    effort=None,
                    due=None,
                    tags=None,
                )

                continue_adding = questionary.confirm("Add another todo?", default=True).ask()

                if not continue_adding:
                    break


@cli.command("standup")
@click.pass_context
def standup_workflow(ctx):
    """Interactive daily standup workflow"""

    console.print("\n[bold cyan]📋 Daily Standup[/bold cyan]")
    console.print(f"[dim]{datetime.now().strftime('%A, %B %d, %Y')}[/dim]\n")

    # Show review first
    ctx.invoke(review, project=None)

    # Ask what they're working on
    console.print("\n[bold cyan]What are you working on today?[/bold cyan]")

    action = questionary.select(
        "Choose an action:",
        choices=[
            {"name": "🚀 Start a todo", "value": "start"},
            {"name": "✅ Complete a todo", "value": "complete"},
            {"name": "📊 View metrics", "value": "metrics"},
            {"name": "🔄 Sync git activity", "value": "sync"},
            {"name": "❌ Skip", "value": "skip"},
        ],
    ).ask()

    if action == "start":
        ctx.invoke(start_workflow)
    elif action == "complete":
        # List in-progress todos
        db_manager = ctx.obj["db"]
        with db_manager.get_session() as session:
            in_progress = session.query(Todo).filter_by(status="in_progress").all()

            if not in_progress:
                console.print("\n[yellow]No todos in progress[/yellow]")
                return

            todo_choices = [
                {"name": f"#{t.id}: {t.title} ({t.project.name})", "value": t.id}
                for t in in_progress
            ]

            todo_id = questionary.select("Which todo did you complete?", choices=todo_choices).ask()

            if todo_id:
                ctx.invoke(todo_complete, todo_id=todo_id)

    elif action == "metrics":
        db_manager = ctx.obj["db"]
        with db_manager.get_session() as session:
            projects = (
                session.query(Project)
                .filter_by(status="active")
                .order_by(Project.priority.desc())
                .limit(5)
                .all()
            )

            project_choices = [{"name": p.name, "value": p.name} for p in projects]

            project_name = questionary.select("Which project?", choices=project_choices).ask()

            if project_name:
                ctx.invoke(metrics, project_name=project_name, detailed=False)

    elif action == "sync":
        ctx.invoke(sync_and_prioritize, project_name=None)


@cli.command("plan-day")
@click.pass_context
def plan_day_workflow(ctx):
    """Interactive daily planning workflow"""

    console.print("\n[bold cyan]📅 Plan Your Day[/bold cyan]")
    console.print(f"[dim]{datetime.now().strftime('%A, %B %d, %Y')}[/dim]\n")

    db_manager = ctx.obj["db"]

    # Step 1: Show yesterday's progress
    console.print("[bold]Yesterday's Progress:[/bold]")

    with db_manager.get_session() as session:
        # Get todos completed yesterday
        yesterday = datetime.now().date() - timedelta(days=1)
        completed_yesterday = (
            session.query(Todo)
            .filter(Todo.completed_at >= datetime.combine(yesterday, datetime.min.time()))
            .filter(
                Todo.completed_at < datetime.combine(datetime.now().date(), datetime.min.time())
            )
            .all()
        )

        if completed_yesterday:
            for todo in completed_yesterday:
                console.print(f"  ✓ {todo.title} ({todo.project.name})")
            console.print(f"\n[green]{len(completed_yesterday)} todos completed![/green]")
        else:
            console.print("  [dim]No todos completed yesterday[/dim]")

    # Step 2: Clear old "today" tags
    console.print("\n[dim]Clearing previous day's plan...[/dim]")

    with db_manager.get_session() as session:
        old_today_todos = session.query(Todo).filter(Todo.tags.contains("today")).all()

        for todo in old_today_todos:
            if todo.tags and "today" in todo.tags:
                tags_dict = todo.tags if isinstance(todo.tags, dict) else {}
                if "today" in tags_dict:
                    del tags_dict["today"]
                    todo.tags = tags_dict

        session.commit()

    # Step 3: Show top priorities
    console.print("\n[bold]Top Priorities:[/bold]")

    with db_manager.get_session() as session:
        top_todos = (
            session.query(Todo)
            .filter(Todo.status.in_(["open", "in_progress"]))
            .order_by(Todo.priority_score.desc())
            .limit(15)
            .all()
        )

        if not top_todos:
            console.print("[yellow]No open todos found.[/yellow]")
            return

        # Show top priorities
        for i, todo in enumerate(top_todos[:10], 1):
            status_icon = "🔵" if todo.status == "in_progress" else "⚪"
            effort = todo.effort_estimate or "?"
            console.print(
                f"  {i:2}. {status_icon} {todo.title[:50]} "
                f"[dim]({todo.project.name}, {effort}, {todo.priority_score:.1f})[/dim]"
            )

    # Step 4: Let user select todos for today
    console.print("\n[bold cyan]Select 3-5 todos for today:[/bold cyan]")
    console.print("[dim](Use space to select, enter to confirm)[/dim]\n")

    with db_manager.get_session() as session:
        top_todos = (
            session.query(Todo)
            .filter(Todo.status.in_(["open", "in_progress"]))
            .order_by(Todo.priority_score.desc())
            .limit(15)
            .all()
        )

        choices = [
            {
                "name": f"#{t.id}: {t.title[:60]} ({t.project.name}, {t.effort_estimate or '?'}, priority: {t.priority_score:.1f})",
                "value": t.id,
            }
            for t in top_todos
        ]

        selected_ids = questionary.checkbox("Select todos for today:", choices=choices).ask()

        if not selected_ids:
            console.print("\n[yellow]No todos selected. Planning cancelled.[/yellow]")
            return

        if len(selected_ids) > 7:
            console.print(
                f"\n[yellow]⚠ Warning: You selected {len(selected_ids)} todos. "
                "Consider limiting to 3-5 for a realistic daily plan.[/yellow]"
            )

        # Tag selected todos with "today"
        for todo_id in selected_ids:
            todo = session.query(Todo).filter_by(id=todo_id).first()
            if todo:
                tags_dict = todo.tags if isinstance(todo.tags, dict) else {}
                tags_dict["today"] = True
                todo.tags = tags_dict

        session.commit()

    # Step 5: Show daily plan
    console.print("\n[bold green]✓ Your Plan for Today:[/bold green]\n")

    with db_manager.get_session() as session:
        today_todos = (
            session.query(Todo)
            .filter(Todo.tags.contains("today"))
            .order_by(Todo.priority_score.desc())
            .all()
        )

        total_effort = {"S": 0, "M": 0, "L": 0, "XL": 0}

        for i, todo in enumerate(today_todos, 1):
            status_icon = "🔵" if todo.status == "in_progress" else "⚪"
            effort = todo.effort_estimate or "?"
            if effort in total_effort:
                total_effort[effort] += 1

            console.print(f"  {i}. {status_icon} {todo.title}")
            console.print(
                f"     [dim]{todo.project.name} • {effort} effort • Priority: {todo.priority_score:.1f}[/dim]"
            )

        # Show effort summary
        effort_parts = [f"{count}{size}" for size, count in total_effort.items() if count > 0]
        if effort_parts:
            console.print(f"\n[dim]Effort breakdown: {', '.join(effort_parts)}[/dim]")

        console.print(f"\n[bold]Total: {len(today_todos)} todos[/bold]")

    # Step 6: Ask if they want to start now
    console.print()
    start_now = questionary.confirm("Start working on the first todo now?", default=True).ask()

    if start_now:
        ctx.invoke(start_workflow)
    else:
        console.print("\n[green]Plan set! Use 'pm todos --today' to see your plan anytime.[/green]")


# ============================================================================
# Export/Import Commands
# ============================================================================


@cli.command("export")
@click.argument("project_name")
@click.option("--output", type=click.Path(), help="Output file path")
@click.pass_context
def export_project(ctx, project_name: str, output: Optional[str]):
    """Export project data to JSON"""

    db_manager = ctx.obj["db"]
    exporter = ExportImport()

    with db_manager.get_session() as session:
        project = session.query(Project).filter_by(name=project_name).first()
        if not project:
            console.print(f"\n[bold red]Error:[/bold red] Project '{project_name}' not found")
            return

        # Get all related data
        goals = session.query(Goal).filter_by(project_id=project.id).all()
        todos = session.query(Todo).filter_by(project_id=project.id).all()
        commits = session.query(Commit).filter_by(project_id=project.id).all()

        # Export
        data = exporter.export_project(project, goals, todos, commits, session)

        # Output
        if output:
            output_path = Path(output)
            output_path.write_text(json.dumps(data, indent=2))
            console.print(f"\n[bold green]✓[/bold green] Exported to: {output_path}")
        else:
            console.print("\n" + json.dumps(data, indent=2))

        console.print(
            f"\n[dim]Exported {len(goals)} goals, {len(todos)} todos, {len(commits)} commits[/dim]"
        )


@cli.command("backup")
@click.option("--output", type=click.Path(), help="Backup directory path")
@click.pass_context
def backup_all(ctx, output: Optional[str]):
    """Backup all projects to JSON files"""

    db_manager = ctx.obj["db"]

    if not output:
        output = str(Path.home() / ".pm" / "backups" / datetime.now().strftime("%Y%m%d_%H%M%S"))

    output_dir = Path(output)
    output_dir.mkdir(parents=True, exist_ok=True)

    with db_manager.get_session() as session:
        projects = session.query(Project).all()

        console.print(f"\n[bold cyan]Backing up {len(projects)} projects...[/bold cyan]")

        for project in projects:
            ctx.invoke(
                export_project,
                project_name=project.name,
                output=str(output_dir / f"{project.name}.json"),
            )

    console.print(f"\n[bold green]✓[/bold green] Backup complete: {output_dir}")


# ============================================================================
# Cheatsheet Command
# ============================================================================


@cli.command("cheatsheet")
@click.option("--workflow", is_flag=True, help="Show workflow-focused commands only")
def cheatsheet(workflow: bool):
    """Show quick reference of common PM commands"""

    console.print("\n[bold cyan]📚 PM CLI Cheatsheet[/bold cyan]\n")

    if workflow:
        # Workflow-focused cheatsheet
        console.print("[bold]🌅 Morning Planning[/bold]")
        morning = Table(show_header=False, box=None, padding=(0, 2))
        morning.add_row("[cyan]pm standup[/cyan]", "Daily overview with top priorities")
        morning.add_row("[cyan]pm plan-day[/cyan]", "Interactive planning (select 3-5 todos)")
        morning.add_row("[cyan]pm todos --today[/cyan]", "See today's plan")
        morning.add_row("[cyan]pm start[/cyan]", "Begin first task")
        console.print(morning)

        console.print("\n[bold]☀️  During the Day[/bold]")
        day = Table(show_header=False, box=None, padding=(0, 2))
        day.add_row("[cyan]pm start[/cyan]", "Pick next priority task")
        day.add_row("[cyan]pm todo complete 15[/cyan]", "Mark todo as done")
        day.add_row("[cyan]pm todos --today[/cyan]", "Check today's status")
        day.add_row("[cyan]pm todos --next[/cyan]", "See all top priorities")
        day.add_row("[cyan]pm todo block 18 --by 19[/cyan]", "Mark todo as blocked")
        console.print(day)

        console.print("\n[bold]🌙 Evening Reflection[/bold]")
        evening = Table(show_header=False, box=None, padding=(0, 2))
        evening.add_row("[cyan]pm sync --all[/cyan]", "Sync today's commits")
        evening.add_row("[cyan]pm review[/cyan]", "See accomplishments")
        evening.add_row("[cyan]pm metrics <project>[/cyan]", "Check project health")
        evening.add_row("[cyan]pm todos --next[/cyan]", "Preview tomorrow")
        console.print(evening)

        console.print(
            "\n[dim]💡 Tip: Reference todos in commits: git commit -m \"feat: add feature (#15)\"[/dim]"
        )

    else:
        # Full cheatsheet
        console.print("[bold]🚀 Getting Started[/bold]")
        start = Table(show_header=False, box=None, padding=(0, 2))
        start.add_row("[cyan]pm init[/cyan]", "Initialize PM and scan workspace")
        start.add_row("[cyan]pm projects[/cyan]", "List all projects")
        start.add_row("[cyan]pm project show <name>[/cyan]", "View project details")
        console.print(start)

        console.print("\n[bold]🎯 Goals & Todos[/bold]")
        goals = Table(show_header=False, box=None, padding=(0, 2))
        goals.add_row("[cyan]pm goals[/cyan]", "List all goals")
        goals.add_row(
            "[cyan]pm goal add <proj> \"Goal\"[/cyan]", "Create goal (add --priority 90)"
        )
        goals.add_row("[cyan]pm todos[/cyan]", "List open todos")
        goals.add_row("[cyan]pm todos --next[/cyan]", "Top 5 priorities")
        goals.add_row("[cyan]pm todo add <proj> \"Task\"[/cyan]", "Create todo")
        goals.add_row("[cyan]pm todo start 15[/cyan]", "Mark as in_progress")
        goals.add_row("[cyan]pm todo complete 15[/cyan]", "Mark as done")
        console.print(goals)

        console.print("\n[bold]📊 Analytics[/bold]")
        analytics = Table(show_header=False, box=None, padding=(0, 2))
        analytics.add_row("[cyan]pm metrics <project>[/cyan]", "Show health dashboard")
        analytics.add_row("[cyan]pm review[/cyan]", "Daily standup view")
        analytics.add_row("[cyan]pm activity <project>[/cyan]", "Show commit timeline")
        console.print(analytics)

        console.print("\n[bold]🔄 Git Integration[/bold]")
        git = Table(show_header=False, box=None, padding=(0, 2))
        git.add_row("[cyan]pm sync <project>[/cyan]", "Sync commits from git")
        git.add_row("[cyan]pm sync --all[/cyan]", "Sync all projects")
        git.add_row("[cyan]pm commits <project>[/cyan]", "Show recent commits")
        console.print(git)

        console.print("\n[bold]🎨 Workflow Commands[/bold]")
        workflow_cmds = Table(show_header=False, box=None, padding=(0, 2))
        workflow_cmds.add_row("[cyan]pm standup[/cyan]", "Daily standup overview")
        workflow_cmds.add_row("[cyan]pm plan-day[/cyan]", "Interactive daily planning")
        workflow_cmds.add_row("[cyan]pm start[/cyan]", "Pick & start next task")
        workflow_cmds.add_row("[cyan]pm prioritize[/cyan]", "Recalculate priorities")
        console.print(workflow_cmds)

        console.print("\n[bold]🛠️  Useful Options[/bold]")
        options = Table(show_header=False, box=None, padding=(0, 2))
        options.add_row("[cyan]pm todos --today[/cyan]", "Filter by 'today' tag")
        options.add_row("[cyan]pm todos --tag urgent[/cyan]", "Filter by any tag")
        options.add_row("[cyan]pm todos --blocked[/cyan]", "Show blocked todos")
        options.add_row(
            "[cyan]pm metrics <proj> --detailed[/cyan]", "Show velocity trends"
        )
        console.print(options)

        console.print("\n[dim]💡 Pro Tips:[/dim]")
        console.print(
            "[dim]  • Use 'pm cheatsheet --workflow' for daily workflow commands[/dim]"
        )
        console.print(
            "[dim]  • Reference todos in commits: git commit -m \"feat: add feature (#15)\"[/dim]"
        )
        console.print("[dim]  • Use 'pm <command> --help' for detailed help[/dim]")

    console.print()


def main():
    """Entry point for the CLI"""
    cli(obj={})


if __name__ == "__main__":
    main()
