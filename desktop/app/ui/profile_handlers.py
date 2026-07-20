from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QMessageBox

from ..services.profile_service import ControllerProfile


class ProfileHandlersMixin:
    def _profile_selected(self, profile_id: str | None) -> None:
        self._selected_profile_id = profile_id

    def _create_profile(self, name: str) -> None:
        profile = ControllerProfile.create(name=name or "New profile")
        self.profile_collection.profiles.append(profile)
        self._selected_profile_id = profile.profile_id
        self._save_profiles_to_disk()
        self._refresh_profiles()
        self.diagnostics.info("Profiles", f"Created {profile.name}")

    def _duplicate_profile(self) -> None:
        selected = self._selected_profile()
        if selected is None:
            return
        copy = self.profile_store.duplicate(selected)
        self.profile_collection.profiles.append(copy)
        self._selected_profile_id = copy.profile_id
        self._save_profiles_to_disk()
        self._refresh_profiles()
        self.diagnostics.info("Profiles", f"Duplicated {selected.name}")

    def _delete_profile(self) -> None:
        selected = self._selected_profile()
        if selected is None:
            return
        if len(self.profile_collection.profiles) <= 1:
            QMessageBox.warning(self, "Cannot delete", "At least one profile must remain.")
            return
        answer = QMessageBox.question(self, "Delete profile", f"Delete '{selected.name}'?")
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.profile_collection.profiles = [p for p in self.profile_collection.profiles if p.profile_id != selected.profile_id]
        if self.profile_collection.active_profile_id == selected.profile_id:
            self.profile_collection.active_profile_id = self.profile_collection.profiles[0].profile_id
        self._selected_profile_id = self.profile_collection.active_profile_id
        self._save_profiles_to_disk()
        self._refresh_profiles()
        self.diagnostics.info("Profiles", f"Deleted {selected.name}")

    def _activate_selected_profile(self) -> None:
        selected = self._selected_profile()
        if selected is None:
            return
        errors = selected.validate()
        if errors:
            QMessageBox.warning(self, "Invalid profile", "\n".join(errors[:12]))
            return
        self.profile_collection.active_profile_id = selected.profile_id
        self._save_profiles_to_disk()
        self.channel_mapper.reset()
        self._refresh_profiles()
        self.diagnostics.info("Profiles", f"Activated {selected.name}")

    def _save_profile_details(self, name: str, guid: str) -> None:
        selected = self._selected_profile()
        if selected is None:
            return
        selected.name = name.strip() or selected.name
        selected.device_guid = guid.strip() or "*"
        selected.touch()
        self._save_profiles_to_disk()
        self._refresh_profiles()
        self.diagnostics.info("Profiles", f"Updated {selected.name}")

    def _import_profile(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "Import profile", "", "JSON files (*.json)")
        if not filename:
            return
        try:
            profile = self.profile_store.import_profile(Path(filename))
        except (OSError, ValueError, TypeError, KeyError) as exc:
            QMessageBox.critical(self, "Import failed", str(exc))
            return
        self.profile_collection.profiles.append(profile)
        self._selected_profile_id = profile.profile_id
        self._save_profiles_to_disk()
        self._refresh_profiles()
        self.diagnostics.info("Profiles", f"Imported {profile.name}")

    def _export_profile(self) -> None:
        selected = self._selected_profile()
        if selected is None:
            return
        filename, _ = QFileDialog.getSaveFileName(self, "Export profile", f"{selected.name}.json", "JSON files (*.json)")
        if not filename:
            return
        try:
            self.profile_store.export_profile(selected, Path(filename))
        except OSError as exc:
            QMessageBox.critical(self, "Export failed", str(exc))
            return
        self.diagnostics.info("Profiles", f"Exported {selected.name} to {filename}")

    def _save_profiles_to_disk(self) -> None:
        try:
            self.profile_store.save(self.profile_collection)
        except OSError as exc:
            QMessageBox.critical(self, "Profile save failed", str(exc))
