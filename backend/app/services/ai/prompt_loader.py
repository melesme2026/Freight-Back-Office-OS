from __future__ import annotations

from pathlib import Path


class PromptLoader:
    def __init__(self) -> None:
        self.base_path = Path(__file__).resolve().parent / "prompt_templates"
        self._cache: dict[str, str] = {}

    def _load_file(self, filename: str) -> str:
        path = self.base_path / filename

        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"Prompt file not found: {filename}")

        try:
            return path.read_text(encoding="utf-8")
        except OSError as exc:
            raise OSError(f"Unable to read prompt file: {filename}") from exc

    def get_prompt(self, name: str) -> str:
        """
        name examples:
        - bol_extraction
        - invoice_extraction
        - ratecon_extraction
        - validation_rules
        """

        filename = f"{name}.txt"

        cached = self._cache.get(filename)
        if cached is not None:
            return cached

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