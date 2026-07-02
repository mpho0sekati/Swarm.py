import os
import sys
import io
import json
import sqlite3
import time
import random
import gradio as gr
from datetime import datetime
from typing import List, Dict, Any, Optional
from unittest.mock import patch
from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools import FileReadTool, FileWriterTool, DirectoryReadTool

# ─────────────────────────────────────────────────────────────────────────────
# PERSISTENCE LAYER (BRAIN & PHEROMONES)
# ─────────────────────────────────────────────────────────────────────────────

class PheromoneMemory:
    """Tracks and decays pheromone levels for different agent roles and task types with SQLite persistence."""
    def __init__(self, db_path: str = "pheromones.db", evaporation_rate: float = 0.1):
        self.db_path = db_path
        self.evaporation_rate = evaporation_rate
        self.memory: Dict[str, Dict[str, float]] = {}
        self._init_db()
        self._load_memory()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pheromones (
                    task_type TEXT,
                    role TEXT,
                    level REAL,
                    PRIMARY KEY (task_type, role)
                )
            """)

    def _load_memory(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT task_type, role, level FROM pheromones")
            for row in cursor:
                task_type, role, level = row
                if task_type not in self.memory:
                    self.memory[task_type] = {}
                self.memory[task_type][role] = level

    def _save_role(self, task_type: str, role: str, level: float):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO pheromones (task_type, role, level)
                VALUES (?, ?, ?)
                ON CONFLICT(task_type, role) DO UPDATE SET level=excluded.level
            """, (task_type, role, level))

    def get_pheromone(self, task_type: str, role: str) -> float:
        return self.memory.get(task_type, {}).get(role, 1.0)

    def deposit_pheromone(self, task_type: str, role: str, amount: float):
        if task_type not in self.memory:
            self.memory[task_type] = {}
        current = self.memory[task_type].get(role, 1.0)
        new_level = current + amount
        self.memory[task_type][role] = new_level
        self._save_role(task_type, role, new_level)

    def evaporate(self):
        for task_type in self.memory:
            for role in self.memory[task_type]:
                self.memory[task_type][role] *= (1 - self.evaporation_rate)
                if self.memory[task_type][role] < 0.1:
                    self.memory[task_type][role] = 0.1
                self._save_role(task_type, role, self.memory[task_type][role])

