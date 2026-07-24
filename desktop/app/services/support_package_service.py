from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import platform
from typing import Any, Iterable
import zipfile

from .diagnostics_service import DiagnosticEntry


class SupportPackageService:
    """Create a user-selected ZIP containing only app support information."""

    README = """Simulator Joystick to FlySky support package
================================================

This package was created only after the user pressed Create Support Package.
It contains application, controller, adapter, mapping and diagnostic summaries.
It does not include passwords, personal documents, joystick movement history,
or unrelated files from the computer.

မြန်မာ
------
ဤ support package ကို အသုံးပြုသူက Create Support Package ကိုနှိပ်ပြီးမှသာ
ဖန်တီးထားပါသည်။ App၊ controller၊ adapter၊ mapping နှင့် diagnostic အကျဉ်းချုပ်များသာ
ပါဝင်ပြီး password၊ ကိုယ်ရေးဖိုင်၊ joystick လှုပ်ရှားမှုမှတ်တမ်းနှင့် အခြားဖိုင်များ မပါဝင်ပါ။
"""

    @staticmethod
    def create(
        destination: Path,
        *,
        context: dict[str, Any],
        diagnostics: Iterable[DiagnosticEntry],
        validation_report: dict[str, Any] | None = None,
    ) -> Path:
        path = destination
        if path.suffix.casefold() != ".zip":
            path = path.with_suffix(".zip")
        path.parent.mkdir(parents=True, exist_ok=True)

        generated_at = datetime.now().astimezone().isoformat(timespec="seconds")
        manifest = {
            "schema_version": 1,
            "generated_at": generated_at,
            "privacy": {
                "user_initiated": True,
                "contains_passwords": False,
                "contains_personal_files": False,
                "contains_joystick_history": False,
            },
            "system": {
                "operating_system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
            },
            "application_context": context,
        }

        diagnostic_lines = [
            "Simulator Joystick to FlySky diagnostics",
            "=" * 56,
            f"Generated: {generated_at}",
            "",
        ]
        diagnostic_lines.extend(entry.format() for entry in diagnostics)

        with zipfile.ZipFile(
            path,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        ) as archive:
            archive.writestr("README.txt", SupportPackageService.README)
            archive.writestr(
                "support-context.json",
                json.dumps(manifest, ensure_ascii=False, indent=2),
            )
            archive.writestr(
                "diagnostics.txt",
                "\n".join(diagnostic_lines) + "\n",
            )
            if validation_report:
                archive.writestr(
                    "hardware-validation.json",
                    json.dumps(validation_report, ensure_ascii=False, indent=2),
                )
        return path
