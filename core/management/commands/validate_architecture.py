"""
Management command to validate app architecture against project standards.

Usage:
    python manage.py validate_architecture                 # Check all apps
    python manage.py validate_architecture apps/crm/       # Check specific app
"""

import os
import sys

from django.conf import settings
from django.core.management.base import BaseCommand


REQUIRED_DIRS = ["models", "services", "serializers", "views", "tests"]
REQUIRED_FILES = ["__init__.py", "apps.py", "admin.py", "urls.py"]
APPS_DIR = os.path.join(settings.BASE_DIR, "apps")


class Command(BaseCommand):
    help = "Validate that apps follow the standard architecture"

    def add_arguments(self, parser):
        parser.add_argument(
            "app_paths",
            nargs="*",
            type=str,
            help="Specific app paths to check (e.g., apps/crm/). Checks all if omitted.",
        )

    def handle(self, *args, **options):
        errors = []
        warnings = []
        app_paths = options["app_paths"]

        if app_paths:
            app_dirs = []
            for p in app_paths:
                clean = p.rstrip("/")
                if os.path.isdir(os.path.join(settings.BASE_DIR, clean)):
                    app_dirs.append(clean)
                else:
                    errors.append(f"Path does not exist: {clean}")
        else:
            app_dirs = self._discover_apps()

        for app_dir in app_dirs:
            app_name = os.path.basename(app_dir)
            full_path = os.path.join(settings.BASE_DIR, app_dir)
            self.stdout.write(f"\nChecking {app_name}...")

            app_errors, app_warnings = self._check_app(app_name, full_path)
            errors.extend(app_errors)
            warnings.extend(app_warnings)

        self.stdout.write("")

        for w in warnings:
            self.stdout.write(self.style.WARNING(f"  WARNING: {w}"))

        for e in errors:
            self.stdout.write(self.style.ERROR(f"  ERROR: {e}"))

        if errors:
            self.stdout.write(self.style.ERROR(f"\n{len(errors)} error(s), {len(warnings)} warning(s)"))
            sys.exit(1)
        else:
            self.stdout.write(self.style.SUCCESS(f"\nAll checks passed. {len(warnings)} warning(s)."))

    def _discover_apps(self):
        """Find all app directories under apps/."""
        app_dirs = []
        if not os.path.exists(APPS_DIR):
            return app_dirs

        for item in sorted(os.listdir(APPS_DIR)):
            item_path = os.path.join(APPS_DIR, item)
            if os.path.isdir(item_path) and not item.startswith("__"):
                if os.path.exists(os.path.join(item_path, "apps.py")):
                    app_dirs.append(f"apps/{item}")
        return app_dirs

    def _check_app(self, app_name, full_path):
        """Run all checks on a single app."""
        errors = []
        warnings = []

        # Check required directories
        for d in REQUIRED_DIRS:
            dir_path = os.path.join(full_path, d)
            if not os.path.isdir(dir_path):
                errors.append(f"[{app_name}] Missing required directory: {d}/")
            else:
                init_path = os.path.join(dir_path, "__init__.py")
                if not os.path.exists(init_path):
                    errors.append(f"[{app_name}] Missing __init__.py in {d}/")

        # Check required files
        for f in REQUIRED_FILES:
            if not os.path.exists(os.path.join(full_path, f)):
                errors.append(f"[{app_name}] Missing required file: {f}")

        # Warn about monolithic files that should be split
        monolithic_models = os.path.join(full_path, "models.py")
        models_dir = os.path.join(full_path, "models")
        if os.path.exists(monolithic_models) and os.path.isdir(models_dir):
            warnings.append(
                f"[{app_name}] Both models.py and models/ exist. "
                "Remove models.py after splitting into models/ package."
            )

        monolithic_views = os.path.join(full_path, "views.py")
        views_dir = os.path.join(full_path, "views")
        if os.path.exists(monolithic_views) and os.path.isdir(views_dir):
            warnings.append(
                f"[{app_name}] Both views.py and views/ exist. "
                "Remove views.py after splitting into views/ package."
            )

        # Check for large monolithic files
        for filename in ["views.py", "models.py"]:
            filepath = os.path.join(full_path, filename)
            if os.path.exists(filepath):
                line_count = sum(1 for _ in open(filepath))
                if line_count > 300:
                    warnings.append(
                        f"[{app_name}] {filename} has {line_count} lines. "
                        "Consider splitting into a package."
                    )

        # Check tests directory has required test files
        tests_dir = os.path.join(full_path, "tests")
        if os.path.isdir(tests_dir):
            expected_tests = ["test_models.py", "test_services.py", "test_api.py"]
            for tf in expected_tests:
                if not os.path.exists(os.path.join(tests_dir, tf)):
                    warnings.append(f"[{app_name}] Missing test file: tests/{tf}")

        return errors, warnings
