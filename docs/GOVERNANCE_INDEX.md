# **Relax Governance Index**

_Version: 1.0 — Canonical Index of Governance Artifacts_  
_Status: Stable_

This index defines the authoritative documents that govern the design, security posture, and operational evolution of the Relax service. Each document has a clear purpose, lifecycle, and relationship to the others. Together, they form the **Relax Governance Kernel**.

---

## **1. Core Documents (Stable)**

These documents define the _current_ architecture and its security posture. They change infrequently and only through intentional versioning.

### **1.1 ARCHITECTURE v1.0**

**Purpose:**  
Defines what Relax _is_, how it is structured, and the invariants that shape its behavior.

**Contents:**

- System topology
- Request flow
- Extraction pipeline
- Concurrency & rate limits
- Security & hardening measures
- Deployment strategy
- Key constraints & tradeoffs

**Update cadence:**  
Low. Updated only when the architecture materially changes.

---

### **1.2 THREAT_MODEL v1.1**

**Purpose:**  
Defines what can go wrong, why the architecture looks the way it does, and which threats matter.

**Contents:**

- Scope & assumptions
- Assets
- Trust boundaries
- STRIDE analysis
- Prioritized risks (P1–P5)
- Derived invariants

**Update cadence:**  
Low–medium. Updated when new threat classes emerge or architecture changes.

---

## **2. Evolution Documents (Living)**

These documents describe how Relax will evolve over time. They are intentionally forward‑looking.

### **2.1 HARDENING_ROADMAP**

**Purpose:**  
Describes _future enhancements_ to Relax’s security posture. Items here correspond to the `[Planned]` mitigations in the Threat Model.

**Contents:**

- Planned improvements, grouped by area
- Cross-references to Threat Model `[Planned]` items

**Update cadence:**  
Medium. Updated as enhancements are completed or reprioritized.

> **Transparency note:** This repository is public, and so is every governance
> document in it — including the Threat Model, which explicitly labels
> not-yet-implemented controls as `[Planned]`. The project deliberately favors
> transparency over secrecy: the security posture relies on layered, implemented
> controls, not on hiding the gap list. Any internal-only operational planning
> lives outside this repository.

---

## **3. Governance Mechanics**

These rules define how the governance kernel evolves.

### **3.1 Versioning Rules**

- All core documents carry a **Version:** header.
- Changes that alter invariants → **major version bump**.
- Changes that refine or clarify → **minor version bump**.
- Evolution documents may remain unversioned or use rolling versions.

---

### **3.2 Change‑Control Process**

Changes to core documents should note the rationale (in the commit message or
the document itself) and update cross‑references in the Threat Model or Roadmap
when they are affected. This keeps the documents from drifting apart.

---

### **3.3 Document Relationships**

```
GOVERNANCE_INDEX (this document)
   |
   |-- ARCHITECTURE v1.0  (defines what Relax is)
   |
   |-- THREAT_MODEL v1.1  (defines what can go wrong)
   |
   `-- HARDENING_ROADMAP (planned improvements)
```

Each document constrains the next:

- **Architecture** → constrains Threat Model
- **Threat Model** → constrains Roadmaps
- **Roadmaps** → drive future Architecture versions

This creates a **closed governance loop**.

---

## **4. Related Non‑Governance Artifacts**

`CLAUDE.md` and `AGENTS.md` (repository root) are contributor/agent instruction
files. They describe how to build, test, and modify the codebase, and they are
kept consistent with `ARCHITECTURE.md` — but they are working aids, not
governance documents, and are not versioned under the rules above.
