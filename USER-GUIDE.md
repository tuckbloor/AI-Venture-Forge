# AI Venture Forge — Installation & User Guide

**Version:** v0.7  
**Platform:** Windows 10/11 · Python · Streamlit · Ollama · SQLite  
**Repository:** https://github.com/tuckbloor/AI-Venture-Forge

## 1. What this system does

AI Venture Forge is an experimental local multi-agent system for discovering and planning online businesses. The team researches opportunities, compares ideas, develops a product concept, creates a written website-design brief, and provides a development plan for the owner. It does not sell products or make money automatically.

The 10 roles are:

| Agent | Job role | Typical output |
|---|---|---|
| CEO | Leads the team and selects a business direction | Chosen idea and action plan |
| Market Researcher | Studies demand and competitors | Opportunity research |
| Data Analyst | Evaluates the evidence and numbers | Opportunity scoring |
| Marketing Director | Plans customer acquisition | Marketing strategy |
| Finance Director | Models business economics | Costs and financial forecasts |
| Product Strategist | Shapes the offer and MVP | Product requirements |
| Operations Manager | Plans fulfilment and operations | Operational procedures |
| Risk & Compliance Officer | Reviews business risks | Risk register and cautions |
| Website Designer | Defines pages, UX and visual approach | Written web design brief |
| Project Manager | Organises implementation | Website development instructions |

**Note:** Agents in the founder workflow generally run **one after another** to pass findings forward. Queued means waiting for a preceding agent, not necessarily malfunctioning.

## 2. Software prerequisites

1. Install **Python 3.11 or later** from https://www.python.org/downloads/ — enable `Add Python to PATH` if offered.
2. Install **Ollama** from https://ollama.com/download/windows.
3. Open PowerShell and verify:

   ```powershell
   python --version
   ollama --version
   ```

4. Download the model used by the included examples:

   ```powershell
   ollama pull llama3.2:3b
   ollama list
   ```

   If a different model is selected in Agent Builder, download that model too. Model speed depends on your computer; CPU-only inference can be slow.

## 3. Extract and install

Extract the full release ZIP into `E:\`. The folder structure must look like:

```text
E:\04-agentforge\
  app.py
  forge.py
  worker.py
  worker_silent.py
  START-BUSINESS.bat
  ensure-env.bat
  requirements.txt
  README.md
  USER-GUIDE.md
  LICENSE
  .gitignore
  images\
    Screenshot 2026-10-31 220148.png
    Screenshot 2026-10-31 220159.png
    Screenshot 2026-10-31 220218.png
    Screenshot 2026-10-31 220433.png
