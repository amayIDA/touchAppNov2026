"""Dependency-checking admin launcher, sharing the exhibit runtime."""
from touchscreen_launcher import main

if __name__ == '__main__':
    raise SystemExit(main(admin=True))
