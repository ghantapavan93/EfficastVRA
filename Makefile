# Verified Recovery Agent — task runner (macOS / Linux / Git-Bash).
# Windows PowerShell users: use ./run.ps1 <command> instead.

PY := backend/.venv/bin/python
# Fall back to the Windows venv layout if the POSIX one is absent (Git-Bash on Windows).
ifeq ($(wildcard $(PY)),)
PY := backend/.venv/Scripts/python.exe
endif

.PHONY: install dev backend frontend seed reset demo eval test help
.DEFAULT_GOAL := help

help:
	@echo "make install   - install backend (editable+dev) and frontend deps"
	@echo "make dev        - run backend (:8000) in background + frontend (:3000, hot-reload)"
	@echo "make backend    - run only the backend (hot-reload)"
	@echo "make frontend   - run only the frontend (hot-reload)"
	@echo "make seed|reset|demo|eval - database / scenario commands"
	@echo "make test       - backend (pytest) + frontend (vitest)"

install:
	cd backend && $(PY) -m pip install -e ".[dev]"
	cd frontend && npm install

backend:
	cd backend && $(PY) -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

frontend:
	cd frontend && npm run dev

# Backend in the background, frontend in the foreground (one command, both hot-reload).
dev:
	cd backend && $(PY) -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 & \
	  cd frontend && npm run dev

seed:
	cd backend && $(PY) -m app.cli seed
reset:
	cd backend && $(PY) -m app.cli reset
demo:
	cd backend && $(PY) -m app.cli demo
eval:
	cd backend && $(PY) -m app.cli eval

test:
	cd backend && $(PY) -m pytest
	cd frontend && npm test
