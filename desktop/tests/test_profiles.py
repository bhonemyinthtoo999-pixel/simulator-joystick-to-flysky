from pathlib import Path

from app.services.profile_service import ControllerProfile, ProfileCollection, ProfileStore


def test_profile_store_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "profiles.json"
    store = ProfileStore(path)
    profile = ControllerProfile.create("Test")
    collection = ProfileCollection(profile.profile_id, [profile])
    store.save(collection)
    loaded = store.load()
    assert loaded.active_profile_id == profile.profile_id
    assert loaded.profiles[0].name == "Test"
    assert len(loaded.profiles[0].mappings) == 8