class SwarmBrain:
    """Long-term task memory that persists successful task outcomes in a Markdown file."""
    def __init__(self, filepath: str = "swarm_brain.md"):
        self.filepath = filepath
        if not os.path.exists(self.filepath):
            with open(self.filepath, "w") as f:
                f.write("# Swarm Brain: Long-Term Memory\n\nTask history and successful patterns.\n\n")

    def record_success(self, prompt: str, results: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"## [{timestamp}] Task: {prompt}\n"
        entry += "**Outcome:** Successful CrewAI execution.\n\n"
        entry += f"### Summary\n{results[:1000]}...\n"
        entry += "\n---\n\n"

        with open(self.filepath, "a", encoding="utf-8") as f:
            f.write(entry)

# ─────────────────────────────────────────────────────────────────────────────
# CREWAI AGENT & TASK DEFINITIONS
# ─────────────────────────────────────────────────────────────────────────────

class AntSafeCrew:
    """Orchestrates ant agents using CrewAI, ACO, and Safety features."""

    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile"):
        self.llm = LLM(model=f"groq/{model}", api_key=api_key, temperature=0.7)
        self.memory = PheromoneMemory()
        self.brain = SwarmBrain()

    def _create_agents(self, task_type: str) -> Dict[str, Agent]:
        # Initialize Tools
        file_read = FileReadTool()
        file_write = FileWriterTool()
        dir_read = DirectoryReadTool()

        # Roles and their backstory
        roles_config = {
            "Architect": {
                "goal": "Design system structure and data flow. Research existing files if needed.",
                "backstory": "A visionary system designer who ensures scalability and modularity. You can read the current codebase to understand the context.",
                "tools": [file_read, dir_read]
            },
            "Coder": {
                "goal": "Write high-quality, efficient Python code and save it to files.",
                "backstory": "A pragmatic developer who focuses on clean, PEP-8 compliant code. You have the ability to write files directly.",
                "tools": [file_write, file_read]
            },
            "Safety Officer": {
                "goal": "Audit outputs and files for AI safety, PII, and ethics compliance.",
                "backstory": "An ethics specialist who prevents harmful content and security leaks. You audit both text outputs and generated files.",
                "tools": [file_read]
            },
            "Strategist": {
                "goal": "Perform deep reasoning and chain-of-thought analysis on the user prompt.",
                "backstory": "A strategic thinker who breaks down complex instructions into actionable steps and identifies potential pitfalls before execution.",
                "tools": [dir_read]
            },
            "AI Specialist": {
                "goal": "Design AI-specific components including model selection, prompt templates, and data pipelines.",
                "backstory": "An AI R&D expert who stays current with the latest LLM patterns, RAG techniques, and agentic workflows.",
                "tools": [file_read]
            }
        }

        agents = {}
        for role, cfg in roles_config.items():
            # Adjust behavior based on pheromones (simulated by adding to backstory)
            pheromone = self.memory.get_pheromone(task_type, role)
            backstory = cfg["backstory"]
            if pheromone > 2.0:
                backstory += f" You are currently in a high-confidence state (Pheromone: {pheromone:.1f})."

            agents[role] = Agent(
                role=role,
                goal=cfg["goal"],
                backstory=backstory,
                llm=self.llm,
                tools=cfg.get("tools", []),
                verbose=True,
                allow_delegation=False
            )
        return agents

    def solve(self, prompt: str, report_file: str = "swarm_report.md", output_dir: Optional[str] = None):
        print(f"--- Processing Prompt with CrewAI: {prompt} ---")

        # Heuristic to detect AI-building tasks
        is_ai_task = any(kw in prompt.lower() for kw in ["ai", "llm", "rag", "agent", "model"])
        task_type = "ai_development" if is_ai_task else "coding_task"

        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            print(f"Output directory set to: {output_dir}")

        def task_callback(output):
            print(f"[Task] completed by {output.agent}. Updating pheromones...")
            role = output.agent.split('(')[0].strip() # Heuristic to get role
            self.memory.deposit_pheromone(task_type, role, 0.2)

        # Dynamic Orchestration: Select Agents based on Pheromone Levels
        # If pheromones are very low for a role, we might use a different "expert" or model
        all_agents = self._create_agents(task_type)

        # In a real ACO, we might select a subset of agents or change the process
        # Here we dynamically adjust the process and delegation based on the Architect's pheromone
        commander_pheromone = self.memory.get_pheromone(task_type, "Architect")

        process_mode = Process.sequential
        if commander_pheromone > 5.0:
            print("High Pheromone detected: Enabling Hierarchical Process with Manager.")
            process_mode = Process.hierarchical

        # Define Tasks
        reasoning_task = Task(
            description=f"Perform a detailed chain-of-thought analysis and breakdown for the following prompt: {prompt}. Identify technical requirements and constraints.",
            expected_output="A comprehensive strategy document with actionable steps.",
            agent=all_agents["Strategist"],
            callback=task_callback
        )

        # AI specific task if needed
        ai_task = None
        if is_ai_task:
            ai_task = Task(
                description=f"Research and design the AI-specific components for: {prompt}. Focus on model choice and prompting.",
                expected_output="AI Implementation strategy and prompt templates.",
                agent=all_agents["AI Specialist"],
                context=[reasoning_task],
                callback=task_callback
            )

        design_task = Task(
            description=f"Design the architecture based on the strategist's breakdown for: {prompt}",
            expected_output="A structured architectural design document.",
            agent=all_agents["Architect"],
            context=[reasoning_task, ai_task] if ai_task else [reasoning_task],
            callback=task_callback
        )

        coding_task = Task(
            description=(
                f"Implement the design for: {prompt}. "
                f"SAVE all code files into the directory: {output_dir if output_dir else './output'}."
            ),
            expected_output="Complete, working Python code saved to the output directory.",
            agent=all_agents["Coder"],
            context=[design_task],
            callback=task_callback
        )

        safety_task = Task(
            description="Audit the generated design and code for safety violations, PII, or harmful content.",
            expected_output="A safety audit report. If unsafe, provide reasons.",
            agent=all_agents["Safety Officer"],
            context=[design_task, coding_task],
            callback=task_callback
        )

        # Agents and Tasks for the Crew
        agents_list = [all_agents["Strategist"], all_agents["Architect"], all_agents["Coder"], all_agents["Safety Officer"]]
        tasks_list = [reasoning_task, design_task, coding_task, safety_task]

        if ai_task:
            agents_list.insert(1, all_agents["AI Specialist"])
            tasks_list.insert(1, ai_task)

        # Create Crew with Dynamic Process
        crew = Crew(
            agents=agents_list,
            tasks=tasks_list,
            process=process_mode,
            manager_llm=self.llm if process_mode == Process.hierarchical else None,
            verbose=True
        )

        try:
            result = crew.kickoff()
            result_text = str(result)

            # Record Success
            self.brain.record_success(prompt, result_text)
            self.memory.deposit_pheromone(task_type, "Architect", 0.5)
            self.memory.deposit_pheromone(task_type, "Coder", 0.5)
            self.memory.deposit_pheromone(task_type, "Safety Officer", 0.5)

            self._write_report(report_file, prompt, result_text)
            print(f"\nReport saved to: {report_file}")

        except Exception as e:
            print(f"CrewAI execution failed: {e}")

        self.memory.evaporate()

    def _write_report(self, filepath: str, prompt: str, results: str):
        content = f"# CrewAI Swarm Report\n\nGenerated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        content += f"## Configuration\n"
        content += f"- **Model:** {self.llm.model}\n"
        content += f"- **Evaporation Rate:** {self.memory.evaporation_rate}\n\n"
        content += f"## Prompt\n> {prompt}\n\n"
        content += f"## Outcome\n{results}\n"
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

def launch_gradio():
    GROQ_MODELS = [
        "llama-3.3-70b-versatile",
        "llama-3.1-70b-versatile",
        "llama3-70b-8192",
        "llama3-8b-8192",
        "mixtral-8x7b-32768",
        "gemma2-9b-it"
    ]

    key = os.environ.get("GROQ_API_KEY", "")

    def run_swarm(prompt, model):
        if not os.environ.get("GROQ_API_KEY"):
            return "### Error\nGroq API Key not found. Please set the `GROQ_API_KEY` environment variable before launching.", "API Key Missing", ""

        swarm = AntSafeCrew(os.environ.get("GROQ_API_KEY"), model=model)

        # Redirect stdout to capture CrewAI logs
        f = io.StringIO()
        with patch('sys.stdout', f):
            swarm.solve(prompt, report_file="gradio_report.md")

        logs = f.getvalue()

        with open("gradio_report.md", "r") as r:
            report = r.read()

        with open("swarm_brain.md", "r") as b:
            brain = b.read()

        return report, logs, brain

    with gr.Blocks(title="Ant-Safe Swarm UI", theme=gr.themes.Soft()) as demo:
        gr.Markdown("# Ant-Safe Swarm Intelligence")
        gr.Markdown("### ACO-inspired multi-agent orchestration with CrewAI and AI Safety Guardrails.")

        with gr.Row():
            with gr.Column(scale=2):
                prompt = gr.Textbox(label="Swarm Instructions", placeholder="e.g., Build a FastAPI app with JWT...", lines=5)
                with gr.Row():
                    model_dropdown = gr.Dropdown(
                        choices=GROQ_MODELS,
                        value="llama-3.3-70b-versatile",
                        label="Select Groq Model",
                        info="Llama-3.3-70b is recommended for complex reasoning."
                    )
                launch_btn = gr.Button("Launch Swarm", variant="primary")
            with gr.Column(scale=1):
                gr.Markdown("### Swarm Status")
                status_box = gr.Label(value="Ready", label="Current State")
                with gr.Accordion("Model Details", open=False):
                    gr.Markdown("""
                    - **Llama 3.3 70B:** State-of-the-art reasoning.
                    - **Llama 3.1 70B:** Reliable balanced model.
                    - **Mixtral 8x7b:** High context window.
                    - **Gemma 2 9b:** Fast and efficient.
                    """)
                gr.Info("Short-term (SQLite) and Long-term (Markdown) memory active.")

        with gr.Tabs():
            with gr.TabItem("Execution Report"):
                report_out = gr.Markdown(label="Latest Report")
            with gr.TabItem("Live Logs"):
                gr.Markdown("### Agent Reasoning & Tool Usage")
                logs_out = gr.Code(label="CrewAI Console Output", language="markdown", lines=20)
            with gr.TabItem("Brain History"):
                brain_out = gr.Markdown(label="Memory History")

        launch_btn.click(
            fn=lambda: "Processing...",
            outputs=status_box
        ).then(
            run_swarm,
            inputs=[prompt, model_dropdown],
            outputs=[report_out, logs_out, brain_out]
        ).then(
            fn=lambda: "Task Complete",
            outputs=status_box
        )

    demo.launch(server_name="0.0.0.0", server_port=3000)

if __name__ == "__main__":
    if "--ui" in sys.argv:
        launch_gradio()
    else:
        key = os.environ.get("GROQ_API_KEY", "your_api_key_here")
        swarm = AntSafeCrew(key)

        # Parse args
        user_prompt = "Build a simple URL shortener API."
        out_dir = None

        for i, arg in enumerate(sys.argv):
            if arg == "--dir" and i + 1 < len(sys.argv):
                out_dir = sys.argv[i+1]
            elif not arg.startswith("--") and i > 0:
                user_prompt = arg

        swarm.solve(user_prompt, output_dir=out_dir)
