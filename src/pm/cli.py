"""Main CLI application for PM tool"""

import click
from pathlib import Path
from typing import Optional
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from . import __version__
from .db import get_db_manager, init_database
from .models import Project, Goal, Todo
from .utils import (
    Config,
    format_datetime,
    format_date,
    parse_date,
    get_project_name_from_path,
    is_git_repo,
    validate_priority,
    validate_status,
    PROJECT_STATUSES,
    GOAL_STATUSES,
    GOAL_CATEGORIES,
    TODO_STATUSES,
    EFFORT_LEVELS,
)
from .priority import PriorityCalculator

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
@click.option("--category", "-c", type=click.Choice(GOAL_CATEGORIES), default="feature", help="Goal category")
@click.option("--priority", "-p", type=int, default=50, help="Priority (0-100)")
@click.option("--target", "-t", help="Target date (YYYY-MM-DD)")
@click.pass_context
def goal_add(ctx, project_name: str, title: str, description: Optional[str],
             category: str, priority: int, target: Optional[str]):
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

        row_data.extend([
            g["title"],
            f"[{category_color}]{g['category']}[/{category_color}]",
            str(g["priority"]),
            f"[{status_color}]{g['status']}[/{status_color}]",
            format_date(g["target_date"]),
            str(g["todo_count"]),
        ])

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

    if data['description']:
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
def goal_update(ctx, goal_id: int, status: Optional[str], priority: Optional[int], target: Optional[str]):
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

        console.print(f"\n[bold green]✓[/bold green] Updated goal #{goal_id}: [bold]{goal.title}[/bold]")
        for field in updated_fields:
            console.print(f"  • {field}")


# Alias 'goals' to 'goal list'
@cli.command("goals")
@click.argument("project_name", required=False)
@click.option("--status", type=click.Choice(GOAL_STATUSES), help="Filter by status")
@click.option("--priority-min", type=int, help="Minimum priority")
@click.pass_context
def goals_alias(ctx, project_name: Optional[str], status: Optional[str], priority_min: Optional[int]):
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
def todo_add(ctx, project_name: str, title: str, description: Optional[str],
             goal: Optional[int], effort: Optional[str], due: Optional[str], tags: Optional[str]):
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
                console.print(f"\n[bold red]Error:[/bold red] Goal #{goal} not found in project '{project_name}'")
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
@click.pass_context
def todo_list(ctx, project_name: Optional[str], status: Optional[str], goal: Optional[int],
              show_next: bool, blocked: bool):
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

        row_data.extend([
            t["title"],
            f"[{status_color}]{t['status']}[/{status_color}]",
            f"[{priority_color}]{t['priority_score']:.1f}[/{priority_color}]",
            t["effort"] or "-",
            format_date(t["due_date"]),
            t["goal_title"] or "-",
        ])

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
        }

    # Create info panel
    info = f"""[bold]ID:[/bold] #{data['id']}
[bold]Title:[/bold] {data['title']}
[bold]Project:[/bold] {data['project_name']}
[bold]Status:[/bold] {data['status']}
[bold]Priority Score:[/bold] {data['priority_score']:.1f}
"""

    if data['goal_title']:
        info += f"[bold]Goal:[/bold] {data['goal_title']}\n"

    if data['effort']:
        info += f"[bold]Effort:[/bold] {data['effort']}\n"

    if data['due_date']:
        info += f"[bold]Due:[/bold] {format_date(data['due_date'])}\n"

    if data['tags']:
        info += f"[bold]Tags:[/bold] {', '.join(data['tags'])}\n"

    if data['blocked_by']:
        info += f"[bold]Blocked By:[/bold] Todos #{', #'.join(map(str, data['blocked_by']))}\n"

    info += f"\n[bold]Created:[/bold] {format_datetime(data['created_at'])}\n"
    info += f"[bold]Updated:[/bold] {format_datetime(data['updated_at'])}\n"

    if data['started_at']:
        info += f"[bold]Started:[/bold] {format_datetime(data['started_at'])}\n"

    if data['completed_at']:
        info += f"[bold]Completed:[/bold] {format_datetime(data['completed_at'])}\n"

    if data['description']:
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
            console.print(f"\n[bold yellow]Warning:[/bold yellow] Todo #{todo_id} is already completed")
            return

        todo_obj.status = "in_progress"
        todo_obj.started_at = datetime.utcnow()

        # Recalculate priority (in_progress gets 1.2x boost)
        config = ctx.obj["config"]
        calculator = PriorityCalculator(config)
        todo_obj.priority_score = calculator.calculate_priority(todo_obj, session)

        session.commit()

        console.print(f"\n[bold green]✓[/bold green] Started todo #{todo_id}: [bold]{todo_obj.title}[/bold]")
        console.print(f"  Status: in_progress")
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
            console.print(f"\n[bold yellow]Warning:[/bold yellow] Todo #{todo_id} is already completed")
            return

        todo_obj.status = "completed"
        todo_obj.completed_at = datetime.utcnow()

        session.commit()

        console.print(f"\n[bold green]✓[/bold green] Completed todo #{todo_id}: [bold]{todo_obj.title}[/bold]")
        console.print(f"  🎉 Great work!")


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

            console.print(f"\n[bold yellow]⚠[/bold yellow] Todo #{todo_id} blocked by #{blocked_by_id}")
            console.print(f"  Status: blocked")
            console.print(f"  Priority Score: {todo_obj.priority_score:.1f}")
        else:
            console.print(f"\n[bold yellow]Warning:[/bold yellow] Todo #{todo_id} already blocked by #{blocked_by_id}")


# Alias 'todos' to 'todo list'
@cli.command("todos")
@click.argument("project_name", required=False)
@click.option("--status", type=click.Choice(TODO_STATUSES), help="Filter by status")
@click.option("--goal", type=int, help="Filter by goal ID")
@click.option("--next", "show_next", is_flag=True, help="Show top 5 by priority")
@click.option("--blocked", is_flag=True, help="Show only blocked todos")
@click.pass_context
def todos_alias(ctx, project_name: Optional[str], status: Optional[str], goal: Optional[int],
                show_next: bool, blocked: bool):
    """List todos (alias for 'todo list')"""
    ctx.invoke(todo_list, project_name=project_name, status=status, goal=goal,
               show_next=show_next, blocked=blocked)


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
        console.print(f"\n[bold green]✓[/bold green] Recalculated priorities for {count} todos {scope}")


def main():
    """Entry point for the CLI"""
    cli(obj={})


if __name__ == "__main__":
    main()
