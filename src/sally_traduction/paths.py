"""Emplacements des modèles et ressources, en développement comme dans l'exécutable."""
import sys
from pathlib import Path

FROZEN = getattr(sys, "frozen", False)


def app_dir() -> Path:
    if FROZEN:
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def models_dir() -> Path:
    return app_dir() / "models"


def assets_dir() -> Path:
    if FROZEN:
        return Path(getattr(sys, "_MEIPASS", app_dir())) / "assets"
    return app_dir() / "assets"


def user_dir() -> Path:
    import os
    base = os.environ.get("APPDATA") or str(Path.home())
    return Path(base) / "SallyTraduction"


MODELS = {
    "opus-en-fr": "opus-mt-en-fr-ct2",
    "opus-fr-en": "opus-mt-fr-en-ct2",
    "m2m100": "m2m100_418m-ct2",
    "minilm": "minilm",
    "lid": "lid",
}


def model_path(key: str) -> Path:
    return models_dir() / MODELS[key]


def model_available(key: str) -> bool:
    return model_path(key).exists()
