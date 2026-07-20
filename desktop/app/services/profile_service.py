from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from .channel_mapping_service import ChannelMapping, default_mappings


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class ControllerProfile:
    profile_id: str
    name: str
    device_guid: str = "*"
    channel_count: int = 8
    mappings: list[ChannelMapping] = field(default_factory=default_mappings)
    ppm_frame_us: int = 22500
    ppm_pulse_us: int = 300
    ppm_polarity: str = "positive"
    failsafe_timeout_ms: int = 700
    created_at: str = field(default_factory=_utc_now)
    updated_at: str = field(default_factory=_utc_now)

    @classmethod
    def create(cls, name: str = "Default", channel_count: int = 8) -> "ControllerProfile":
        return cls(
            profile_id=str(uuid4()),
            name=name.strip() or "Untitled profile",
            channel_count=channel_count,
            mappings=default_mappings(channel_count),
        )

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.name.strip():
            errors.append("profile name is required")
        if not 4 <= self.channel_count <= 16:
            errors.append("channel_count must be 4..16")
        if len(self.mappings) != self.channel_count:
            errors.append("mapping count must equal channel_count")
        if not 10000 <= self.ppm_frame_us <= 40000:
            errors.append("ppm_frame_us must be 10000..40000")
        if not 100 <= self.ppm_pulse_us <= 1000:
            errors.append("ppm_pulse_us must be 100..1000")
        if self.ppm_polarity not in {"positive", "negative"}:
            errors.append("ppm_polarity must be positive or negative")
        if not 100 <= self.failsafe_timeout_ms <= 10000:
            errors.append("failsafe_timeout_ms must be 100..10000")
        for mapping in self.mappings:
            errors.extend(f"CH{mapping.channel}: {error}" for error in mapping.validate())
        minimum_frame = sum(max(800, mapping.maximum) for mapping in self.mappings) + self.ppm_pulse_us
        if self.ppm_frame_us <= minimum_frame:
            errors.append("PPM frame is too short for the configured channel maximums")
        return errors

    def touch(self) -> None:
        self.updated_at = _utc_now()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["mappings"] = [mapping.to_dict() for mapping in self.mappings]
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ControllerProfile":
        values = dict(payload)
        values["mappings"] = [ChannelMapping.from_dict(item) for item in payload.get("mappings", [])]
        profile = cls(**values)
        if not profile.mappings:
            profile.mappings = default_mappings(profile.channel_count)
        return profile


@dataclass
class ProfileCollection:
    active_profile_id: str | None = None
    profiles: list[ControllerProfile] = field(default_factory=list)


class ProfileStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or (Path.home() / ".simulator-joystick-to-flysky" / "profiles.json")

    def load(self) -> ProfileCollection:
        if not self.path.exists():
            default = ControllerProfile.create()
            return ProfileCollection(active_profile_id=default.profile_id, profiles=[default])
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            profiles = [ControllerProfile.from_dict(item) for item in payload.get("profiles", [])]
            if not profiles:
                default = ControllerProfile.create()
                return ProfileCollection(active_profile_id=default.profile_id, profiles=[default])
            active = payload.get("active_profile_id")
            if active not in {profile.profile_id for profile in profiles}:
                active = profiles[0].profile_id
            return ProfileCollection(active_profile_id=active, profiles=profiles)
        except (OSError, ValueError, TypeError, KeyError):
            default = ControllerProfile.create()
            return ProfileCollection(active_profile_id=default.profile_id, profiles=[default])

    def save(self, collection: ProfileCollection) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": 1,
            "active_profile_id": collection.active_profile_id,
            "profiles": [profile.to_dict() for profile in collection.profiles],
        }
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        temporary.replace(self.path)

    @staticmethod
    def active(collection: ProfileCollection) -> ControllerProfile:
        for profile in collection.profiles:
            if profile.profile_id == collection.active_profile_id:
                return profile
        if not collection.profiles:
            profile = ControllerProfile.create()
            collection.profiles.append(profile)
        collection.active_profile_id = collection.profiles[0].profile_id
        return collection.profiles[0]

    @staticmethod
    def find(collection: ProfileCollection, profile_id: str | None) -> ControllerProfile | None:
        return next((profile for profile in collection.profiles if profile.profile_id == profile_id), None)

    @staticmethod
    def duplicate(profile: ControllerProfile, name: str | None = None) -> ControllerProfile:
        payload = profile.to_dict()
        payload["profile_id"] = str(uuid4())
        payload["name"] = name or f"{profile.name} Copy"
        payload["created_at"] = _utc_now()
        payload["updated_at"] = payload["created_at"]
        return ControllerProfile.from_dict(payload)

    @staticmethod
    def export_profile(profile: ControllerProfile, path: Path) -> None:
        path.write_text(json.dumps({"schema_version": 1, "profile": profile.to_dict()}, indent=2), encoding="utf-8")

    @staticmethod
    def import_profile(path: Path) -> ControllerProfile:
        payload = json.loads(path.read_text(encoding="utf-8"))
        raw = payload.get("profile", payload)
        profile = ControllerProfile.from_dict(raw)
        profile.profile_id = str(uuid4())
        profile.name = f"{profile.name} (Imported)"
        profile.created_at = _utc_now()
        profile.updated_at = profile.created_at
        return profile
