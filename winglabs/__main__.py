from __future__ import annotations

import sys


def main() -> None:
    if "--cli" in sys.argv:
        from winglabs.cli import main as cli_main

        cli_main()
    else:
        from winglabs.ui.app import main as gui_main

        gui_main()


if __name__ == "__main__":
    main()
