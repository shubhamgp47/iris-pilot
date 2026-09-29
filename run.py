"""
Cross-platform task runner for Project IRIS pilot.
Works on Windows, macOS, and Linux without needing 'make'.
"""
import sys
import subprocess
import time

def run(cmd: str):
    print(f"\n>> Running: {cmd}")
    res = subprocess.run(cmd, shell=True)
    if res.returncode != 0:
        print(f"Error executing command: {cmd}")
        sys.exit(res.returncode)

def main():
    if len(sys.argv) < 2:
        print("Usage: python run.py [up|down|migrate|seed|test|verify|reset]")
        sys.exit(1)

    action = sys.argv[1].lower()

    if action == "up":
        run("docker compose up -d")
    elif action == "down":
        run("docker compose down -v")
    elif action == "migrate":
        run("python -m src.migrate")
    elif action == "seed":
        run("python -m src.loader")
    elif action == "test":
        run("pytest -v tests/")
    elif action == "verify":
        run("python -m src.queries")
    elif action == "reset":
        run("docker compose down -v")
        run("docker compose up -d")
        print("Waiting for Postgres/PostGIS container...")
        time.sleep(4)
        run("python -m src.migrate")
        run("python -m src.loader")
        run("python -m src.queries")
        run("pytest -v tests/")
    elif action == "help":
        print("Available actions:")
        print("  up       - Start Docker containers")
        print("  down     - Stop and remove Docker containers")
        print("  migrate  - Run database migrations")
        print("  seed     - Load initial data into the database")
        print("  test     - Run unit tests")
        print("  verify   - Run verification queries")
        print("  reset    - Reset the environment (down, up, migrate, seed, test)")
    else:
        print(f"Unknown action: {action}")
        sys.exit(1)

if __name__ == "__main__":
    main()