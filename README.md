# PROJECT REPORT

# Elvyn

*A Personal Productivity, Savings & AI Coaching Companion App*

**Prepared by AbdulRazaq**
IT Operator, DataGuard NG · Founder, KunleTech

September 2026 — Revision 5 (Post–Phase 5 / Phase 6 In Progress)

*"Make Progress Personal."*

---

## 1. Executive Summary

Elvyn (originally built and shipped internally under the working name "Change") is a personal mobile application designed and built by AbdulRazaq to address four recurring problems in daily life: forgetfulness, procrastination, disorganization, and inconsistent savings habits. It is architected as a full-stack solo software project — a genuine production system, not a prototype — and simultaneously serves as a deliberate vehicle for deepening real-world skills in backend engineering, mobile development, and applied artificial intelligence.

Elvyn combines five core pillars: an intelligent task and reminder system with per-task priority notification control; a frictionless capture layer ("Brain Dump") for offloading thoughts before they need to be organized; a mood-aware check-in system; a Retrieval-Augmented Generation (RAG)-bound AI coaching layer, currently in its foundational single-turn phase; and — pending regulatory clearance — a locked savings vault enforcing financial discipline through goal-based commitment and a cooling-off mechanism on early withdrawal.

The product was renamed from "Change" to "Elvyn" mid-build once it became clear the original name was tied to the founder's personal motivation rather than a name that would generalize to other users. The rename came with a full brand identity: a folded-ribbon "E" mark, an indigo/amber/emerald color system, and a small two-state illustrated mascot used to give the AI coaching layer a consistent, non-childish visual personality.

As of this revision, **Phases 1 through 5 are complete**, and **Phase 6 (Retrieval-Augmented Generation and behavioral intelligence) is in its foundational stage**, with the first durable behavioral-event logging system built and pending final verification against a live database.

---

## 2. Product Identity

| | |
|---|---|
| **Product name** | Elvyn |
| **Tagline** | "Make Progress Personal." |
| **Founder / brand identity** | KunleTech |
| **Legal entity** | K.T Labs Ltd |
| **Platform (current)** | Android (React Native / Expo); iOS deliberately out of scope until real demand or resourcing exists |
| **Market** | General productivity/AI-coaching audience; Savings feature is Nigeria-specific |

**Visual identity:**

| Token | Hex | Use |
|---|---|---|
| Indigo (Primary) | `#4F46E5` | Primary actions, brand accent |
| Deep Purple | `#312E81` | Deep brand shade, gradients |
| Amber (Accent) | `#F59E0B` | Highlights, mascot accents, milestones |
| Emerald (Success) | `#10B981` | Completion states, positive confirmation |
| Soft White (Background) | `#F8FAFC` | Light mode background |
| Near Black (Text) | `#111827` | Primary text, light mode |

The mascot is a small, gender-neutral, non-human, non-robotic illustrated creature (indigo body, amber accents) rendered as scalable vector assets, currently implemented in two emotional states (`neutral`, `supportive`) via a single reusable `<ElvynMascot variant size />` component. A fuller, streak-driven visual evolution system (progressively more expressive states tied to consistency milestones) is designed conceptually but deliberately not built, pending real usage data on whether it adds value.

---

## 3. Problem Statement & Motivation

The motivation for Elvyn is personal in origin, generalized deliberately during the rename. Four patterns motivated the build:

| Problem | How Elvyn addresses it |
|---|---|
| Forgetting tasks and commitments | Reminders with per-task priority-interruption control; local, offline-reliable delivery |
| Lack of self check-in | Lightweight, optional morning/evening mood check-ins, never mandatory |
| Procrastination | AI-assisted task breakdown ("Make it easier"), always user-initiated, never automatic |
| Disorganization | Frictionless capture (Brain Dump) separated cleanly from structured task management |
| Poor savings discipline | A goal-locked savings vault with a cooling-off period on early withdrawal (Nigeria-only, pending Paystack business verification) |

A further, explicit design principle carried through the entire build: **calm over crowded, action over administration, evidence over assumption, no shame.** Concretely, this means the product never labels a user's behavior (e.g. it will never store or surface a judgment like "procrastinator"), never auto-executes AI-suggested actions without confirmation, and treats a missed task or broken streak as neutral information rather than a failure state.

---

## 4. Technical Architecture

