"""Desktop preferences, independent of historical case save formats."""

from dataclasses import asdict, dataclass
import json
from pathlib import Path

from .storage import SessionStore, atomic_json_write


@dataclass
class DesktopPreferences:
    language: str = "en"
    volume: int = 35
    width: int = 1280
    height: int = 720
    active_case: str | None = None

    def to_dict(self):
        return {"schema_version": 1, **asdict(self)}

    @classmethod
    def from_dict(cls, data):
        expected = {"schema_version", "language", "volume", "width", "height", "active_case"}
        if not isinstance(data, dict) or set(data) != expected or type(data["schema_version"]) is not int or data["schema_version"] != 1:
            raise ValueError("Invalid desktop preferences")
        if data["language"] not in ("en", "zh-Hant"):
            raise ValueError("Invalid desktop language")
        if type(data["volume"]) is not int or not 0 <= data["volume"] <= 100:
            raise ValueError("Invalid desktop volume")
        if any(type(data[key]) is not int for key in ("width", "height")):
            raise ValueError("Invalid window size")
        if not 320 <= data["width"] <= 7680 or not 180 <= data["height"] <= 4320:
            raise ValueError("Invalid window size")
        if abs(data["width"] / data["height"] - 16 / 9) > .01:
            raise ValueError("Window size must use the desktop aspect ratio")
        if data["active_case"] not in (None, *(f"T{i:02}" for i in range(1, 9)), "M01", *(f"W{i:02}" for i in range(1, 7))):
            raise ValueError("Invalid active case")
        return cls(**{key: value for key, value in data.items() if key != "schema_version"})


class DesktopStore:
    def __init__(self, path):
        self.path = Path(path)
        self.warning = ""
        self.blocked = False

    def load(self):
        if not self.path.exists():
            return DesktopPreferences()
        try:
            if self.path.stat().st_size > 8192:
                raise ValueError("Desktop preferences too large")
            return DesktopPreferences.from_dict(json.loads(self.path.read_text(encoding="utf-8")))
        except (OSError, ValueError, TypeError):
            try:
                SessionStore(self.path).preserve_invalid()
                self.warning = "backup"
            except OSError:
                self.blocked = True
                self.warning = "save_error"
            return DesktopPreferences()

    def save(self, preferences):
        if self.blocked:
            raise OSError("Cannot preserve unreadable desktop preferences; original retained")
        data = preferences.to_dict()
        DesktopPreferences.from_dict(data)
        atomic_json_write(self.path, data)


def window_sizes(available_width, available_height):
    """Client sizes that leave room for native Windows decorations."""
    max_width = max(320, available_width - 32)
    max_height = max(180, available_height - 64)
    scale = min(max_width / 1280, max_height / 720)
    units = max(20, int(min(scale, 1) * 80))
    fitted = (units * 16, units * 9)
    presets = [(640, 360), (960, 540), (1280, 720), (1600, 900), (1920, 1080)]
    result = [size for size in presets if size[0] <= max_width and size[1] <= max_height]
    if fitted not in result:
        result.append(fitted)
    result.sort()
    return tuple(result)
