from __future__ import annotations

from pathlib import Path
from typing import Dict


class PromptLoader:
    def __init__(self) -> None:
        self.base_path = Path(__file__).parent / "prompt_templates"
        self._cache: Dict[str, str] = {}

    def _load_file(self, filename: str) -> str:
        path = self.base_path / filename

        if not path.exists():
            raise FileNotFoundError(f"Prompt file not found: {filename}")

        return path.read_text(encoding="utf-8")

    def get_prompt(self, name: str) -> str:
        """
        name examples:
        - bol_extraction
        - invoice_extraction
        - ratecon_extraction
        - validation_rules
        """

        filename = f"{name}.txt"

        if filename in self._cache:
            return self._cache[filename]

        content = self._load_file(filename)
        self._cache[filename] = content

        return content

    def get_bol_prompt(self) -> str:
        return self.get_prompt("bol_extraction")

    def get_invoice_prompt(self) -> str:
        return self.get_prompt("invoice_extraction")

    def get_ratecon_prompt(self) -> str:
        return self.get_prompt("ratecon_extraction")

    def get_validation_prompt(self) -> str:
        return self.get_prompt("validation_rules")


# singleton (recommended for services)
prompt_loader = PromptLoader()