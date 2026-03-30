"""
scan_project.py
Run this from your project root:
    python scan_project.py

Gives you:
  - Empty files
  - Syntax errors
  - Import errors
  - Missing packages
  - File stats
"""

import os
import ast
import sys

sys.path.insert(0, ".")

project_root = "."
src_path = os.path.join(project_root, "src")

total_files = 0
empty_files = []
error_files = []
all_stats = {}

print("=" * 60)
print("  AP TOURISM — PROJECT SCAN")
print("=" * 60)

# ── Step 1: Scan all .py files ────────────────────────────────
print("\n[1/3] Scanning files...\n")

for root, dirs, files in os.walk(src_path):
    dirs[:] = [d for d in dirs if d != "__pycache__"]
    for file in files:
        if not file.endswith(".py"):
            continue
        filepath = os.path.join(root, file)
        rel_path = os.path.relpath(filepath, project_root)
        total_files += 1

        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        lines = len(content.splitlines())

        if lines == 0:
            empty_files.append(rel_path)
            continue

        try:
            tree = ast.parse(content)
            functions = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
            classes   = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
            all_stats[rel_path] = {
                "lines":     lines,
                "functions": len(functions),
                "classes":   len(classes),
            }
        except SyntaxError as e:
            error_files.append((rel_path, str(e)))

total_lines = sum(v["lines"] for v in all_stats.values())

print(f"  Total files   : {total_files}")
print(f"  Empty files   : {len(empty_files)}")
print(f"  Syntax errors : {len(error_files)}")
print(f"  Total lines   : {total_lines}")

# ── Empty files ───────────────────────────────────────────────
if empty_files:
    print("\n--- EMPTY FILES (need code) ---")
    for f in empty_files:
        print(f"  EMPTY  {f}")
else:
    print("\n  [OK] No empty files")

# ── Syntax errors ─────────────────────────────────────────────
if error_files:
    print("\n--- SYNTAX ERRORS ---")
    for f, e in error_files:
        print(f"  ERROR  {f}")
        print(f"         {e}")
else:
    print("  [OK] No syntax errors")

# ── Top 10 largest files ──────────────────────────────────────
print("\n--- TOP 10 LARGEST FILES ---")
for path, s in sorted(all_stats.items(), key=lambda x: -x[1]["lines"])[:10]:
    print(f"  {s['lines']:>5} lines   {path}")

# ── Step 2: Import every module ───────────────────────────────
print("\n" + "=" * 60)
print("[2/3] Checking imports...\n")

failed_imports = []
ok_imports = []

for root, dirs, files in os.walk(src_path):
    dirs[:] = [d for d in dirs if d != "__pycache__"]
    for file in files:
        if not file.endswith(".py"):
            continue
        filepath = os.path.join(root, file)
        rel_path = os.path.relpath(filepath, project_root)

        # Skip empty files and __init__ files
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read().strip()
        if not content or content.startswith("#"):
            continue

        module = rel_path.replace(os.sep, ".").replace(".py", "")

        try:
            __import__(module)
            ok_imports.append(module)
        except Exception as e:
            failed_imports.append((module, type(e).__name__, str(e)))

print(f"  OK     : {len(ok_imports)}")
print(f"  FAILED : {len(failed_imports)}")

if failed_imports:
    print("\n--- IMPORT ERRORS ---")
    for mod, err_type, err_msg in failed_imports:
        print(f"\n  FAIL   {mod}")
        print(f"         {err_type}: {err_msg}")
else:
    print("\n  [OK] All modules import successfully!")

# ── Step 3: Check installed packages ─────────────────────────
print("\n" + "=" * 60)
print("[3/3] Checking key packages...\n")

required = [
    "fastapi", "uvicorn", "sqlalchemy", "asyncpg", "alembic",
    "pydantic", "pydantic_settings", "redis", "httpx",
    "jose", "passlib", "razorpay", "aioboto3",
    "celery", "elasticsearch", "aiosmtplib",
    "google.oauth2", "firebase_admin",
]

missing = []
for pkg in required:
    try:
        __import__(pkg)
        print(f"  OK      {pkg}")
    except ImportError:
        print(f"  MISSING {pkg}")
        missing.append(pkg)

# ── Summary ───────────────────────────────────────────────────
print("\n" + "=" * 60)
print("  SUMMARY")
print("=" * 60)
print(f"  Empty files    : {len(empty_files)}")
print(f"  Syntax errors  : {len(error_files)}")
print(f"  Import errors  : {len(failed_imports)}")
print(f"  Missing pkgs   : {len(missing)}")

if not empty_files and not error_files and not failed_imports and not missing:
    print("\n  ALL GOOD — ready to run the server!")
    print("  uvicorn src.main:app --reload --port 8000")
else:
    print("\n  Fix the issues above, then run:")
    print("  uvicorn src.main:app --reload --port 8000")

print("=" * 60)
