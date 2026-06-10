# Relax Threat Model 

_Version: 1.1 — Threat Model_  
_Status: Stable_

## 1. Scope and assumptions

**Scope:**
- **In-scope:** Public Relax web app, Caddy, backend FastAPI service, OCR/image pipeline (OpenCV + Tesseract), SQLite, Docker containers, Cloudflare edge.
- **Out-of-scope (for v1):** Cloudflare internals, user devices, ISP networks, OS/hypervisor of the host, CI/CD system (covered only at supply-chain level).

**Core assumptions:**
- **[Implemented]** All user uploads are treated as **fully untrusted**.
- **[Assumed]** OpenCV/Tesseract and their dependencies are **memory-unsafe** and may contain 0-days.
- **[Assumed]** Cloudflare and Caddy are correctly configured and not malicious.
- **[Assumed]** Host OS and container runtime are not compromised.

## 1.1 Mitigation status labels

Each mitigation is labeled so the model distinguishes current controls from future work:

- **[Implemented]** Currently active in code, config, deployment, or documented operation.
- **[Planned]** Not active yet; tracked in `HARDENING_ROADMAP.md`.
- **[Assumed]** Environmental or operational condition outside Relax’s direct enforcement.

---

## 2. Primary assets

**User-facing assets**
- **A1: Service availability** — Relax remains responsive and stable.
- **A2: Output integrity** — OCR results are correct or fail safely (no silent corruption).
- **A3: User trust** — No obvious compromise, defacement, or data leak.

**Backend assets**
- **B1: Backend execution environment** — Python process, OpenCV/Tesseract, container FS.
- **B2: SQLite database** — Rate-limit data, logs, minimal metadata.
- **B3: Configuration & secrets** — `REQUEST_LOG_SALT`, the Cloudflare Origin certificate and private key, and other environment variables.

**Infrastructure assets**
- **C1: Host machine** — OS, other containers, Docker daemon.
- **C2: Network perimeter** — Cloudflare config, Caddy config, TLS keys.
- **C3: Build artifacts** — Docker images and application/system dependencies.

---

## 3. Trust boundaries

**TB1: Internet → Cloudflare**
- Untrusted clients, arbitrary HTTP.

**TB2: Cloudflare → Caddy**
- Cloudflare is semi-trusted; Caddy must resolve the real client IP only from trusted proxy ranges.

**TB3: Caddy → Backend**
- Caddy enforces upload size limits, TLS, and response security headers. Application-level rate limiting lives in FastAPI/SQLite, with optional Cloudflare rules.

**TB4: Backend → OCR libraries**
- Python (managed) → C libraries (unmanaged, memory-unsafe).

**TB5: Backend → SQLite**
- Application → data store; SQL injection and data integrity concerns.

**TB6: Build system → Runtime**
- CI/build → deployed images; supply-chain and artifact integrity.

---

## 4. STRIDE by major component

### 4.1 Edge & routing (Cloudflare + Caddy)

**Spoofing**
- **Risk:** Spoofed client IPs via misused headers.
- **Mitigation:** **[Implemented]** Caddy resolves `{client_ip}` using configured Cloudflare trusted proxy ranges and forwards it to the backend as `X-Real-IP`. The backend trusts this header unconditionally; the guarantee comes from network isolation (no published backend port, so only Caddy can reach it), not from header validation.

**Tampering**
- **Risk:** HTTP request manipulation in transit.
- **Mitigation:** **[Implemented]** TLS terminates at Cloudflare and Caddy uses Cloudflare Origin TLS in production; Caddy and FastAPI perform normal HTTP parsing.

**Repudiation**
- **Risk:** Attackers deny abusive traffic.
- **Mitigation:** **[Implemented]** Cloudflare/Caddy access logs and backend SQLite request logs record timing, status, and hashed client IPs. **[Planned]** Add request IDs for cross-log correlation.

**Information disclosure**
- **Risk:** Misconfigured TLS or headers leaking internal info.
- **Mitigation:** **[Implemented]** HSTS, response security headers, `Server` header removal, and generic backend 500 responses.

**Denial of service**
- **Risk:** Volumetric attacks, slowloris, large uploads.
- **Mitigation:** **[Implemented]** Caddy upload size caps and FastAPI rate/concurrency limits. **[Assumed]** Cloudflare absorbs volumetric traffic. **[Planned]** Add optional Cloudflare rules for burst control.

**Elevation of privilege**
- **Risk:** None directly at this layer (no code execution), but misconfig could expose backend directly.
- **Mitigation:** **[Implemented]** Backend has no published Docker port. **[Assumed]** Host firewall restricts direct origin access to Cloudflare/Caddy paths.

