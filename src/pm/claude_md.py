"""CLAUDE.md file parsing and integration"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class ClaudeMdParser:
    """Parser for CLAUDE.md files to extract project metadata and goals"""

    def __init__(self):
        """Initialize parser"""
        pass

    def parse_file(self, file_path: Path) -> Dict:
        """Parse CLAUDE.md file and extract structured data

        Args:
            file_path: Path to CLAUDE.md file

        Returns:
            Dictionary with extracted metadata
        """
        if not file_path.exists():
            return {}

        content = file_path.read_text()

        return {
            "description": self._extract_description(content),
            "tech_stack": self._extract_tech_stack(content),
            "commands": self._extract_commands(content),
            "goals": self._extract_goals(content),
            "architecture": self._extract_architecture(content),
        }

    def _extract_description(self, content: str) -> Optional[str]:
        """Extract project description from Overview or first paragraph

        Args:
            content: CLAUDE.md file content

        Returns:
            Description text or None
        """
        # Look for Overview section
        overview_match = re.search(
            r'##\s+Overview\s*\n+(.*?)(?=\n##|\Z)',
            content,
            re.DOTALL | re.IGNORECASE
        )

        if overview_match:
            desc = overview_match.group(1).strip()
            # Take first paragraph
            first_para = desc.split('\n\n')[0]
            return first_para[:500]  # Limit length

        # Fallback: first paragraph after title
        lines = content.split('\n')
        desc_lines = []
        found_title = False

        for line in lines:
            if line.startswith('# '):
                found_title = True
                continue
            if found_title and line.strip():
                if line.startswith('#'):
                    break
                desc_lines.append(line)
                if len(' '.join(desc_lines)) > 500:
                    break

        if desc_lines:
            return ' '.join(desc_lines).strip()[:500]

        return None

    def _extract_tech_stack(self, content: str) -> List[str]:
        """Extract technology stack from content

        Args:
            content: CLAUDE.md file content

        Returns:
            List of technologies mentioned
        """
        tech_keywords = {
            'python', 'javascript', 'typescript', 'react', 'vue', 'angular',
            'node', 'express', 'fastapi', 'django', 'flask',
            'swift', 'kotlin', 'java', 'go', 'rust',
            'postgresql', 'mysql', 'mongodb', 'redis',
            'docker', 'kubernetes', 'aws', 'gcp', 'azure',
            'nextjs', 'gatsby', 'nuxt', 'svelte',
        }

        content_lower = content.lower()
        found_tech = []

        for tech in tech_keywords:
            if tech in content_lower:
                found_tech.append(tech.title())

        return found_tech[:10]  # Limit to top 10

    def _extract_commands(self, content: str) -> Dict[str, str]:
        """Extract command examples from Commands section

        Args:
            content: CLAUDE.md file content

        Returns:
            Dictionary mapping command names to commands
        """
        commands = {}

        # Look for Commands section
        commands_match = re.search(
            r'##\s+Commands\s*\n+(.*?)(?=\n##|\Z)',
            content,
            re.DOTALL | re.IGNORECASE
        )

        if not commands_match:
            return commands

        commands_section = commands_match.group(1)

        # Extract code blocks
        code_blocks = re.findall(
            r'```(?:bash|sh)?\n(.*?)```',
            commands_section,
            re.DOTALL
        )

        for i, block in enumerate(code_blocks):
            lines = block.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Extract command name from first word
                    parts = line.split()
                    if parts:
                        cmd_name = parts[0]
                        if cmd_name not in ['cd', 'export', 'source']:
                            commands[f"{cmd_name}_{i}"] = line

        return commands

    def _extract_goals(self, content: str) -> List[Dict[str, str]]:
        """Extract potential goals from Next Steps, TODO, or Roadmap sections

        Args:
            content: CLAUDE.md file content

        Returns:
            List of goal dictionaries with title and category
        """
        goals = []

        # Look for relevant sections
        section_patterns = [
            r'##\s+Next\s+Steps\s*\n+(.*?)(?=\n##|\Z)',
            r'##\s+TODO\s*\n+(.*?)(?=\n##|\Z)',
            r'##\s+Roadmap\s*\n+(.*?)(?=\n##|\Z)',
            r'##\s+Planned\s+Features\s*\n+(.*?)(?=\n##|\Z)',
        ]

        for pattern in section_patterns:
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                section_content = match.group(1)
                goals.extend(self._parse_goal_items(section_content))

        return goals

    def _parse_goal_items(self, content: str) -> List[Dict[str, str]]:
        """Parse individual goal items from a section

        Args:
            content: Section content

        Returns:
            List of goal dictionaries
        """
        goals = []

        # Match list items (bullets or checkboxes)
        patterns = [
            r'^\s*[-*]\s+\[[ x]\]\s+(.+)$',  # Checkbox list
            r'^\s*[-*]\s+(.+)$',              # Bullet list
            r'^\s*\d+\.\s+(.+)$',             # Numbered list
        ]

        lines = content.split('\n')
        for line in lines:
            for pattern in patterns:
                match = re.match(pattern, line)
                if match:
                    title = match.group(1).strip()
                    # Skip if it's a heading or too short
                    if len(title) > 5 and not title.startswith('#'):
                        category = self._infer_category(title)
                        goals.append({
                            'title': title,
                            'category': category,
                        })
                    break

        return goals

    def _infer_category(self, title: str) -> str:
        """Infer goal category from title

        Args:
            title: Goal title

        Returns:
            Category string
        """
        title_lower = title.lower()

        if any(word in title_lower for word in ['fix', 'bug', 'issue', 'error']):
            return 'bugfix'
        elif any(word in title_lower for word in ['refactor', 'cleanup', 'improve']):
            return 'refactor'
        elif any(word in title_lower for word in ['doc', 'readme', 'guide']):
            return 'docs'
        elif any(word in title_lower for word in ['deploy', 'ci', 'test', 'build']):
            return 'ops'
        else:
            return 'feature'

    def _extract_architecture(self, content: str) -> Optional[str]:
        """Extract architecture description

        Args:
            content: CLAUDE.md file content

        Returns:
            Architecture description or None
        """
        arch_match = re.search(
            r'##\s+Architecture\s*\n+(.*?)(?=\n##|\Z)',
            content,
            re.DOTALL | re.IGNORECASE
        )

        if arch_match:
            arch_text = arch_match.group(1).strip()
            return arch_text[:1000]  # Limit length

        return None

    def suggest_priority(self, goal_title: str) -> int:
        """Suggest priority based on goal title keywords

        Args:
            goal_title: Goal title text

        Returns:
            Suggested priority (0-100)
        """
        title_lower = goal_title.lower()

        # High priority keywords
        if any(word in title_lower for word in ['critical', 'urgent', 'blocker', 'security']):
            return 90

        # Medium-high priority
        if any(word in title_lower for word in ['important', 'bug', 'fix', 'issue']):
            return 70

        # Medium priority
        if any(word in title_lower for word in ['enhance', 'improve', 'optimize']):
            return 60

        # Default
        return 50


class ExportImport:
    """Export and import project data for backup/restore"""

    def __init__(self):
        """Initialize export/import handler"""
        pass

    def export_project(self, project, goals, todos, commits, session) -> Dict:
        """Export project data to dictionary

        Args:
            project: Project object
            goals: List of Goal objects
            todos: List of Todo objects
            commits: List of Commit objects
            session: Database session

        Returns:
            Dictionary with all project data
        """
        return {
            'version': '1.0',
            'project': {
                'name': project.name,
                'path': project.path,
                'description': project.description,
                'tech_stack': project.tech_stack,
                'status': project.status,
                'priority': project.priority,
                'has_git': project.has_git,
                'extra_data': project.extra_data,
            },
            'goals': [
                {
                    'title': g.title,
                    'description': g.description,
                    'category': g.category,
                    'priority': g.priority,
                    'status': g.status,
                    'target_date': g.target_date.isoformat() if g.target_date else None,
                }
                for g in goals
            ],
            'todos': [
                {
                    'title': t.title,
                    'description': t.description,
                    'goal_title': t.goal.title if t.goal else None,
                    'status': t.status,
                    'effort_estimate': t.effort_estimate,
                    'due_date': t.due_date.isoformat() if t.due_date else None,
                    'tags': t.tags,
                    'blocked_by': t.blocked_by,
                }
                for t in todos
            ],
            'commits': [
                {
                    'sha': c.sha,
                    'message': c.message,
                    'author': c.author,
                    'committed_at': c.committed_at.isoformat(),
                    'insertions': c.insertions,
                    'deletions': c.deletions,
                    'files_changed': c.files_changed,
                }
                for c in commits
            ],
        }

    def import_project(self, data: Dict, session) -> Tuple[bool, str]:
        """Import project data from dictionary

        Args:
            data: Dictionary with project data
            session: Database session

        Returns:
            Tuple of (success, message)
        """
        # This would be implemented to import data
        # For now, just validate structure
        required_keys = ['version', 'project', 'goals', 'todos']

        for key in required_keys:
            if key not in data:
                return False, f"Missing required key: {key}"

        return True, "Data structure valid"
