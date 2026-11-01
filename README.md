# Shelfmark

**Shelfmark: An AI-Powered Smart E-Commerce Management System** — an online
electronics shop with a smart assistant, plus the operator back office behind it.

It has two halves that share the same data:

- **Storefront** for customers — browse and compare products, ask the AI
  assistant, search by photo or by voice, add to cart, check out, and track an
  order. Arabic-first with full English support.
- **Back office** for staff — forecast stock and reorder, adjust prices, segment
  customers, review risky orders, and read business dashboards.

Everything runs on your own computer with one command. This guide assumes you
have never used a terminal before.

<p>
  <img src="docs/presentation/assets/01-catalog.png" alt="Customer catalog, Arabic RTL" width="49%">
  <img src="docs/presentation/assets/21-analytics.png" alt="Operator analytics dashboard" width="49%">
</p>

<sub>Screens captured from the running system. All product and order data is
synthetic and labelled as such.</sub>

---

## Run it — Windows (start here)

You need two programs: **Docker Desktop**, which runs the app, and **Git**, which
downloads it. Everything else runs inside Docker.

### Step 1 — Install Docker Desktop

1. Go to <https://www.docker.com/products/docker-desktop/> and click **Download
   for Windows**.
2. Open `Docker Desktop Installer.exe`, click **Install**, and leave **"Use WSL 2
   instead of Hyper-V"** ticked.
3. Restart the computer if it asks.
4. Open **Docker Desktop** from the Start menu and wait until it says **"Engine
   running"**.

If Windows asks for a "WSL 2 kernel update", install it, then reopen Docker
Desktop.

### Step 2 — Install Git (skip if you already have it)

If you already use Git, skip this step.

1. Go to <https://git-scm.com/download/win> — the download starts on its own.
2. Open the downloaded file, click **Next** through the installer, and finish.
   The default options are fine.

### Step 3 — Download the project

1. Press the **Windows key**, type `powershell`, and press **Enter**.
2. Paste this line and press **Enter**:

```powershell
git clone https://github.com/adham-samir/shelfmark.git
```

3. Then enter the folder:

```powershell
cd shelfmark
```

The project is saved in your user folder, for example
`C:\Users\YourName\shelfmark`.

### Step 4 — Start the app

Paste this line and press **Enter**:

```powershell
docker compose -f infra/compose.yaml up --build
```

- The first run takes several minutes and downloads about 2 GB. This happens once.
- Text scrolls past quickly. That is normal.
- When you see a line containing `ready`, the app is running.
- Leave this window open while you use the app.

### Step 5 — Open the shop

Go to <http://localhost:3000>.

### Step 6 — Sign in

The demo accounts are ready to use:

| Role     | Email                      | Password          |
|----------|----------------------------|-------------------|
| Customer | `customer@example.invalid` | `demo-customer-1` |
| Operator | `operator@example.invalid` | `demo-operator-1` |

The customer signs in at **/login**; the operator back office is at
**/backoffice/login**.

### Step 7 — Stop the app

Press **Ctrl + C** in the terminal, or open a terminal in the same folder and
run:

```powershell
docker compose -f infra/compose.yaml down
```

To start again later, repeat **Step 4**. It is much faster the second time.

---

## Run it — Linux

The commands are the same as Windows: install Git and Docker, clone the project,
then start it. Only the install step differs.

### Step 1 — Install Docker

On Ubuntu/Debian, the simplest path is Docker's official convenience script:

```bash
curl -fsSL https://get.docker.com | sudo sh
```

Then let your user run Docker without `sudo` (log out and back in for it to take
effect):

```bash
sudo usermod -aG docker "$USER"
```

Check it works:

```bash
docker compose version
```

> If you would rather not use the convenience script, follow
> <https://docs.docker.com/engine/install/> for your distribution.

### Step 2 — Get the project

```bash
git clone https://github.com/adham-samir/shelfmark.git
cd shelfmark
```

### Step 3 — Start the app

```bash
docker compose -f infra/compose.yaml up --build
```

Wait for the first run to finish downloading and building (a few minutes), then
open <http://localhost:3000> and sign in with the same demo accounts as above.

### Step 4 — Stop the app

Press **Ctrl + C** in the terminal, or from another terminal:

```bash
docker compose -f infra/compose.yaml down
```

---

## Turn on the AI assistant (optional)

Everything works without this. Only the assistant and voice search show a
"provider unavailable" message.

The app uses OpenRouter with a cheap DeepSeek model, so trying it costs pennies.

### Step 1 — Get a key

1. Go to <https://openrouter.ai/keys> and create an account.
2. Add a few dollars of credit.
3. Click **Create Key** and copy the key. It starts with `sk-or-v1-`.

Keep it private, like a password.

### Step 2 — Add the key to the app

In a terminal in the `shelfmark` folder that `git clone` created:

```powershell
copy .env.example .env
notepad .env
```

On Linux, use `cp .env.example .env` and open it with `nano .env`.

Find `OPENAI_API_KEY=` and paste your key straight after the `=`, with no spaces.
Leave the three lines below it unchanged. Save with **Ctrl + S**, then close
Notepad.

