"""SkillSourceScanner — discovers and parses SKILL.md-based skills."""

from __future__ import annotations

from pathlib import Path
import re
from typing import TYPE_CHECKING, Any

import yaml

from lexigram.ai.skills.exceptions import SkillExecutionError, SkillValidationError
from lexigram.contracts.ai.skills import SkillDefinition, SkillError
from lexigram.logging import (
    get_logger,
)
from lexigram.result import Err, Ok, Result

if TYPE_CHECKING:
    from lexigram.ai.skills.registry import SkillRegistry

from lexigram.ai.skills.base.core import FunctionSkill
from lexigram.ai.skills.discovery.skill_loader import SkillLoader

logger = get_logger(__name__)

SKILL_MD_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)", re.DOTALL)
ARGUMENT_PLACEHOLDER = "$ARGUMENTS"
ARGUMENT_ESCAPED = "$$ARGUMENTS"


class SkillSourceScanner:
    """Discovers and registers SKILL.md-based skills.

    Features:
    - YAML frontmatter parsing (name, description, version, author, tags)
    - $ARGUMENTS placeholder substitution
    - Instruction-only skills (skill body as instructions)
    - Executable skills (scripts/main.py)
    - Bundled context files (reference.md, forms.md, etc.)
    - Configurable max depth for nested discovery
    """

    def __init__(
        self,
        loader: SkillLoader | None = None,
        max_depth: int | None = 5,
        skill_root: Path | None = None,
        allowed_script_types: tuple[str, ...] | None = None,
    ) -> None:
        """Initialize the scanner.

        Args:
            loader: Optional SkillLoader for executing scripts.
            max_depth: Maximum directory depth to scan (None for unlimited).
            skill_root: Root directory that skill scripts must resolve
                inside of (passed through to the default SkillLoader).
            allowed_script_types: Script suffixes permitted for execution
                (passed through to the default SkillLoader).
        """
        self._loader = loader or SkillLoader(
            skill_root=skill_root,
            allowed_script_types=allowed_script_types,
        )
        self._max_depth = max_depth

    async def scan(self, registry: SkillRegistry, root: str | Path) -> int:
        """Scan a directory tree for SKILL.md folders and register them.

        Args:
            registry: The SkillRegistry to register discovered skills.
            root: Root directory to scan.

        Returns:
            Number of skills successfully registered.
        """
        root = Path(root).expanduser().resolve()
        if not root.exists():
            logger.warning("skill_source_scanner_root_not_found", path=str(root))
            return 0

        count = 0
        for md_path in self._find_skill_files(root):
            skill_dir = md_path.parent
            result = await self._register_skill(registry, skill_dir)
            if result.is_ok():
                count += 1
            else:
                err = result.unwrap_err()
                logger.warning(
                    "skill_source_scanner_register_failed",
                    skill_dir=str(skill_dir),
                    error=str(err),
                )

        logger.info(
            "skill_source_scanner_scan_complete",
            skills_registered=count,
            root=str(root),
        )
        return count

    def _find_skill_files(self, root: Path) -> list[Path]:
        """Find all SKILL.md files within max_depth.

        Args:
            root: Root directory to search.

        Returns:
            List of SKILL.md file paths.
        """
        if self._max_depth is None:
            return list(root.rglob("SKILL.md"))

        root_depth = len(root.parts)
        return [
            md_path
            for md_path in root.rglob("SKILL.md")
            if len(md_path.parent.parts) - root_depth <= self._max_depth
        ]

    async def _register_skill(
        self, registry: SkillRegistry, skill_dir: Path
    ) -> Result[None, SkillError]:
        """Parse SKILL.md and register as a skill."""
        md_path = skill_dir / "SKILL.md"
        if not md_path.exists():
            return Err(SkillValidationError(skill_dir.name, ["SKILL.md not found"]))

        try:
            content = md_path.read_text(encoding="utf-8")
        except OSError as exc:
            return Err(
                SkillExecutionError(
                    f"Failed to read {md_path}",
                    skill_name=skill_dir.name,
                    cause=exc,
                )
            )

        skill_info = await self._parse_skill_file(md_path)
        if skill_info.is_err():
            return Err(skill_info.unwrap_err())

        info = skill_info.unwrap()
        name = info["name"]
        description = info.get("description", "")
        body = info.get("body", "")
        allowed_tools = info.get("allowed_tools", [])
        context_files = info.get("context_files", [])
        hooks = info.get("hooks", {})

        has_script = (skill_dir / "scripts" / "main.py").exists()

        skill = self._create_skill(
            name=name,
            description=description,
            body=body,
            skill_dir=skill_dir,
            has_script=has_script,
            allowed_tools=allowed_tools,
            context_files=context_files,
            hooks=hooks,
        )

        try:
            registry.register(skill)
            logger.debug("skill_source_scanner_registered", skill=name)
            return Ok(None)
        except Exception as exc:  # noqa: BLE001  # skill registration can fail for any reason; surfaced as Err
            return Err(
                SkillExecutionError(
                    f"Failed to register skill {name}",
                    skill_name=name,
                    cause=exc,
                )
            )

    async def _parse_skill_file(
        self, md_path: Path
    ) -> Result[dict[str, Any], SkillError]:
        """Parse SKILL.md file into structured data."""
        try:
            content = md_path.read_text(encoding="utf-8")
        except OSError as exc:
            return Err(
                SkillExecutionError(
                    f"Failed to read {md_path}",
                    skill_name=md_path.stem,
                    cause=exc,
                )
            )

        if not content.startswith("---"):
            return Err(
                SkillValidationError(
                    md_path.stem,
                    ["Missing YAML frontmatter - must start with '---'"],
                )
            )

        match = SKILL_MD_PATTERN.match(content)
        if not match:
            return Err(
                SkillValidationError(
                    md_path.stem,
                    ["Invalid SKILL.md format - missing frontmatter separator"],
                )
            )

        frontmatter_raw, body = match.groups()

        try:
            frontmatter: dict[str, Any] = yaml.safe_load(frontmatter_raw) or {}
        except yaml.YAMLError as exc:
            return Err(
                SkillValidationError(
                    md_path.stem,
                    [f"Invalid YAML frontmatter: {exc}"],
                )
            )

        name = frontmatter.get("name") or md_path.parent.name
        description = frontmatter.get("description", "")
        version = frontmatter.get("version")
        author = frontmatter.get("author")
        tags = frontmatter.get("tags", [])
        model = frontmatter.get("model")
        allowed_tools = frontmatter.get("allowed-tools", [])
        context_files = frontmatter.get("context", [])
        hooks = frontmatter.get("hooks", {})

        skill_dir = md_path.parent
        has_script = (skill_dir / "scripts" / "main.py").exists()

        return Ok(
            {
                "name": name,
                "description": description,
                "version": version,
                "author": author,
                "tags": tags,
                "model": model,
                "allowed_tools": allowed_tools,
                "context_files": context_files,
                "hooks": hooks,
                "body": body.strip(),
                "has_script": has_script,
            }
        )

    def _create_skill(
        self,
        name: str,
        description: str,
        body: str,
        skill_dir: Path,
        has_script: bool,
        allowed_tools: list[str],
        context_files: list[str],
        hooks: dict[str, str],
    ) -> FunctionSkill:
        """Create a FunctionSkill from parsed SKILL.md data."""
        definition = SkillDefinition(
            name=name,
            description=description,
            category="skill_source",
            metadata={
                "skill_dir": str(skill_dir),
                "has_script": has_script,
                "body": body,
                "allowed_tools": allowed_tools,
                "context_files": context_files,
                "hooks": hooks,
            },
        )

        async def _execute(**kwargs: Any) -> dict[str, Any]:
            processed_body = body
            if kwargs:
                args_str = ", ".join(f"{k}={v!r}" for k, v in kwargs.items())
                processed_body = body.replace(ARGUMENT_PLACEHOLDER, args_str)
                processed_body = processed_body.replace(ARGUMENT_ESCAPED, "$ARGUMENTS")

            if has_script:
                return await self._loader.execute_script(
                    skill_dir / "scripts" / "main.py",
                    kwargs,
                )
            return {
                "status": "instruction_only",
                "instructions": processed_body,
                "skill_dir": str(skill_dir),
                "context_files": context_files,
            }

        return FunctionSkill(_execute, definition)


__all__ = ["SkillSourceScanner"]