```

The GitHub documentation bundle contains only the documentation and screenshots. If you need the application itself, use the **full application release ZIP** or a repository checkout that contains the source code.

Run:

```powershell
cd E:\04-agentforge
.\START-BUSINESS.bat
```

On first launch, `ensure-env.bat` creates `.venv` and installs requirements. After startup, the dashboard should be at:

**http://127.0.0.1:8501**

If the port is occupied, close the older instance before launching again. Read `data\worker.log` when the worker fails.

## 4. Using the dashboard

### Business Dashboard

Your main control centre. Start the founder workflow if needed, pause or resume schedules, use emergency stop and answer questions the AI team asks about information, funding or website-building work. A funding question **does not** authorise or perform a payment.

### Team & Deadlines

Shows the agent name, job role, active or queued assignment, estimated deadline and available result. The page refreshes automatically about every three seconds. The activity feed records real worker events. Completed text appears when the corresponding agent's task finishes; it is **not** token-by-token Ollama streaming.

### Agent Builder

Create additional agents beyond the default ten, edit instructions and select a locally available Ollama model. Agent names and job roles are mandatory. Assign tools only where relevant and avoid granting sensitive access to untrusted prompts.

### Workflows

Review the **Autonomous Online Business Founder** workflow and its schedule. A typical run passes research findings to specialists, then asks the CEO to prepare the final business recommendation. Repeated runs may take previous reports into account.

### Run & Approvals

Start a cycle manually and review approval-related controls. Routine research/planning does not require approval in the automated founder workflow.

### History

Read prior results and troubleshooting details. An AI-generated plan is not proof that a business is launched or profitable.

### Worker & Schedules

Review worker status and schedule execution. A running dashboard alone is not enough — the separate worker and Ollama must also run.

## 5. What happens after starting the business workflow?

1. Specialist agents research possible UK online businesses.
2. Analysts and finance agents evaluate ideas and assumptions.
3. The CEO selects a candidate business concept.
4. The Website Designer writes a site structure and branding brief.
5. The Project Manager supplies implementation instructions and asks the owner to develop the website.
6. The owner reviews questions, including possible future advertising budgets.
7. Scheduled runs revisit and refine the plan.

Outputs are not guaranteed to be accurate. Check sources and feasibility before acting on them.

## 6. Running continuously

The background worker handles scheduled research and planning. To keep it running:

- Leave the Windows machine powered on and prevent it from sleeping.
- Keep Ollama running.
- Keep only one business worker active to avoid duplicated jobs.
- Check worker logs and execution history for failures.

A Windows desktop is not equivalent to a production 24/7 server. If Windows shuts down, sleeps or crashes, work stops. There is no automatic advertising, fulfilment, sales or customer support integration in v0.7.

## 7. Troubleshooting

**The dashboard doesn't open** — Check `http://127.0.0.1:8501`, ensure Streamlit was installed, check that another process isn't using port 8501, and rerun `START-BUSINESS.bat` once after stopping previous processes.

**The agents stay queued** — They may be waiting for earlier agents. Look for an active running agent in Team & Deadlines, check the worker status and inspect `data\worker.log` for errors.

**Ollama connection or model error** — Test `ollama list`; download the model referenced in the agent configuration, and ensure Ollama is running.

**Windows says a file is open** — Close the launcher/dashboard and stop the project's Python worker processes before copying new files. Avoid terminating unrelated Python projects.

**The page is slow** — CPU-only local inference can take time, particularly for ten sequential agent calls.

**Images don't show on GitHub** — Confirm `images/` is in the repository root, that the four PNG files are committed, and that the README uses the exact case-sensitive names shown above.

## 8. Updating without losing your data

1. Stop the application and worker.
2. Back up `E:\04-agentforge\data\` to a safe location **outside the repository**.
3. Replace application code and documentation with the new release.
4. Preserve your database and settings in `data/`.
5. Start `START-BUSINESS.bat`, then check Business Dashboard, Team & Deadlines and History.

The `.gitignore` intentionally excludes `data/` to prevent uploading local histories or credentials. This also means deleting your working folder can remove database history unless you have a backup.

## 9. Publishing the project to GitHub

Create an empty repository named **AI-Venture-Forge** under `tuckbloor`, if it does not already exist.

From PowerShell:

```powershell
cd E:\04-agentforge

git init
git branch -M main
git add .
git status
```

Carefully inspect the staged files; never upload `data/`, `.env`, keys or other private information. Then:

```powershell
git commit -m "Document AI Venture Forge v0.7"
git remote add origin https://github.com/tuckbloor/AI-Venture-Forge.git
git push -u origin main
```

If `origin` already exists, use:

```powershell
git remote set-url origin https://github.com/tuckbloor/AI-Venture-Forge.git
git push -u origin main
```

If the repository already has commits, do not force-push or overwrite others' work. Pull/reconcile any diverged history before pushing.

## 10. Security and licensing

This Streamlit interface has no production-grade user authentication or network hardening. Run on `127.0.0.1` only and do not expose it as-is to the internet. Verify generated market data and seek appropriate professional guidance for consequential financial or legal decisions.

The project is offered under the MIT License. See [LICENSE](LICENSE) for the complete terms.
