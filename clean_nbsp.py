# clean_nbsp.py
import pathlib
import shutil

EXTENSIONS = {".py", ".sh", ".env", ".yaml", ".yml", ".swift", ".txt", ".json", ".css", ".html", ".svg"}
SKIP_DIR_NAMES = {".venv", "venv", "__pycache__", ".git", ".mypy_cache", ".pytest_cache"}
SKIP_SUFFIXES = {".bak"}


def should_skip(path: pathlib.Path) -> bool:
    for part in path.parts:
        if part in SKIP_DIR_NAMES:
            return True
    if path.suffix in SKIP_SUFFIXES:
        return True
    return False


def clean_nbsp_everywhere(root="."):
    total_fixed = 0
    total_skipped = 0

    for path in pathlib.Path(root).rglob("*"):
        if path.is_dir():
            continue

        if should_skip(path):
            continue

        if path.suffix not in EXTENSIONS:
            continue

        try:
            content = path.read_text(encoding="utf-8")
        except Exception as e:
            print(f"⚠️ Could not read {path}: {e}")
            total_skipped += 1
            continue

        if "\u00a0" in content:
            print(f"🧹 Cleaning NBSPs in: {path}")
            backup = path.with_suffix(path.suffix + ".bak")
            if not backup.exists():
                shutil.copy(path, backup)

            fixed = content.replace("\u00a0", " ")
            path.write_text(fixed, encoding="utf-8")
            total_fixed += 1

    print(f"\n✅ Clean complete! Fixed {total_fixed} files, skipped {total_skipped}.\n")


if __name__ == "__main__":
    clean_nbsp_everywhere(".")