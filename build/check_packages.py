"""Check every ``package.published`` flag against the real package index.

The registry claims which names are live. This asks PyPI. Run it before a
release, and after one — a stale ``published: false`` hides a real install
command, and a stale ``published: true`` publishes a command that 404s.

    python -m build.check_packages

Exits non-zero if the registry and the index disagree. Needs network; that is
why it is a separate command rather than part of ``make check``.
"""

from __future__ import annotations

import sys
import urllib.error
import urllib.request

from .site import Registry

TIMEOUT = 10


def is_live(registry: str, name: str) -> bool | None:
    """True/False if the index answered, None if it could not be reached."""
    if registry != "pypi":
        return None
    url = f"https://pypi.org/pypi/{name}/json"
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT) as response:
            return response.status == 200
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return False
        return None
    except OSError:
        return None


def main() -> int:
    reg = Registry.load()
    disagreements: list[str] = []
    unreachable: list[str] = []

    for product in reg.products:
        package = product.get("package")
        if not package:
            continue
        live = is_live(package["registry"], package["name"])
        claimed = package["published"]
        if live is None:
            unreachable.append(package["name"])
            print(f"  ?  {package['name']:<20} index unreachable")
            continue
        mark = "ok" if live == claimed else "!!"
        print(f"  {mark} {package['name']:<20} index={live} registry={claimed}")
        if live != claimed:
            disagreements.append(
                f"{product['slug']}: package.published is {claimed} but "
                f"{package['name']} is {'live' if live else 'absent'} on {package['registry']}"
            )

    if disagreements:
        print("\n" + "\n".join(disagreements), file=sys.stderr)
        return 1
    if unreachable:
        print(f"\n{len(unreachable)} name(s) unchecked — no network?", file=sys.stderr)
        return 2
    print("\nregistry agrees with the index")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