---

### 4.2 Backend API (FastAPI app)

**Spoofing**
- **Risk:** Forged internal calls pretending to be edge.
- **Mitigation:** **[Implemented]** Backend is exposed only on the Docker network. **[Planned]** Add a shared secret or stronger network policy if future internal callers are introduced.

**Tampering**
- **Risk:** Malicious request bodies, parameters.
- **Mitigation:** **[Implemented]** Explicit date parsing, bounded upload reads, image decode validation, dimension validation, and no dynamic eval.

**Repudiation**
- **Risk:** Attackers deny sending abusive requests.
- **Mitigation:** **[Implemented]** Backend request logging stores salted IP hash, processing time, status, success flag, and error detail. **[Planned]** Add request IDs and richer request metadata.

**Information disclosure**
- **Risk:** Error messages leaking stack traces or internal paths.
- **Mitigation:** **[Implemented]** Unexpected exceptions return generic 500 messages while details stay server-side; expected extraction failures return user-facing 422 messages.

**Denial of service**
- **Risk:** High concurrency, slow requests, large bodies.
- **Mitigation:** **[Implemented]** `_MAX_INFLIGHT` cap, OCR semaphore, `file.read(MAX_UPLOAD_BYTES + 1)`, rate limiting, extraction timeout, and backend memory limit. **[Planned]** Add explicit CPU limits.

**Elevation of privilege**
- **Risk:** Exploiting Python or framework bugs to escape app logic.
- **Mitigation:** **[Implemented]** Backend runs as non-root, with dropped capabilities and no dynamic plugin loading. **[Planned]** Further reduce runtime tooling and base-image footprint.

---

### 4.3 Image parsing & OCR (OpenCV + Tesseract)

**Spoofing**
- **Risk:** Crafted images pretending to be benign formats.
- **Mitigation:** **[Implemented]** PNG/JPEG header parsing where possible, OpenCV decode, decompression-bomb pixel guard, and final resolution validation.

**Tampering**
- **Risk:** Malicious images causing memory corruption, arbitrary writes.
- **Mitigation:** **[Implemented]** OCR runs in a non-root, capability-dropped backend container with strict upload byte and image pixel/dimension limits. **[Planned]** Add read-only root filesystem and DPI/complexity checks.

**Repudiation**
- **Risk:** Hard to attribute which image caused a crash.
- **Mitigation:** **[Implemented]** Backend logs request outcome and error detail. **[Planned]** Add request IDs and image metadata such as decoded dimensions and format.

**Information disclosure**
- **Risk:** OCR engine reading unintended files if path-based APIs used.
- **Mitigation:** **[Implemented]** Uploaded screenshots are decoded in memory and passed through the in-memory extraction path. **[Planned]** Tighten filesystem policy for OCR support files.

**Denial of service**
- **Risk:** OOM or CPU exhaustion from decompression bombs or adversarial images.
- **Mitigation:** **[Implemented]** Decompression-bomb guard, 1 MB upload limit, backend memory limit, OCR concurrency cap, and extraction timeout. **[Planned]** Explicitly enforce single-threaded OCR and CPU-time ceilings.

**Elevation of privilege**
- **Risk:** RCE via C library exploit → code execution in container.
- **Mitigation:** **[Implemented]** Non-root user, `no-new-privileges`, dropped capabilities, no Docker socket mount, and host/container isolation. **[Planned]** Add no-outbound-network policy and a read-only/minimal writable filesystem.

---

### 4.4 Data layer (SQLite)

**Spoofing**
- **Risk:** Fake identity in rate-limit keys (e.g., IP spoofing upstream).
- **Mitigation:** **[Implemented]** Rate-limit identity comes from `X-Real-IP` set by Caddy after trusted-proxy resolution. **[Planned]** Consider additional keys if auth or sessions are added later.

**Tampering**
- **Risk:** SQL injection, log manipulation.
- **Mitigation:** **[Implemented]** Parameterized queries only, no dynamic SQL, and database files owned by the app user in `/data`.

**Repudiation**
- **Risk:** Attackers deny having hit rate limits or triggered guards.
- **Mitigation:** **[Implemented]** Request log rows include timestamps, salted IP hashes, status, success flag, timing, and error detail. **[Planned]** Add request IDs.

**Information disclosure**
- **Risk:** Logs leaking sensitive data.
- **Mitigation:** **[Implemented]** Do not store raw images, OCR text, or raw IPs; store hashed IPs, timing, status, success, and error detail only. **[Planned]** Add a retention policy.

**Denial of service**
- **Risk:** DB lock contention, file corruption.
- **Mitigation:** **[Implemented]** Low write volume, short-lived SQLite connections, and WAL mode. **[Planned]** Add integrity checks and retention/rotation.

