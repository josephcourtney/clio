import ast
from pathlib import Path


DUnderWhitelist = {"__version__"}


def find_public_names(tree: ast.Module) -> list[str]:
    names = set()

    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                name = alias.asname or alias.name
                if not name.startswith("_") or name in DUnderWhitelist:
                    names.add(name)

        elif isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname or alias.name.split(".")[0]
                if not name.startswith("_") or name in DUnderWhitelist:
                    names.add(name)

    return sorted(names)


def update_dunder_all(path: Path, new_all: list[str]) -> None:
    code = path.read_text()
    tree = ast.parse(code)

    lines = code.splitlines()
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    start, end = node.lineno - 1, node.end_lineno
                    indent = " " * (len(lines[start]) - len(lines[start].lstrip()))
                    new_all_str = ", ".join(f'"{name}"' for name in new_all)
                    replacement = f'{indent}__all__ = [{new_all_str}]'
                    lines[start:end] = [replacement]
                    path.write_text("\n".join(lines) + "\n")
                    print(f"✅ Updated __all__ in {path}")
                    return

    # No __all__ found — add one at the end
    new_all_str = ", ".join(f'"{name}"' for name in new_all)
    lines.append(f'__all__ = [{new_all_str}]')
    path.write_text("\n".join(lines) + "\n")
    print(f"➕ Added __all__ to {path}")


def main(path: str = "src/clio/__init__.py"):
    p = Path(path)
    tree = ast.parse(p.read_text())
    names = find_public_names(tree)
    update_dunder_all(p, names)


if __name__ == "__main__":
    main()

