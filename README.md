# AI Venture Forge

**AI-powered multi-agent business discovery, research and planning — running locally with Ollama, Python and Streamlit.**

[Installation & User Guide](USER-GUIDE.md) · [MIT License](LICENSE) · [GitHub Repository](https://github.com/tuckbloor/AI-Venture-Forge)

> **Current status — v0.7:** A local business research and planning prototype. The agents can analyse opportunities, propose an online business, draft website specifications and produce owner questions. They **cannot** independently build/deploy a website, buy advertising, accept orders or guarantee income. Agent work is generally sequential, not simultaneous.

## Screenshots

### Business dashboard
![Business dashboard](images/Screenshot%202026-10-31%20220148.png)

### Live team & deadlines
![Live team progress](images/Screenshot%202026-10-31%20220159.png)

### Owner controls
![Business owner controls](images/Screenshot%202026-10-31%20220218.png)

### Individual agent assignments
![Agent assignment details](images/Screenshot%202026-10-31%20220433.png)

The images above are stored in the repository's root-level `images/` directory. Keep the original file names for the links to work.

## Features

- **10 default specialist agents:** CEO, Market Researcher, Data Analyst, Marketing Director, Finance Director, Product Strategist, Operations Manager, Risk & Compliance Officer, Website Designer and Project Manager.
- **Business discovery workflow:** research and evaluate online businesses, choose a concept, develop website requirements and prepare the owner-facing plan.
- **Owner dashboard:** review business progress, funding questions and tasks that require your involvement.
- **Live monitoring:** agent name, role, assignment, estimated deadline, current status and completed work; page refreshes about every 3 seconds.
- **Workflow controls:** start, pause, resume and emergency-stop functionality.
- **Custom agent builder:** add or edit agents, model choice, instructions and supported tools.
- **Local operation:** Ollama inference, SQLite persistence, Windows launch scripts and a separate background worker.

## Requirements

- Windows 10 or 11
- Python 3.11 or later and internet access for first-time Python package installation
- [Ollama](https://ollama.com/) installed and running, with a downloaded compatible model
- Suitable RAM/CPU capacity for the Ollama model you choose
- Optional internet access for public research tools

## Quick installation (Windows)

1. Extract the complete application archive to `E:\` so the files are at `E:\04-agentforge\`.
2. Open PowerShell and pull the default example model:

   ```powershell
   ollama pull llama3.2:3b
   ```

3. Make sure Ollama is running, then start the application:

   ```powershell
   cd E:\04-agentforge
   .\START-BUSINESS.bat
   ```

4. Open **http://127.0.0.1:8501** if your browser does not open automatically.
5. Use **Business Dashboard** to control the work and **Team & Deadlines** to see progress.

The launcher creates `.venv`, installs Python dependencies, starts the background worker and launches the Streamlit web dashboard. Read [USER-GUIDE.md](USER-GUIDE.md) for troubleshooting, controls, scheduling, updating and GitHub setup.

## Dashboard sections

| Section | Purpose |
|---|---|
| Business Dashboard | Business overview, owner questions, start/pause/resume controls |
| Team & Deadlines | Auto-updating agent execution status, assignments, outputs and estimated deadlines |
| Agent Builder | Create or modify agents and their instructions |
| Workflows | Inspect and configure business workflows |
| Run & Approvals | Manually initiate a workflow, check requested actions |
| History | Review completed and failed runs and reports |
| Worker & Schedules | Check worker activity, scheduling and health |

## How autonomous is it?

The scheduler can run business research and planning workflows without your manually starting every cycle, provided the computer, worker and Ollama remain running. The AI agents don't have permission or tooling to make purchases, send marketing campaigns or deploy websites. Owner questions are shown in the dashboard and funding requests are **not** payments. AI output is advisory, and market claims should be independently checked.

## Testing

```powershell
cd E:\04-agentforge
.\run-tests.bat
```

## Privacy and security

- Keep the dashboard bound to `127.0.0.1`; it is **not hardened for public internet hosting**.
- Do not commit `data/`, API keys or local environment settings; see [.gitignore](.gitignore).
- Do not run two workers simultaneously: stop the previous application processes before restarting.
- The emergency stop requests cancellation but may not instantly interrupt an Ollama operation already running.

## License

MIT — see [LICENSE](LICENSE).

Copyright © 2026 tuckbloor.
