# Agent Contributor Guide

This document explains the workflow, quality bar, architecture rules and etiquette expected from autonomous code‑generation agents (e.g. OpenAI Codex, GPT‑4o) contributing to this repository. Follow it **every time** you change code or docs.

## 1. Golden Loop – **E·C·P·I**

| Phase         | What you *must* do                                                                                                                                                                                                                                                                                                                                                             |
| ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Examine**   | Silently read every supplied file/snippet **and the repository README(s)** for context. Then consult `/docs` for relevant **Layer Guides** (why a layer exists, allowed deps) and **Agent Contracts** (public interface, I/O schema, SLA). Build a mental model and list unknowns.                                                                                             |
| **Challenge** | Before planning, critically reflect on the proposed design; suggest better architectures, edge‑cases or simpler approaches.                                                                                                                                                                                                                                                    |
| **Plan**      | Once questions are answered, post a **numbered checklist** (≤ 10 steps) describing the exact changes you will make **with each item mapped to one of the three layers – presentation, service, infrastructure**. Wait for the maintainer’s message `Approved – implement X‑Y` before touching code.                                                                            |
| **Implement** | Carry out the approved steps. After committing:<br>• Summarise what changed in plain language (no diff).<br>• Run the full test‑suite and any additional scripts named in the task’s *Success criteria*.<br>• If tests fail, post a short failure summary and a fix plan; wait for approval.<br>• After three consecutive unsuccessful fixes, stop and propose an alternative. |

Important -- before implement, you should acquire confirmation of your plan from maintainer!

### Interaction Rules

* **One clarifying question per message**—keep the loop tight.
* Never skip a phase, even for “tiny” fixes.
* Treat *Success criteria* in the task description as blocking acceptance tests.

## 2. Testing & Verification

| Task                       | Command                                                                              |
| -------------------------- | ------------------------------------------------------------------------------------ |
| Run Python tests           | `pytest -q`                                                                          |
| Run JS/TS package tests    | `pnpm test --filter <pkg>`                                                           |
| End‑to‑end simulation      | `uv python simulate.py run test_scenario.json --prompt-spec file_based_prompts.json` |
| Inspect conversation batch | `jq .results llm-simulation-service/results/batches/<batch_id>_metadata.json`        |

Add or update tests for every new behaviour. CI must be green before requesting review.

## 3. Code Quality

* **Python**: Black (line length 100), Ruff, type hints, docstrings.
* **JavaScript/TypeScript**: ESLint, Prettier, strict TS.
* Functions ≤ 50 LoC; favour pure, testable components.
* Use descriptive names; avoid magic numbers.

## 4. Layered Architecture & Documentation

Our backend follows a **three‑layer architecture**:

| Layer          | Purpose                                                                   | Typical contents                      |
| -------------- | ------------------------------------------------------------------------- | ------------------------------------- |
| Presentation   | I/O boundaries – request/response DTOs, controllers, CLI, FastAPI routes. | No heavy logic. Translate & validate. |
| Service        | Business logic, orchestration, domain models, state machines.             | Pure functions / classes, no I/O.     |
| Infrastructure | External integrations – DB, file IO, queues, LLM providers, HTTP calls.   | Encapsulate side‑effects behind ports |

**Rules**

1. Each new feature must have its responsibilities split across these layers. Do **not** leak one concern into another (e.g. DB calls from a service function).
2. If you must change the public contract of an existing class/module, include that change in your *Plan* and justify it in the *Challenge* phase.
3. After implementation, update documentation:

   * **README** – refresh high‑level architecture or business logic overview if affected.
   * **Layer Guides** – list new/modified components and their role.
   * **Contracts** – add or amend interface definitions, method signatures, accepted/returned data shapes.

Documentation lives in `/docs`. Keep it in sync with the codebase; CI will reject PRs with missing doc updates.

## 5. Commit & PR Workflow

1. Keep commit **subject** ≤ 72 chars; body explains *why*.
2. PR title: `[<project_name>] <concise summary>`.
3. Fill out the PR template, link issues, and attach relevant logs or screenshots.
4. Ensure all affected docs (README, layer guides, contracts) are updated alongside code.
5. Require at least **one reviewer approval + green CI** to merge.

## 6. Do / Don’t

| ✅ Do                        | ❌ Don’t                    |
| --------------------------- | -------------------------- |
| Ask until sure              | Guess requirements         |
| Keep messages brief         | Paste raw diffs            |
| Include tests               | Merge red builds           |
| Summarise changes           | Duplicate full file bodies |
| Propose design improvements | Bypass Challenge phase     |

---

**When in doubt, ask — precision beats speed. Happy shipping!**
