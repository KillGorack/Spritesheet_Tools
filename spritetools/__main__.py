"""Start Spritesheet Tools: `spritesheet-tools`, or `python3 -m spritetools` from the source folder."""
import argparse

from . import __version__


def main() -> None:
    ap = argparse.ArgumentParser(prog="spritesheet-tools", description="Spritesheet Tools")
    ap.add_argument("--install-menu", action="store_true", help="add the applications-menu entry and icon")
    ap.add_argument("--uninstall-menu", action="store_true", help="remove the applications-menu entry and icon")
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = ap.parse_args()

    if args.install_menu or args.uninstall_menu:
        from . import desktop
        desktop.install_menu() if args.install_menu else desktop.uninstall_menu()
        return

    from .ui.app import App
    App().run()


if __name__ == "__main__":
    main()