**Elevation of privilege**
- **Risk:** Using SQLite features (e.g., ATTACH) to access other files.
- **Mitigation:** **[Implemented]** No user-controlled SQL, no `ATTACH`, and no extension loading in application code.

---

### 4.5 Containers, host, and supply chain

**Spoofing**
- **Risk:** Malicious image pretending to be a trusted base.
- **Mitigation:** **[Planned]** Pin image digests, verify SHA256, and use trusted registries.

**Tampering**
- **Risk:** Compromised base image or dependency.
- **Mitigation:** **[Implemented]** Build avoids `curl | bash`. **[Planned]** Add Trivy/Grype scans, pinned dependency versions, pinned image digests, and smaller runtime images.

**Repudiation**
- **Risk:** No trace of what image/version was deployed.
- **Mitigation:** **[Planned]** Tag images with immutable IDs and record image digests in deployment logs.

**Information disclosure**
- **Risk:** Secrets baked into images or logs.
- **Mitigation:** **[Implemented]** Secrets/configuration come from environment variables or mounted cert files; `.env` and certs are not committed. **[Planned]** Add log scrubbing checks if richer logs are introduced.

**Denial of service**
- **Risk:** Host resource exhaustion from multiple containers.
- **Mitigation:** **[Implemented]** Backend has a memory limit. **[Planned]** Add CPU limits and host-level monitoring.

**Elevation of privilege**
- **Risk:** Container escape to host.
- **Mitigation:** **[Implemented]** App containers run non-root, capabilities are dropped, Caddy gets only `NET_BIND_SERVICE`, and no Docker socket is mounted. **[Planned]** Add rootless Docker, custom seccomp, and AppArmor/SELinux policy.

---

## 5. Key invariants derived from the threat model

These are the “constitutional” rules that fall out of the analysis:

1. **All OCR runs must execute as a non-root user in a capability-dropped container.**  
2. **[Assumed] No request bypasses Cloudflare + Caddy to reach the backend directly from the internet.** Relax cannot enforce this from inside the repo: it depends on the backend having no published port (implemented), plus the origin firewall and Cloudflare proxying (environmental — see P3).  
3. **No upload may exceed the configured byte limit at either Caddy or FastAPI.**  
4. **No image may exceed implemented byte, pixel, or resolution limits before OCR.**  
5. **No SQL may be constructed via string concatenation; parameters only.**  
6. **No `shell=True`, user-controlled command construction, or dynamic code loading is allowed in the backend.**  
7. **No container may run with `privileged: true`; application containers must not add Linux capabilities, and the edge proxy may add only `NET_BIND_SERVICE` to bind ports 80/443.**

Planned hardening goals that are not yet invariants:

1. **Pin Docker base images by digest and pin Python/system dependencies for reproducible builds.**
2. **Add DPI/complexity checks, explicit OCR thread limits, CPU limits, and read-only/minimal writable filesystems.**

---

## 6. Prioritized risk list (v1)

**P1: OCR-layer memory corruption / RCE (Elevation of privilege, Tampering, DoS)**  
- **Why:** Highest-risk code (C libraries, complex formats, untrusted input).  
- **Mitigations:** **[Implemented]** Non-root, dropped caps, strict byte/pixel/resolution guards, memory limit, OCR concurrency cap. **[Planned]** Explicit single-threaded OCR and supply-chain pinning.

**P2: Resource exhaustion via crafted uploads (DoS)**  
- **Why:** Direct impact on availability; easy to attempt.  
- **Mitigations:** **[Implemented]** Edge upload caps, bounded `file.read`, decompression-bomb guard, concurrency limits, timeout, and backend memory cap.

**P3: Misconfiguration exposing backend directly (Spoofing, DoS, Elevation)**  
- **Why:** Bypasses Cloudflare/Caddy protections.  
- **Mitigations:** **[Implemented]** Backend has no published host port. **[Assumed]** Origin firewall restricts direct access. **[Planned]** Add infra-as-code checks.

**P4: Supply-chain compromise (Tampering, Elevation)**  
- **Why:** Single compromised base image or wheel can subvert all other defenses.  
- **Mitigations:** **[Planned]** Pinned digests, dependency pinning, scanning, trusted registries, and minimal images.

**P5: Logging/observability gaps (Repudiation, delayed detection)**  
- **Why:** Harder to investigate incidents or tune defenses.  
- **Mitigations:** **[Implemented]** Backend SQLite request log and Caddy JSON access logs. **[Planned]** Correlation IDs, richer structured metadata, and bounded retention.
