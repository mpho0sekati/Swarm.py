# 🧪 Testing Guide: Ant-Safe Swarm Intelligence

Follow these instructions to verify the new Ant Colony Optimization (ACO) swarm, AI safety features, and persistent brain.

---

## 1. Quick Mock Demo (No API Key Required)
We've provided a `demo_swarm_mock.py` script that simulates the swarm's behavior. This is the fastest way to see the logic in action.

```bash
python demo_swarm_mock.py
```
**What to look for:**
- Check `pheromones.db` (SQLite) to see the learning weights.
- Check `swarm_brain.md` (Markdown) to see the task history.

---

## 2. Testing the Standalone Swarm (`ant_safe_swarm.py`)
This script requires a [Groq API Key](https://console.groq.com).

### CLI Mode
Run a prompt directly from your terminal:
```bash
export GROQ_API_KEY="your_gsk_..."
python ant_safe_swarm.py "Build a secure authentication system in Python."
```
**Verification:**
- Verify `swarm_report.md` is generated with the outcome.
- Ensure the `Safety Officer` role is mentioned in the output.

### Web UI Mode (Gradio)
Launch the interactive web interface:
```bash
python ant_safe_swarm.py --ui
```
**Verification:**
- Open `http://localhost:7860` in your browser.
- Enter a prompt and hit **Launch Swarm**.
- Watch the **Live Logs** tab for real-time CrewAI output.

---

## 3. Testing the Main Factory (`Main.py`)
Launch the primary project scaffold generator:

```bash
streamlit run Main.py
```

### Steps:
1. Add 1 or more Groq keys in the sidebar.
2. Set **Swarm Size** to **9** (this enables the Safety Officer).
3. Set **Refinement Cycles** to **2**.
4. Enter instructions and hit **Launch Swarm**.

**Verification:**
- Look for the `🛡️ Safety & Ethics Compliance Officer` icon in the execution log.
- After completion, check the generated files for `safety_audit.md`.

---

## 4. Testing Automation (GitHub Actions)
1. Push your changes to GitHub.
2. Go to the **Actions** tab.
3. Select **Swarm Automation**.
4. Click **Run workflow** and enter a custom prompt.

**Verification:**
- Once finished, download the `swarm-report` artifact from the run summary.

---

## 5. Verifying the "Brain" (Learning)
The swarm learns over time. To verify:
1. Run a coding task multiple times.
2. Observe the "Pheromone" level for the `Architect` and `Coder` roles increasing in the logs.
3. After 5+ successes, the swarm will automatically switch to **Hierarchical Process** (indicated in the console logs).