### 4.1 Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React Native (Expo) + TypeScript |
| Backend | FastAPI (Python, async) |
| Database | PostgreSQL via Supabase |
| ORM & Migrations | SQLAlchemy 2.0 (async) + Alembic |
| Authentication | Supabase Auth (migrated from a custom JWT implementation in Phase 2) |
| Background jobs | Celery + Redis (Upstash) |
| AI | Google Gemini, via a server-side structured-output wrapper |
| Payments (pending) | Paystack — Nigeria-specific, gated behind business account verification |
| Push notifications | Expo local notifications (primary, offline-capable) + Firebase Cloud Messaging (server-originated fallback only) |
| Icon/vector assets | `react-native-svg` |
| Calendar UI | `react-native-calendars` |
| Voice input | `expo-speech-recognition` |

### 4.2 Backend Domain Structure

The backend follows a domain-based folder structure (`app/users/`, `app/tasks/`, `app/braindump/`, `app/ai/`, etc.), each owning its own models, service logic, and router — a decision made in Phase 1 and validated repeatedly since, including surviving the Phase 2 authentication migration with zero changes required to downstream routes.

### 4.3 Security Model

- All authentication is handled by Supabase Auth; FastAPI verifies Supabase-issued JWTs.
- Row Level Security is enabled on Supabase as defense-in-depth, verified directly against the live project.
- Every data-owning query is filtered by `user_id`, not merely by record ID — UUID unguessability is treated as an implementation detail, never as authorization.
- The Gemini API key is server-side only and never shipped in the client application.
- The AI layer cannot access savings/financial data or execute any financial operation under any circumstance — this boundary is architectural, not merely a prompt instruction.
- AI-invoked actions (once function-calling ships in a later phase) will always be executed by FastAPI after independent ownership and authorization checks — the model itself is never granted direct database access.

---

## 5. Data Model (Current, as of Phase 6 Day 1)

### 5.1 Core Tables

| Table | Purpose |
|---|---|
| `users` | Identity, country/entitlement linkage, notification/appearance preferences, Paystack/DVA/payout profile fields (pending activation), activity-streak fields |
| `tasks` | Task records — typed priority/status, soft-delete (`is_deleted`/`deleted_at`), per-task `priority_reminder`, recurrence linkage (`series_id`, `occurrence_date`), Brain Dump provenance (`source_brain_dump_id`) |
| `task_series` | Recurring-task rule definitions (frequency, interval, days of week, end conditions) |
| `task_events` | Append-only behavioral event log (`created`, `completed`, `not_now`, `rescheduled`, `cancelled`, `overdue`, `deadline_changed`, `reminder_scheduled`, `reminder_opened`) with JSONB metadata |
| `task_event_outbox` | Durable delivery buffer ensuring a failed event write never blocks or breaks the task action it observes |
| `brain_dumps` | Raw captured thoughts — `content`, `source` (text/voice), `is_converted` |
| `checkins` | Morning/evening mood (1–5 scale), optional goal, goal status, optional reflection |
| `wins` | Lightweight freeform positive-moment log (legacy, superseded in relevance by the activity-streak system) |
| `ai_usage_logs` | Per-user daily AI request quota tracking |
| `ai_interactions` | Logged AI exchanges — intent, context size, token counts, tool usage, outcome |
| `feature_entitlements` | Server-enforced per-user feature flags (`savings_enabled`, `ai_enabled`, `brain_dump_enabled`, `premium`) — the actual mechanism behind the Nigeria-only Money tab |
| `savings_vaults`, `pending_deposits`, `savings_transactions`, `platform_revenue` | Savings/Paystack domain — architecturally complete, gated on Paystack business verification before real-money use |

### 5.2 Notable Schema Decisions

- **Soft deletion, not hard deletion**, is the standing pattern for tasks and (eventually) other user-generated content — supports recoverability and preserves behavioral history.
- **`event_type` on `task_events` is a validated Python enum backed by a plain `VARCHAR`**, not a native Postgres enum — a deliberate tradeoff favoring cheap extensibility (new event types never require a schema migration) over database-level value constraints, consistent with the existing precedent on `tasks.recurrence`.
- A live schema audit conducted mid-Phase-5 caught and corrected several instances of documentation/reality drift: an `ai_interactions` table referenced in documentation but never actually created; dead columns left over from a reversed KYC/BVN approach; a superseded account-level DND toggle; an unused `avatar_url` column. All were resolved via a single cleanup migration.

---

## 6. Feature Breakdown

### 6.1 Home

The Home screen is deliberately restrained: a greeting with a rotating, context-aware ELVYN prompt (courage/motivation in the morning, mood-aware in the evening once a check-in exists); a compact progress indicator; a Brain Dump quick-capture entry point; a lightweight 3-option mood check-in card; a compact calendar link; and today's task list. Explicitly excluded: a dashboard-style grid of every feature, a permanently visible mascot, and a duplicate calendar widget.

### 6.2 Tasks

Full CRUD, typed priority/status, and a deliberately precise action vocabulary distinguishing five genuinely different user intents:

