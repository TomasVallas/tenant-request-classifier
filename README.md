# Tenant Request Classifier

> **Tiivistelmä:** Sovellus luokittelee vuokralaisen suomenkielisen palvelupyynnön, arvioi sen kiireellisyyden ja ehdottaa kohteliasta vastausta. Kielimalli vain ehdottaa, deterministiset säännöt ja ihminen päättävät, eikä sovellus koskaan lähetä vastausta itse. Kyseessä on portfoliodemo kuvitteelliselle vuokrataloyhtiölle, ja kaikki data on keksittyä.

> **Status:** under construction. This README describes the planned application, and sections marked _Coming in phase N_ are not implemented yet.

## What it does and why

Handling tenant service requests takes time: each message has to be read, routed, prioritised and answered. This application prepares that work for a human. For a request such as "Keittiön hana vuotaa, asunto B12", it:

1. classifies the request as `vika`, `laskutus`, `muutto` or `muu`
2. assesses urgency as `kiireellinen` or `normaali`
3. writes a short summary
4. suggests a polite reply in Finnish
5. gives a confidence score (0–1) and flags whether a human must review the request

## Screenshot

_Coming in phase 7, with instructions for capturing it._

## Live demo

_Coming after the Azure deployment in phase 6._

## Architecture

```mermaid
flowchart LR
    A[React + TypeScript] --> B[FastAPI]
    B --> C[LangChain]
    C --> D[Language model]
    D --> E[Deterministic rules gate]
    E --> F[Human decides]
```

## Design decisions

- **Structured output:** the model must return a validated schema instead of free text.
- **Rules gate:** deterministic rules run after the model and have the final say.
- **Human in the loop:** the application only suggests and never sends a reply.
- **Fake provider:** a deterministic classifier allows tests and demos without API keys or costs.
- **Prompt injection protection:** request text is delimited and treated strictly as data.

## Evaluation results

The pipeline is evaluated against 30 fictional labelled requests, including ambiguous messages, typos, two issues in one message and a prompt injection attempt. See the [full results](backend/eval/results.md).

Current baseline with the `fake` keyword provider, which is not a language model:

| Metric | Result |
| --- | ---: |
| Category accuracy | 93.3% |
| Urgency accuracy | 86.7% |
| Urgent requests detected | 55.6% |
| Prompt injection cases handled | 1/1 |

Run the evaluation from the `backend` folder:

```bash
python -m eval.run_eval --provider fake
python -m eval.run_eval --provider azure_openai --limit 3   # small paid trial, writes no file
python -m eval.run_eval --provider azure_openai             # full run, updates results.md
```

## Running locally

### Backend

Requires Python 3.11+. The default `fake` provider needs no API key.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate      # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
cp .env.example .env           # Windows PowerShell: Copy-Item .env.example .env
uvicorn app.main:app --reload
```

The API runs at <http://localhost:8000>, with interactive docs at <http://localhost:8000/docs>.

Try it from the `backend` folder in a second terminal. In Windows PowerShell, write `curl.exe` instead of `curl`.

```bash
curl http://localhost:8000/api/health
curl -X POST http://localhost:8000/api/classify -H "Content-Type: application/json" --data-binary "@examples/urgent.json"
```

Run the backend checks:

```bash
pytest
ruff check .
ruff format --check .
```

### Using a real model

Set `LLM_PROVIDER` and the provider's values in `backend/.env`, then restart the server. `GET /api/health` shows the active provider.

| `LLM_PROVIDER` | Required settings |
| --- | --- |
| `azure_openai` | `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_API_VERSION` |
| `openai` | `OPENAI_API_KEY`, `OPENAI_MODEL` |
| `anthropic` | `ANTHROPIC_API_KEY`, optionally `ANTHROPIC_MODEL` |

The model must support structured outputs. If an OpenAI or Azure model rejects the temperature parameter, set `LLM_TEMPERATURE=none`.

### Frontend

_Coming in phase 4._

## Tests and CI

_Coming in phase 5._

## Limitations and future work

- All data is fictional. Real data would require data processing agreements and a model hosted in the EU.
- Integration with a ticketing system is not included.
- The application supports Finnish only.
