"""Load prompts from Markdown in this directory."""

import re
from collections import defaultdict
from pathlib import Path
from typing import Dict

_base_dir = Path(__file__).parent

# TODO: The prompts used by each agent should be configurable per user, maybe
# as a FastAPI/PydanticAI Depends based on toggles saved in localStorage.
PROMPTS: Dict[str, str | None] = defaultdict(lambda: None)

for _f in _base_dir.glob("*.md"):
    if _f.is_file():
        with _f.open(encoding="utf-8") as f:
            content = f.read()
            # Remove all <!-- ... --> comments (including multiline), including surrounding whitespace/newlines.
            content = re.sub(
                r"^[ \t]*<!--.*?-->[ \t]*(\r?\n)?",
                "",
                content,
                flags=re.DOTALL | re.MULTILINE,
            )
            PROMPTS[_f.name] = content.strip()
