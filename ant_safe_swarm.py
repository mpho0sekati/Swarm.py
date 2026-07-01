import os
import sys
import json
import sqlite3
import time
import random
from datetime import datetime
from typing import List, Dict, Any, Optional
from groq import Groq
from crewai import Agent, Task, Crew, Process, LLM

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
                f.write("# 🧠 Swarm Brain: Long-Term Memory\n\nTask history and successful patterns.\n\n")

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
        # Roles and their backstory
        roles_config = {
            "Architect": {
                "goal": "Design system structure and data flow.",
                "backstory": "A visionary system designer who ensures scalability and modularity."
            },
            "Coder": {
                "goal": "Write high-quality, efficient Python code.",
                "backstory": "A pragmatic developer who focuses on clean, PEP-8 compliant code."
            },
            "Safety Officer": {
                "goal": "Audit outputs for AI safety, PII, and ethics compliance.",
                "backstory": "An ethics specialist who prevents harmful content and security leaks."
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
                verbose=True,
                allow_delegation=False
            )
        return agents

    def solve(self, prompt: str, report_file: str = "swarm_report.md"):
        print(f"--- Processing Prompt with CrewAI: {prompt} ---")
        task_type = "coding_task"

        def task_callback(output):
            print(f"📌 Task completed by {output.agent}. Updating pheromones...")
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
            print("🚀 High Pheromone detected: Enabling Hierarchical Process with Manager.")
            process_mode = Process.hierarchical

        # Define Tasks
        design_task = Task(
            description=f"Design the architecture for: {prompt}",
            expected_output="A structured architectural design document.",
            agent=all_agents["Architect"],
            callback=task_callback
        )

        coding_task = Task(
            description=f"Implement the design for: {prompt}",
            expected_output="Complete, working Python code.",
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

        # Create Crew with Dynamic Process
        crew = Crew(
            agents=[all_agents["Architect"], all_agents["Coder"], all_agents["Safety Officer"]],
            tasks=[design_task, coding_task, safety_task],
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
            print(f"\n📄 Report saved to: {report_file}")

        except Exception as e:
            print(f"CrewAI execution failed: {e}")

        self.memory.evaporate()

    def _write_report(self, filepath: str, prompt: str, results: str):
        content = f"# CrewAI Swarm Report\n\nGenerated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        content += f"## Prompt\n> {prompt}\n\n"
        content += f"## Outcome\n{results}\n"
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

if __name__ == "__main__":
    key = os.environ.get("GROQ_API_KEY", "your_api_key_here")
    swarm = AntSafeCrew(key)

    user_prompt = sys.argv[1] if len(sys.argv) > 1 else "Build a simple URL shortener API."
    swarm.solve(user_prompt)
