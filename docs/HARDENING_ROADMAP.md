# **Relax Hardening Roadmap**

_Version: 1.0 — Forward‑Looking Enhancements_  
_Status: Living_

This roadmap outlines **planned improvements** to Relax’s security posture, operational resilience, and supply‑chain integrity. Items here correspond to the mitigations labeled `[Planned]` in `THREAT_MODEL.md`, which documents the current posture and its gaps openly.

---

## **1. Container & Runtime Isolation Enhancements**

These items deepen the isolation guarantees already present in the architecture.

- **Add seccomp profile** — introduce a restrictive syscall filter tailored to FastAPI + Tesseract workloads.
- **Add AppArmor/SELinux policy** — enforce filesystem and process‑level constraints beyond Docker defaults.
- **Adopt distroless or minimal base images** — reduce attack surface by removing unused binaries and shells.
- **Introduce read‑only root filesystem** — ensure containers cannot modify their own runtime environment.

---

## **2. OCR & Image‑Processing Safety Enhancements**

These items strengthen the defenses around the highest‑risk part of the system: image parsing and OCR.

- **Expand decompression‑bomb guards** — add megapixel, DPI, and color‑complexity checks after OpenCV decode.
- **Enforce single‑threaded OCR explicitly** — ensure Tesseract never spawns additional worker threads.
- **Add OCR runtime limits** — enforce CPU‑time and memory ceilings at the container level.
- **Introduce adversarial‑image detection heuristics** — detect malformed or intentionally complex images before OCR.

---

## **3. Supply‑Chain & Build Integrity Enhancements**

These items ensure deterministic, verifiable builds and reduce dependency risk.

- **Pin all Docker base images by digest** — guarantee reproducible builds and prevent upstream drift.
- **Pin Python wheels and system libraries** — ensure OpenCV/Tesseract versions remain stable across deployments.
- **Add automated image scanning** — integrate Trivy/Grype scanning into CI.
- **Introduce SBOM generation** — produce a Software Bill of Materials for each release.

---

## **4. Edge & API Boundary Enhancements**

These items strengthen the public interface without revealing any current weaknesses.

- **Add request‑rate anomaly detection** — detect unusual traffic patterns beyond simple per‑IP quotas.
- **Introduce structured error telemetry** — improve observability for unexpected failures.
- **Add optional CAPTCHA for abuse spikes** — enable only during elevated threat periods.
- **Enhance Caddy security headers** — periodically review CSP, Permissions‑Policy, and HSTS settings.

---

## **5. Data & Logging Enhancements**

These items improve auditability and privacy without exposing sensitive operational details.

- **Add log‑rotation and retention policy** — ensure request logs remain bounded and manageable.
- **Introduce structured log schema** — standardize fields for easier analysis.
- **Add optional encrypted log export** — allow secure off‑host log review when needed.
- **Add integrity checks for SQLite files** — verify log and rate‑limit DB consistency.

---

## **6. Operational Resilience Enhancements**

These items improve reliability and make the system more robust under load.

- **Add health‑based autoscaling hooks** — prepare for future scaling scenarios. _Note: this would require re‑architecting shared state first — rate limits, request logs, and concurrency caps are currently per‑host SQLite/in‑process, and `ARCHITECTURE.md` assumes no multi‑host deployment._
- **Introduce synthetic monitoring** — periodic end‑to‑end checks of extraction flow.
- **Add graceful‑degradation modes** — e.g., temporarily disable annotated PNG generation under high load.
- **Document SLOs and capacity envelope** — formalize expected performance and load boundaries.