```text
OPENAI_API_KEY=sk-or-v1-your-key-here
```

To use OpenAI instead, clear the base-URL line and set OpenAI model names. The
comments inside `.env` explain how.

### Step 3 — Restart the app

```powershell
docker compose -f infra/compose.yaml down
docker compose -f infra/compose.yaml up
```

### Step 4 — Try it

Open <http://localhost:3000/assistant> and ask a question, for example "I want a
phone with a good camera". Ask a follow-up to see it remember the conversation,
or use **Ask about an order** to attach one of your orders.

> `.env` is ignored by Git, so your key is never uploaded. Never share it.

---

## Troubleshooting

**"docker : The term 'docker' is not recognized" (Windows) or
"docker: command not found" (Linux).**
Docker is not installed, or Docker Desktop is not running. On Windows, open
Docker Desktop and wait for "Engine running".

**"port is already allocated" / "address already in use".**
Something else is using port 3000 (the shop) or 8000 (the API). Close the other
program, or edit `infra/compose.yaml` and change `"3000:3000"` to `"3001:3000"`
(the left number is the one on your computer).

**It seems stuck, or the data looks wrong.**
Reset the demo data completely and start clean:

```bash
docker compose -f infra/compose.yaml down -v
docker compose -f infra/compose.yaml up --build
```

The `-v` deletes the demo databases so they are re-created and re-seeded fresh.

**The first run is very slow.**
It is downloading images (about 2 GB) and building the app. Later runs are much
faster.

**I closed the terminal.**
The app stops when you close it. Reopen a terminal in the project folder and run
the **Step 4** start command again.

---

## What's inside

| Area | Highlights |
|---|---|
| Customer storefront | Catalog with filters, product detail, comparison, cart, retry-safe checkout, order history, saved addresses |
| AI shopping assistant | Answers questions, suggests products, keeps the thread of the conversation, and can attach one of your own orders to ask about it |
| Smart search | Photo search, voice search, and dynamic filters |
| Predictive inventory (BO-01) | 14-day demand forecast and automatic reorder through a supplier simulator |
| Dynamic pricing (BO-02) | Bounded price changes from supply, demand, cost, and season |
| Customer segmentation (BO-03) | RFM segments with a documented rule set and CSV export |
| Fraud detection (BO-04) | Pre-checkout risk scoring with an operator review queue |
| Business intelligence (BI-01) | Consumer and financial dashboards that reconcile to the orders |

Built with Next.js, React, and Tailwind CSS; Python and FastAPI; PostgreSQL and
MongoDB; Scikit-learn, PyTorch, and the OpenAI API; Docker.

## Project documentation

- [Software Requirements Specification](docs/SRS.md) and [requirements traceability](docs/requirements-traceability.md)
- [Architecture diagrams](docs/diagrams/README.md) and [data foundation](docs/architecture/data-foundation.md)
- [API contracts](docs/api/README.md)
- [Design system](DESIGN.md) and [UI/UX specification](docs/ui-ux/README.md)
- [Test report](docs/test-report.md) and [testing guide](docs/testing.md)
- [Decision register](docs/decisions.md) and [progress](docs/progress.md)
- [User manual](docs/user-manual.md), [demo script](docs/demo-script.md), and [final presentation](docs/presentation/README.md)

## For developers

Run the app in the background and develop against it:

```bash
docker compose -f infra/compose.yaml up --build -d
```

Or use the shortcuts in the [`Makefile`](Makefile): `make up`, `make up-d`,
`make down`, `make reset`, `make logs`, `make test`, `make gates` (run `make`
for the list).

The full test/verification commands — API suites, database checks, integration,
security and load, the accessibility gate, and the demo rehearsal — are in
[`docs/testing.md`](docs/testing.md). CI runs the API suite and the storefront
typecheck/tests/build on every push.

Service-level guides: [`services/api/README.md`](services/api/README.md) and
[`apps/storefront/README.md`](apps/storefront/README.md).

## Status and limitations

Stages 1–4 are complete and documented; Stage 5 packaging, deployment guidance,
the user manual, the demo script, and the presentation are delivered. The
remaining work needs outside access and is stated honestly rather than implied:

- The assistant and voice transcription are proven live through OpenRouter with
  `deepseek/deepseek-v4.1-flash` and `openai/whisper-large-v3` — grounded
  answers, own-order lookup, conversation memory, and real speech transcribed
  from every browser's recording format.
- No cloud deployment — AWS placement needs an account.
- Accessibility is verified by automated axe-core checks; no manual
  screen-reader pass has been run.
- The Arabic copy has not had a native-speaker pass: the 43 strings from the UI
  overhaul, plus the assistant and voice surface rewritten since. Both lists are
  in [docs/ui-ux/manual-review.md](docs/ui-ux/manual-review.md).
- Recommendation, forecast, segmentation, pricing, and fraud models are trained
  and evaluated on labelled synthetic data; the results show the pipeline works,
  not real-world quality.

Details and per-requirement evidence are in the [test report](docs/test-report.md)
and [progress](docs/progress.md).