| Action | Meaning | Effect |
|---|---|---|
| **Not now** | "I still intend to do this, just not right now" | Reminder time shifts forward; task stays active |
| **Reschedule** | "Change the actual planned time" | `due_date`/`reminder_time` genuinely updated |
| **Cancel** | "Remove from my active list" | Soft-deleted, recoverable |
| **Edit** | Update details | Same task ID, same history |
| **Complete** | Done | Status updated, retained in history, never hard-deleted |

AI-assisted task breakdown ("Make it easier") is available from Task Detail, strictly user-initiated, and never auto-creates subtasks without explicit confirmation of which suggested steps to add.

### 6.3 Recurring Tasks

A task-series model (`task_series` + linked task occurrences) generates a rolling window of future occurrences via a scheduled background job, with database-level uniqueness constraints preventing duplicate generation under concurrent or retried execution. Editing a recurring task supports three distinct scopes — this occurrence only, this and all future occurrences, or the entire series — reflecting that these are meaningfully different user intents, not one generic "edit" action.

### 6.4 Calendar

A dedicated (non-tab) screen presenting the same task records as Home, filtered by date, with month-level presence indicators. Deliberately not a separate data model — Calendar is a view, not a second source of truth.

### 6.5 Brain Dump

The capture-first philosophy is enforced structurally, not just in copy: saving a thought is always instant and free of any AI cost. A lightweight, fully deterministic (non-AI) pattern check flags a dump as a possible task; the user must explicitly request conversion before Gemini is ever called. Conversion is a genuine two-step confirmation flow (parse → user reviews and selects which of potentially several suggested tasks to keep → convert), never silent, and the original dump is always preserved with a provenance link to any task it produced. Retried conversions are idempotent — they cannot produce duplicate tasks.

### 6.6 Check-Ins

A single record type serves both morning and evening check-ins, distinguished by a `type` field rather than separate tables. Mood is stored as an integer (1–5); the interface exposes a fast 3-option version on Home and the full 5-option scale on a dedicated Check-in screen, which also carries evening-only goal status and optional reflection. A submission always produces a real record — the interface never fakes a completed check-in merely to dismiss a prompt.

### 6.7 Activity Streak

Independent of check-ins and the legacy Win Log, the streak system tracks consecutive days of genuine app activity, recorded once per user-local calendar day (a device timezone is stored to make this correct across travel). A broken streak resets the current count but preserves the historical longest streak, and is treated as neutral information in the interface, never as a punitive signal.

### 6.8 Notifications

Local, offline-capable scheduled notifications (via Expo) are the primary reminder-delivery mechanism; Firebase Cloud Messaging is reserved strictly for server-originated events and, as a fallback, checks whether a local reminder has already been confirmed scheduled before sending, to prevent duplicate alerts. A per-task **Priority Reminder** flag — replacing an earlier account-wide "Strict/Normal" DND toggle — lets a user mark individual reminders as needing stronger, OS-supported interruption behavior, framed honestly as "harder to miss when supported by your device" rather than a guaranteed DND override. There is no escalation or re-notification mechanism; an unanswered reminder is simply logged as behavioral signal, never chased.

### 6.9 AI Coaching Layer (Phase 5 foundation)

The current AI screen is a scoped personal coach, not a general-purpose chatbot. An empty-state screen offers suggested prompts oriented around the user's own tasks and progress; a lightweight intent classifier determines what ELVYN-owned data is actually relevant to a given message, so only that data — never a user's entire history — is included in the prompt sent to Gemini. Responses are returned as structured JSON and rendered natively by the client, rather than the model generating free-text descriptions of interface elements. The system is deliberately **single-turn** in this phase: no persistent conversation history exists yet, and no AI-driven task creation, editing, or deletion is exposed — both are explicitly reserved for Phase 6, once genuine behavioral data exists to ground them in.

### 6.10 Money / Savings

Architecturally complete from Phase 4 (vault creation, Paystack Dedicated Virtual Account collection, transfer-based payouts, withdrawal PIN separate from the local app passcode, milestone tracking, break-vault and emergency-withdrawal mechanics) but gated end-to-end on Paystack business account verification, which itself is gated on completed CAC business registration. No real money has moved through the system to date. Feature access is enforced server-side via `feature_entitlements.savings_enabled`, itself derived from a confirmed `country_code = "NG"`, never re-derived from device signals on each request.

### 6.11 Appearance

A theme mechanism (System/Light/Dark, persisted locally) exists and is applied to Home, Task Detail, Brain Dump, and core task components; a full visual retrofit of every remaining screen is intentionally deferred as a separate visual-polish pass, not yet scheduled.

---

## 7. Development Roadmap & Phase History

