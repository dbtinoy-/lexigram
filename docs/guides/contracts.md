---
title: "Contracts, Boundaries, and Extension Points"
description: "Where contracts live, what counts as a boundary violation, and how to create or upstream a contract."
---

Every interface that crosses a package boundary in the framework must live in
`lexigram-contracts` — a zero-dependency package that only ever defines
types, protocols, and exceptions. This guide states the rules for deciding
*where a new contract goes*, *when a local protocol is allowed*, and *how a
consumer upstreams a contract*.

The golden rule: **a type, protocol, or exception shared by two or more
packages belongs in `lexigram-contracts`, organized by domain directory —
never by package name.**

---

## 1. The Rules

### R1 — The golden rule

A type, protocol, or exception referenced by **two or more packages** must
live in `lexigram-contracts`, under the domain directory that describes
*what it is*, not *who uses it*.

| Shared by | Canonical home |
|---|---|
| Vector-store + AI packages | `lexigram.contracts.ai.vector` (e.g. `DocumentProtocol`, `ChunkerProtocol`) |
| Web + admin packages | `lexigram.contracts.admin` (e.g. `AdminError`, `BaseAdminContributor`) |
| Any package + CLI tooling | `lexigram.contracts.cli` (e.g. `GenerationResult`, `parse_fields`) |
| RAG pipeline packages | `lexigram.contracts.ai.rag`, `lexigram.contracts.ai.vector` |

Rule of thumb: if the same `import` statement appears in two or more
packages, the symbol is a contract. One package importing a symbol from
another package's internals is a boundary violation.

### R2 — Experimental contracts still land in the stable contracts package

There is **no separate experimental contracts package** and none may be
created. Experimental packages (`lexigram-ai-*`, `lexigram-multimedia-*`,
`lexigram-cli`, `lexigram-ui`, `lexigram-admin`) publish to their own
repositories, but their cross-package contracts still live in
`lexigram-contracts` under clearly experimental domain directories:

| Domain directory | Serves |
|---|---|
| `lexigram.contracts.ai` | the 17 `lexigram-ai-*` packages |
| `lexigram.contracts.multimedia` | the 8 `lexigram-multimedia-*` packages |
| `lexigram.contracts.admin` | `lexigram-admin` and the stable packages that consume it |
| `lexigram.contracts.cli`, `lexigram.contracts.ui` | `lexigram-cli`, `lexigram-ui` |

A new experimental domain directory requires a short proposal stating: which
packages share it, which stable packages consume it (if any), and which core
domains it imports.

### R3 — Stability is marked by consumption, not by directory

A contract consumed by a **stable package** is de facto stable, regardless of
the domain directory it lives in — treat it as frozen (semver minor+ only).

Experimental domain directories may evolve (breaking changes are permitted
within reason) but may import **only core contracts domains** — e.g.
`core.result`, `core.di`, `infra.*`, `exceptions.domain`,
`data.vector.exceptions`, `observability.ai`. The dependency direction is
inward only: `lexigram.contracts.ai` → core domains is sanctioned; core
domains → `lexigram.contracts.ai` is a violation.

### R4 — Local protocols are seams, not contracts

A package may keep its own `protocols.py` for *internal* implementation
seams (e.g. a plugin used only inside the package). It must be consumed only
within that package. A cross-package import of a local protocol module is a
violation — the protocol must be promoted into the matching contracts domain
per R1/R2.

This rule is enforced mechanically: `.importlinter` forbids cross-package
imports of the known local protocol modules (see the `local-protocols-scoped`
contract). Run the check with:

```bash
uv run python tools/lint_imports.py
```

### R5 — One canonical definition

No duplicate protocol, type, or exception definitions. If a symbol already
exists in `lexigram-contracts`, reference it — never copy it into a package.
A local copy with a different signature is drift, not isolation.

### R6 — Consumer contracts stay in the consumer project

A contract used only by a consumer's application stays in that application.
It never becomes a new framework package.

To upstream a consumer contract that became generally useful:

1. Submit a proposal (this plan's format: context, evidence of ≥2 packages
   sharing it, target domain directory).
2. Get it reviewed against R1–R3.
3. Move it into the canonical contracts domain directory.
4. Change the consumer to depend on `lexigram-contracts`.

---

## 2. Decision Tree

```
New type / protocol / exception needed
|
+-- Used by >= 2 framework packages?
|       |
|       +-- YES --> lexigram-contracts, by domain directory
|       |              |
|       |              +-- experimental domain (ai, multimedia) --> R2 (same package, experimental dir)
|       |              +-- stable domain/consumed by stable pkg --> R1 + freeze (R3)
|       |
|       +-- NO --> imported from another package today? --> promote to contracts (R4 violation)
|       |              +-- single-package internal seam --> local protocols.py (R4)
|
+-- Consumer application code only --> stays in the consumer project (R6)
```

---

## 3. Publication Tiers at a Glance

| Tier | Packages | Published to |
|---|---|---|
| Stable | 36 packages + `lexigram-contracts` | main image |
| Experimental (individual) | `lexigram-cli`, `lexigram-ui`, `lexigram-admin` | own `*-experimental` repos |
| Experimental (groups) | `lexigram-multimedia-*` (8 pkgs), `lexigram-ai-*` (17 pkgs) | shared per-group `*-experimental` repos |

A leak guard in the publish pipeline rejects experimental package names from
the stable image, so boundary violations that would invert this table fail
the build. `lexigram-contracts` is the single contract package for all of
them.

---

## 4. Checklist for Adding a Contract

- [ ] Who consumes it? If ≥2 packages → `lexigram-contracts`.
- [ ] Which domain directory describes it? (never a package name)
- [ ] Does it already exist in contracts? If yes, reference it (R5).
- [ ] If experimental: is the domain dir sanctioned (ai/multimedia/admin/ui/cli) or does it need a proposal (R2)?
- [ ] Does it import only core domains (R3)?
- [ ] If it stays local: is it a single-package seam, and does it pass
      `python tools/lint_imports.py` (R4)?
- [ ] Consumer-only? Leave it in the consumer project (R6).