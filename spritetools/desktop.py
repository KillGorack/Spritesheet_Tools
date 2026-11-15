"""Add or remove the applications-menu entry (Linux, per user, no admin).

pipx installs the `spritesheet-tools` command but not a menu entry, so the app writes its own:
    spritesheet-tools --install-menu
    spritesheet-tools --uninstall-menu
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

APP_ID = "spritesheet-tools"
ICON_SIZE = 128
ASSETS = Path(__file__).resolve().parent / "assets"


def _data_home() -> Path:
    return Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")


def _paths():
    data = _data_home()
    return (data / "applications" / f"{APP_ID}.desktop",
            data / "icons" / "hicolor" / f"{ICON_SIZE}x{ICON_SIZE}" / "apps" / f"{APP_ID}.png")


def _command() -> str:
    """The installed command (pipx puts it in ~/.local/bin), or this Python running the package."""
    found = shutil.which(APP_ID)
    if found:
        return found
    return f'"{sys.executable}" -m spritetools'


def _refresh(applications: Path, icons: Path) -> None:
    for cmd in (["update-desktop-database", str(applications)],
                ["gtk-update-icon-cache", "-q", str(icons)],
                ["kbuildsycoca6"]):
        if shutil.which(cmd[0]):
            subprocess.run(cmd, capture_output=True)


def install_menu() -> None:
    desktop, icon = _paths()
    desktop.parent.mkdir(parents=True, exist_ok=True)
    icon.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ASSETS / "icon.png", icon)
    desktop.write_text(
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=Spritesheet Tools\n"
        "Comment=Spritesheets, animations, autotile tilesets and batch image jobs for 2D games\n"
        f"Exec={_command()}\n"
        f"Icon={icon}\n"
        "Terminal=false\n"
        "Categories=Graphics;2DGraphics;\n"
        "StartupNotify=true\n"
    )
    desktop.chmod(0o755)
    _refresh(desktop.parent, _data_home() / "icons" / "hicolor")
    print(f"Menu entry added: {desktop}")


def uninstall_menu() -> None:
    desktop, icon = _paths()
    for f in (desktop, icon):
        if f.exists():
            f.unlink()
    _refresh(desktop.parent, _data_home() / "icons" / "hicolor")
    print("Menu entry removed. Your settings are still in ~/.config/spritetools/.")
