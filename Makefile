PYTHON ?= python
VENV_DIR ?= .venv
UVICORN_APP ?= app.main:app
TMUX_SESSION ?= nanaimo-api
FRONTEND_DIR ?= frontend

.PHONY: setup setup-backend setup-frontend run run-backend run-frontend

setup: setup-backend setup-frontend

setup-backend:
	@echo "Creating virtualenv in $(VENV_DIR) (if needed)..."
	@test -d "$(VENV_DIR)" || $(PYTHON) -m venv "$(VENV_DIR)"
	@echo "Installing backend requirements..."
	@"$(VENV_DIR)/bin/pip" install --upgrade pip
	@"$(VENV_DIR)/bin/pip" install -r requirements.txt

setup-frontend:
	@echo "Installing frontend dependencies in $(FRONTEND_DIR)..."
	@cd "$(FRONTEND_DIR)" && npm install

run:
	@echo "Starting tmux session '$(TMUX_SESSION)' with backend and frontend panes..."
	@tmux has-session -t "$(TMUX_SESSION)" 2>/dev/null && { \
		echo "Session $(TMUX_SESSION) already exists. Attaching..."; \
		tmux attach -t "$(TMUX_SESSION)"; \
	} || { \
		# Pane 0: backend (FastAPI) \
		tmux new-session -d -s "$(TMUX_SESSION)" "cd $$(pwd) && source $(VENV_DIR)/bin/activate && uvicorn $(UVICORN_APP) --host 0.0.0.0 --port 8000 --reload"; \
		# Pane 1: frontend (Vite) \
		tmux split-window -h -t "$(TMUX_SESSION):0" "cd $$(pwd)/$(FRONTEND_DIR) && npm run dev"; \
		tmux select-layout -t "$(TMUX_SESSION):0" tiled; \
		tmux attach -t "$(TMUX_SESSION)"; \
	}

run-backend:
	@echo "Starting or attaching to tmux session '$(TMUX_SESSION)' for backend..."
	@tmux has-session -t "$(TMUX_SESSION)" 2>/dev/null && { \
		tmux attach -t "$(TMUX_SESSION)"; \
	} || { \
		tmux new-session -s "$(TMUX_SESSION)" "cd $$(pwd) && source $(VENV_DIR)/bin/activate && uvicorn $(UVICORN_APP) --host 0.0.0.0 --port 8000 --reload"; \
	}

run-frontend:
	@echo "Starting frontend dev server (npm run dev) in $(FRONTEND_DIR)..."
	@cd "$(FRONTEND_DIR)" && npm run dev

