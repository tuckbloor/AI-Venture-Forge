# AI Venture Forge · v0.8.0-rc2

**Self-hosted AI business research and planning with a configurable team of Ollama-powered agents, built on AI App Server.**

AI Venture Forge helps you research business ideas, coordinate specialist agents, build practical business plans and track ongoing work in a local dashboard. It is a *planning and research prototype*, not a system that independently registers businesses, deploys websites, buys products, sends emails, spends money or guarantees income.

**Release status:** v0.8.0-rc2 is a UI and installer release candidate. The application logic and source-level installer paths have automated checks; the full graphical Windows installation needs confirmation on a real Windows machine before a stable release.

## Installation requirements

- **Windows 10/11** and **Python 3.11 or newer** (the `py` launcher or `python` must work from a command prompt).
- **AI App Server v1.0.4 or v1.0.5** is **required**. The Forge installer checks for it and can install bundled **AI App Server v1.0.5** if it is not already installed. You do **not** need to download or run another installer beforehand.
- Internet access for Python package installation on first setup.
- [Ollama](https://ollama.com/) installed and running locally, with at least one model available. For example: `ollama pull llama3.2:3b`.
- Sufficient RAM/CPU/GPU resources for the model you choose. The business research tools optionally need internet access.

**Each installed application remains independent.** Even if you already have AI App Server in `C:\Users\<you>\AppData\Local\Programs\AI-App-Server`, Forge gets its **own** Python environment, administration, accounts, SQLite database, worker and port. The existing server is checked **read-only**, not altered. No `E:` drive is necessary.

## What changed in rc2

- A Venture Forge-branded dashboard replaces the generic framework title and navigation.
- Overview statistics now display in a responsive four-column grid instead of a tall vertical list.
- The business research panel shows when a run is queued, running, or awaiting approval and does not offer a redundant Start button for an active workflow.
- Worker health, owner questions and recent activity have dedicated panels, with Overview/Live team refreshing every 15 seconds while not editing a form.
- Installer remains the same two-stage wizard with only `INSTALL.bat` and `START.bat`. Existing Forge data is preserved by the installer update process.

## 1. Download and extract

1. Download the full project ZIP from [GitHub](https://github.com/tuckbloor/AI-Venture-Forge) or its Releases page.
2. Extract the **entire ZIP** to any source directory, for example `Downloads\AI-Venture-Forge` or `E:\AI-Venture-Forge`. Don't extract it inside a currently running Forge installation.
3. Check the extracted folder contains **`INSTALL.bat`**, **`START.bat`**, `framework/`, `app/`, `tools/`, `forge.py` and `worker.py`.
4. Double-click **`INSTALL.bat` in the extracted source folder**.

The source project has only **two Windows BAT files**: `INSTALL.bat` and `START.bat`. There are no extra setup, update, worker or test BAT files to choose between.

## 2. Installer wizard — AI App Server first

The installer opens a **persistent window**. It does not intentionally close when a folder picker closes, and its log remains visible if installation fails.

**Step A: AI App Server prerequisite**

- **Use an existing AI App Server (read-only)** — choose the folder where your compatible AI App Server is **installed**, not merely a downloaded source directory. The installer verifies its engine version, application and Python environment, and doesn't change its database or settings.
- **Install AI App Server first** — if no compatible installation is present, select this option and choose a **new empty destination directory**. The installer copies the bundled v1.0.5 framework, creates its isolated `.venv`, installs dependencies and initializes its application. It will not overwrite an unrelated or existing server folder.

**Step B: Forge destination**

Choose where **AI Venture Forge** itself should be installed. Typical default:

```text
%LOCALAPPDATA%\Programs\AI-Venture-Forge
```

You can choose `C:`, `D:`, `E:` or any other user-writable destination. The Forge directory must be separate from the AI App Server directory, and neither may be placed inside the other. You don't need administrator privileges for a user-writable location.

**Step C: Install / Update**

Click **Install / Update**. Watch the progress log in the installer window. The installer creates Forge's own Python environment and AI App Server engine, installs requirements, and configures the local app. Tick **Start Forge now and enable automatic startup at Windows sign-in** only if you want it to start each time you sign in.

If you select an **existing recognised Forge installation**, the installer will ask:

> An existing AI Venture Forge installation was found. Do you want to overwrite its application files with this version?

- **Yes:** Back up the previous managed application code and update it. Preserve `data/`, `config/`, `.venv/`, custom files under `app/` and existing SQLite data. Older v0.7 Streamlit layouts can be migrated after explicit confirmation.
- **No:** Cancel and keep the current project unchanged.
- **Unrelated non-empty folder:** Refuse to overwrite it.

**Important:** Stop a previously running Forge worker/dashboard before updating a live installation. Back up your data separately before major upgrades. The installer never deliberately deletes private databases, but no software update is risk-free.

## 3. Start, stop and open the application

**Use `START.bat` in the installed Forge directory**, not the `START.bat` in the downloaded source folder. If your installer destination was the default, open it by pressing **Win + R**, entering:

```text
%LOCALAPPDATA%\Programs\AI-Venture-Forge
```

Double-click **`START.bat`**. It starts the isolated AI App Server dashboard and the background Forge scheduling worker. The browser normally opens automatically.

If your main AI App Server already uses port **8501**, Forge typically chooses the next available port (for example **8502**) the **first** time it starts. The chosen port is saved; it does not jump randomly between ports on subsequent starts. The address is displayed by the launcher. The Forge administration page is at `/admin` on **Forge's port**, not on the separate existing server's port.

From PowerShell in the installed directory:

```powershell
.\START.bat                   # Start Forge and open browser
.\START.bat --status          # Report server/worker status
.\START.bat --stop            # Stop this Forge instance and its worker
.\START.bat --disable-autostart  # Disable sign-in startup
```

Leave Ollama running while processing agent workflows. The worker can perform scheduled work only when your computer, AI App Server instance and Forge worker are running.

## 4. Desktop shortcut and Windows sign-in

To make a shortcut: open the **installed Forge folder**, right-click `START.bat`, choose **Send to → Desktop (create shortcut)** and rename it **AI Venture Forge**.

For sign-in startup, choose the option in the installer. This uses the existing AI App Server sign-in launcher, which invokes Forge's `START.bat --background`. For a manual alternative, press **Win + R**, type `shell:startup`, then place a shortcut to the installed `START.bat` in that folder. Use one startup method, not both, to avoid duplicate attempts.

**Sign-in startup is not the same as a Windows Service.** A real before-login Windows Service requires administrator-controlled service setup and separate testing. This release does not silently register one.

## 5. First login and using Forge

Open Forge's local dashboard URL. The AI App Server **administrator interface** is available at the same host and port with `/admin`; configure an administrator account/password according to the prompts there. Forge's database and administration are distinct from other AI App Server installations. Do not expose Forge publicly without proper authentication, TLS reverse proxy and a security review.

The dashboard includes:

| Section | What you can do |
|---|---|
| **Overview** | Start the business-research team, view summary metrics, pause/resume the schedule and answer owner questions |
| **Live team** | Refresh actual agent assignments, estimated deadlines, progress, outputs and worker events |
| **Agents** | Create and edit specialist agents, choose available Ollama models, set instructions and allowed read-only tools |
| **Workflows** | Build ordered multi-agent workflows, choose scheduled intervals and optionally require approval |
| **Approvals** | Approve or reject jobs requiring owner consent |
| **History** | Inspect previous runs, agent outputs, errors and events |
| **Worker** | Check the worker heartbeat and request emergency cancellation |

The first setup seeds ten specialist roles: CEO, Market Researcher, Data Analyst, Marketing Director, Finance Director, Product Strategist, Operations Manager, Risk & Compliance Officer, Website Designer and Project Manager. You can also add custom agents and workflows.

### Start your first business research

1. Start Ollama. Open Command Prompt and run `ollama list` to see your models; install one with `ollama pull llama3.2:3b` if needed.
2. Start Forge. Go to **Overview → Start business research**.
3. The run is queued for Forge's separate worker. Go to **Live team** and press **Refresh team progress** to see the latest recorded assignments and outputs.
4. Review **Overview** for owner questions and answer them. Visit **History** for finished reports and individual agent results.
5. Use **Agents** and **Workflows** to create your own teams and run recurring tasks.

Agents currently process sequentially when a workflow depends on prior outputs. Queued jobs may wait for the current model or workflow. Refresh reports actual database records; it does not display fabricated progress or hidden model reasoning.

### Capabilities and limits

Research tools include Wikipedia previews, Google News RSS leads, UTC time and a restricted arithmetic calculator. Research results are leads to verify, not guaranteed facts. No shell access, purchasing, publishing, bank integration or unapproved transactions are supplied to agents.

## 6. Data, upgrades and backups

Files inside your **installed Forge folder** include:

```text
AI-Venture-Forge/
  START.bat                  Windows launcher
  app/app.py                 AI App Server UI
  forge.py                   Agent and workflow logic
  worker.py                  Scheduler worker
  engine/                    Independent AI App Server framework copy
  .venv/                     Independent installed dependencies
  data/                      SQLite database, worker state and logs (private)
  config/                    Per-instance settings (private)
  backups/                   Previous managed code after an update
```

The downloaded GitHub **source project** includes `INSTALL.bat`, `START.bat`, and the bundled `framework/` prerequisite; it excludes local runtime databases and virtual environments. Keep your private data off GitHub.

For an update, download a new full ZIP to a **new source folder**, run its **`INSTALL.bat`**, choose the existing installed Forge directory, answer Yes when prompted and verify the backup and startup. Do not delete a running installation to make room for an update.

## 7. Troubleshooting

**Installer closes / no progress:** Use the `INSTALL.bat` from the complete extracted project and check the persistent installer log. It also writes a user-local `AI-Venture-Forge/installer.log` beneath `%LOCALAPPDATA%` when available. If Windows blocks the graphical UI, run `INSTALL.bat` in a PowerShell window to read the error.

**AI App Server not found:** Browse to the real *installed* server directory containing `engine/`, `app/app.py` and `.venv/`. Alternatively choose **Install AI App Server first** and an empty destination.

**Forge installation folder is not empty:** The installer must recognise it as AI Venture Forge before it can offer an update. It never offers to overwrite unrelated files.

**START.bat says not installed:** Run `START.bat` from the directory chosen during installation, not the downloaded source folder. Confirm `.venv\Scripts\python.exe` exists there.

**No Ollama models:** Start Ollama and run `ollama list`. Install a model, then reopen or refresh Forge.

**No progress / queued work:** Check **Worker** in the UI and `data/logs/forge-worker.log`. Use `START.bat --status`. Stop an old process before running the launcher again. One worker per Forge instance is enforced.

**Port already used:** On initial run, AI App Server picks a free local port. For an existing installation, it retains the saved port rather than taking over another application's port. Use the administration service settings or stop the conflicting process.

## 8. Developers and tests

From the extracted source directory, with Python dependencies installed:

```powershell
python -m pip install -r requirements-dev.txt
python -m pip install -e .\framework\engine
python -m pytest -q tests
```

The bundled framework is AI App Server v1.0.5. The Forge agent engine (`forge.py`) and scheduler (`worker.py`) remain separate Python modules. Tests cover core agent functions, UI rendering, source packaging, installation path selection, existing-server detection, protected upgrades and the legacy v0.7 migration path. Tests run offline where possible; Windows GUI and dependency installation still need testing on a genuine Windows host.

The screenshots in `images/` show the **original v0.7 Streamlit interface**. They are retained for project history and must not be mistaken for screenshots of the new v0.8 AI App Server dashboard.

## Security and license

- Localhost binding by default; public production exposure is **not** validated.
- Never commit `data/`, `config/`, `.venv/`, API credentials or private reports.
- The included agent tools are read-only, but their results and AI-generated reports can be inaccurate; always verify important claims.
- Each instance has its own users, data, logs, port and maintenance controls; no shared admin dashboard.

**MIT License** — see [LICENSE](LICENSE). © 2026 tuckbloor.