| Phase | Focus | Status |
|---|---|---|
| 1 | FastAPI/Supabase foundation, JWT auth, React Native scaffold | Complete — auth later migrated to Supabase Auth |
| 2 | Task CRUD, Celery-driven reminders, Brain Dump backend | Complete |
| 3 | Check-ins, direct Gemini integration, habit/confidence log | Complete |
| 3.5 | Debt-clearing sprint: local notifications, calendar UI, voice capture, EAS build pipeline | Complete |
| 4 | Savings vault, Paystack integration | Architecturally complete; gated on business verification |
| 5a | Rebrand to Elvyn; Home/Check-in/Task/Calendar/Brain Dump/AI-screen rebuild; per-task Priority Reminder; dark-mode mechanism; voice task creation; notification reconciliation | **Complete**, confirmed on-device |
| 5b | Full visual polish pass across all remaining screens | Deferred, unscheduled, non-blocking |
| 6 | Behavioral event logging (`task_events`), recurring-task-series redesign, activity streak — foundational RAG groundwork | **In progress** — implemented, pending live-database verification |
| 6 (cont.) | Conversational memory, deeper RAG retrieval, AI-driven task actions | Not yet started |
| 7 | Vector RAG (pgvector/embeddings), text-to-speech, voice conversation | Not started |
| 8 | Self-updating AI personality profile, premium tier, customer support, admin tooling, publish preparation | Not started |

---

## 8. Verification Status — Honest Account

Consistent with a standing practice on this project of verifying claims against the real system rather than trusting documentation, the current state as of this revision is:

- Phases 1 through 5a: **confirmed working on-device.**
- Phase 6 Day 1 (behavioral event logging, the recurring-task-series redesign, the activity-streak system): **implemented and unit-tested against a mocked database session, but not yet verified against a live PostgreSQL instance.** No environment configuration currently exists to run the relevant migrations or confirm real data is written correctly. This is the single most important outstanding item before any further Phase 6 work is trusted as a foundation.
- Several real bugs were caught specifically by comparing designed architecture against actual running code rather than assuming a prior description was still accurate — including a Brain Dump conversion flow that had silently reverted to an earlier single-task, auto-creating design, and a live-database schema audit that surfaced multiple pieces of dead or superseded schema.

---

## 9. Risks & Honest Constraints

- The savings vault's lock is a behavioral deterrent, not a technical barrier — a sufficiently determined user could still withdraw funds directly through Paystack's own systems.
- Publishing Elvyn beyond a personal/trusted-circle audience introduces obligations (privacy policy, terms of service, eventual regulatory exposure) that do not apply at the current stage.
- The project's greatest historical risk has never been technical difficulty but sustained follow-through and scope discipline — repeatedly, proposed architecture documents attempted to pull deferred future work (a full mascot evolution system, full conversational AI memory, AI-driven task mutation, a complete behavioral-event system) forward into the current phase before it was actually needed; each instance was caught and deliberately deferred rather than absorbed.
- Formal independent security review has not occurred and is explicitly scheduled no earlier than Phase 8, ahead of any real external users or real money.
- International regulatory questions (subscription billing via app-store in-app-purchase requirements, cross-border payment processor selection) have been researched but are explicitly time-boxed to be re-verified immediately before Phase 8 implementation, since the vendor landscape in that space is acknowledged to shift meaningfully within a single year.

---

## 10. Skills Development

Beyond its function as a personal productivity tool, Elvyn has served as a deliberate vehicle for developing backend engineering (async FastAPI, SQLAlchemy, Alembic, authentication migration), background job orchestration (Celery, Redis, idempotent scheduled generation), mobile development (React Native, Expo, native module boundaries), applied AI engineering (prompt scoping, structured output, cost-aware context retrieval, tool-calling security boundaries), and systems-level product judgment — most visibly, the repeated, disciplined practice of catching and deferring scope creep rather than absorbing every proposed enhancement into the current build.

---

## 11. Conclusion

Elvyn has evolved from a personally-motivated productivity tool into a coherently architected, security-conscious application with a genuine and differentiated product thesis: an AI coaching layer grounded in a user's own real behavioral data rather than acting as an unrestricted general-purpose assistant, built on top of a task and capture system deliberately designed to reduce friction rather than add administrative overhead. Phases 1 through 5 represent a complete, daily-usable personal application; Phase 6 has begun laying the behavioral-data foundation that the product's stated differentiation — grounded, evidence-based AI guidance rather than generic productivity assistance — actually depends on. The project's continued success will be measured, as it always has been on this build, by whether claimed progress is verified against the real running system before it is trusted, and whether deferred scope stays deferred until its actual phase arrives.

*Prepared by AbdulRazaq · KunleTech · September 2026 (Revision 5)*