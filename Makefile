.PHONY: setup run-ui run-factory demo clean help

setup: ## Install dependencies and initialize environment
	@bash setup.sh

run-ui: ## Launch the Ant-Safe Swarm Gradio UI
	@python ant_safe_swarm.py --ui

run-factory: ## Launch the Streamlit Project Factory
	@streamlit run Main.py

demo: ## Run the offline mock demo to see the logic in action
	@python demo_swarm_mock.py

build: ## Build a new AI project (Usage: make build PROMPT="your prompt" [DIR="out"])
	@python ant_safe_swarm.py "$(PROMPT)" --dir $(or $(DIR),output)

clean: ## Remove temporary files, pycache, and logs
	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@rm -f *.log gradio_report.md swarm_report.md
	@echo "✨ Project cleaned."

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
