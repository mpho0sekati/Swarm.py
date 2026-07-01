import os
import sys
import json
import sqlite3
import time
import random
from datetime import datetime
from typing import List, Dict, Any, Optional
from groq import Groq

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

    def record_success(self, prompt: str, results: Dict[str, str]):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"## [{timestamp}] Task: {prompt}\n"
        entry += "**Outcome:** Successful execution by swarm agents.\n\n"
        for role, output in results.items():
            # Extract first 200 chars for summary
            summary = output.strip().split('\n')[0][:200]
            entry += f"- **{role}**: {summary}...\n"
        entry += "\n---\n\n"

        with open(self.filepath, "a", encoding="utf-8") as f:
            f.write(entry)

class SafetyGuard:
    """Validates inputs and outputs against AI safety standards."""
    def __init__(self, client: Groq, model: str = "llama-3.3-70b-versatile"):
        self.client = client
        self.model = model

    def validate(self, text: str, context: str = "general") -> bool:
        """Returns True if the text is safe, False otherwise."""
        system_prompt = (
            "You are an AI Safety Auditor. Your task is to analyze the provided text "
            "and determine if it violates safety policies. Violation categories: "
            "1. PII exposure, 2. Hate speech, 3. Instructions for illegal acts, "
            "4. Self-harm, 5. Harassment. "
            "Output ONLY 'SAFE' or 'UNSAFE'."
        )
        try:
            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Context: {context}\nText: {text}"}
                ],
                model=self.model,
                temperature=0,
                max_tokens=10
            )
            result = response.choices[0].message.content.strip().upper()
            return result == "SAFE"
        except Exception as e:
            print(f"Safety Check Error: {e}")
            return False  # Fail safe

class AntAgent:
    """A single 'ant' agent that acts on a prompt."""
    def __init__(self, role: str, goal: str, client: Groq, model: str):
        self.role = role
        self.goal = goal
        self.client = client
        self.model = model

    def act(self, prompt: str) -> str:
        messages = [
            {"role": "system", "content": f"You are a {self.role}. Your goal is: {self.goal}"},
            {"role": "user", "content": prompt}
        ]
        response = self.client.chat.completions.create(
            messages=messages,
            model=self.model,
            temperature=0.7
        )
        return response.choices[0].message.content

class Swarm:
    """Orchestrates ant agents using ACO and Safety features."""
    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile"):
        self.client = Groq(api_key=api_key)
        self.model = model
        self.memory = PheromoneMemory()
        self.brain = SwarmBrain()
        self.safety = SafetyGuard(self.client, model)
        self.roles = {
            "Coder": "Write high-quality, efficient Python code.",
            "Architect": "Design system structure and data flow.",
            "Tester": "Create comprehensive test cases and find bugs."
        }

    def solve(self, prompt: str, report_file: str = "swarm_report.md"):
        print(f"--- Processing Prompt: {prompt} ---")

        report_content = f"# Swarm Intelligence Report\n\nGenerated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        report_content += f"## Prompt\n> {prompt}\n\n"

        # 1. Initial Safety Check
        if not self.safety.validate(prompt, "user_input"):
            print("❌ Input blocked by Safety Guard.")
            report_content += "## Safety Status\n❌ **BLOCKED**: User input violated safety policies.\n"
            self._write_report(report_file, report_content)
            return

        report_content += "## Safety Status\n✅ **PASSED**: User input verified safe.\n\n"
        task_type = "general_coding" # Heuristic or classifier could be used here

        # 2. Path Selection (ACO)
        # Select roles based on pheromone levels
        sorted_roles = sorted(
            self.roles.keys(),
            key=lambda r: self.memory.get_pheromone(task_type, r),
            reverse=True
        )

        context = prompt
        results = {}

        for role in sorted_roles:
            print(f"🐜 Ant Agent ({role}) is exploring...")

            agent = AntAgent(role, self.roles[role], self.client, self.model)
            try:
                output = agent.act(context)

                # 3. Output Safety Check
                if self.safety.validate(output, f"agent_output_{role}"):
                    print(f"✅ {role} output passed safety check.")
                    results[role] = output
                    context += f"\n\nResults from {role}:\n{output}"

                    # Deposit Pheromone on success
                    self.memory.deposit_pheromone(task_type, role, 0.5)
                else:
                    print(f"⚠️ {role} output failed safety check. Ignoring.")
                    # Possible negative pheromone or just no deposit
            except Exception as e:
                print(f"Error with agent {role}: {e}")

        # 4. Final Aggregation
        print("\n--- Final Swarm Conclusion ---")
        report_content += "## Agent Results\n"
        if results:
            for role, output in results.items():
                report_content += f"### {role}\n{output}\n\n"

            # Record in long-term brain
            self.brain.record_success(prompt, results)

            summary = results.get("Architect", "") + "\n" + results.get("Coder", "")
            print(summary[:500] + "...")
        else:
            report_content += "_No safe agent results were generated during this run._\n"
            print("No safe results generated.")

        self._write_report(report_file, report_content)
        print(f"\n📄 Report saved to: {report_file}")

        # Evaporate pheromones for the next run
        self.memory.evaporate()

    def _write_report(self, filepath: str, content: str):
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

if __name__ == "__main__":
    # For demonstration purposes, expect an API key from env
    key = os.environ.get("GROQ_API_KEY", "your_api_key_here")
    swarm = Swarm(key)

    # Use command line argument if available, else default
    test_prompt = sys.argv[1] if len(sys.argv) > 1 else "Design and implement a simple task manager in Python."
    swarm.solve(test_prompt)
