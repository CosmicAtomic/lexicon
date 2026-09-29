# Performance & Reliability Report

**Scope:** `lexicon` (blogging API, cloned from `Aegis`), tested against a local
dev server on Windows. Covers contract testing, load testing, an end-to-end
flow test, and stress testing to find breaking points.

**Tools used:** Schemathesis (contract testing), Locust (load/stress
testing), pytest (E2E test).

---

## 1. Contract Testing (Schemathesis)

Ran against the OpenAPI schema for both `lexicon` and `aegis`'s auth/session
routes, using an authenticated hook to exercise protected endpoints rather
than only public ones.

**Finding:** several auth/session routes were missing documented response
schemas for `401`/`403` responses — the routes correctly *returned* those
statuses, but the OpenAPI schema didn't declare them, so
`response_schema_conformance` flagged a mismatch between actual and
documented behavior.

**Fix:** added explicit response models for `401`/`403` on the affected
routes in `lexicon`, then backported the same fix into `aegis` and tagged it
`v1.1`, so future clones inherit the corrected contract.

---

## 2. Load Testing (Locust)

Ramped from a 1-user smoke test up through 200 concurrent users, targeting
`POST /v1/auth/jwt/login` and `GET /v1/posts`.

| Users | Endpoint | Requests | Median (ms) | 95%ile (ms) | Failures |
|------:|----------|---------:|-------------:|-------------:|---------:|
| 1     | login    | 13       | 79           | 100          | 0        |
| 1     | posts    | 117      | 10           | 29           | 0        |
| 10    | login    | 31       | 7            | 2300         | 26       |
| 10    | posts    | 125      | 9            | 2100         | 0        |
| 50    | login    | 28       | 25           | 2100         | 28       |
| 50    | posts    | 183      | 15           | ~200         | 0        |
| 200   | login    | 45       | 21           | 2100         | 40       |
| 200   | posts    | 182      | 19           | 2100         | 0        |

*(Figures transcribed from handwritten test logs; treat as approximate —
exact Locust CSV exports would tighten precision if needed later.)*

**Observations:**

- **Login failures are the rate limiter working as designed**, not a bug.
  With a 5 requests/minute limit and 10-200 simulated users all hitting
  `/login`, the large majority of attempts correctly receive `429`.
- **Login's median latency (~7-79ms) is higher than a typical passthrough
  request** purely because of Argon2 password hashing, which is
  deliberately compute-expensive to resist brute-force attacks. A "slow"
  login is a sign of secure hashing, not a performance problem.
- **`/posts` 95%ile plateaus around 2100ms across every user count** (10,
  50, 200) rather than climbing progressively with load. A flat, high tail
  regardless of scale points toward a fixed-cost event — most likely
  intermittent DB connection creation/recycling in the pool — rather than
  load-driven degradation. Median stays low and healthy throughout,
  meaning most requests are unaffected; only a consistent minority hit the
  slow path.

---

## 3. End-to-End Test

One continuous test covering: signup → login → create post → fetch post →
create comment → webhook dispatch (mocked). Confirms the full user journey
works as a single connected flow, on top of the isolated integration tests.

---

## 4. Stress Testing — Finding the Breaking Points

Pushed well past expected real-world traffic (500-1000 concurrent users) to
find where and how the system fails.

### Single worker (`uvicorn app.main:app`)

| Users | Result |
|------:|--------|
| 500   | `/posts` began returning `500` errors — timeouts consistent with DB connection pool exhaustion under a single process. `/login` continued returning the expected `429`s from the rate limiter. |
| 1000  | Both endpoints began failing with `ConnectionRefusedError`. Uvicorn's terminal reported **"too many file descriptors in select()."** |

**Root cause:** Windows' default asyncio event loop uses a `select()`-based
implementation, which has a **hard limit of 512 monitored sockets** — a
constraint of the Windows API itself, not something app code or uvicorn
configuration can raise. Past that ceiling, the OS refuses new connections
outright, independent of application logic.

### Four workers (`uvicorn app.main:app --workers 4`)

| Users | Result |
|------:|--------|
| ~1000 | Failures shifted from `ConnectionRefusedError` to `sqlalchemy.exc.TimeoutError: QueuePool limit of size 5 overflow 10 reached, connection timed out, timeout 30.00`. |

**Interpretation — the key finding of the week:** adding workers didn't
just delay failure, it **moved the bottleneck**. Four independent
processes push the effective OS socket ceiling up (each process gets its
own ~512-socket budget), so the system tolerates more concurrent
connections before failing at that layer. But at roughly the same total
user count, a *different* constraint — the DB connection pool's fixed size
(5 base + 10 overflow, per process) — becomes the limiting factor instead.

This demonstrates a general lesson about scaling: **removing one
bottleneck exposes the next one downstream**, rather than removing the
ceiling entirely. Here, scaling workers shifted the constraint from the
OS/network layer to the database layer.

---

## 5. Recommendations (not yet implemented — noted for later weeks)

- Tune SQLAlchemy pool size / max overflow, and re-test to see whether the
  ~1000-user ceiling moves further out.
- Re-run this same stress test against a containerized/Linux target (Week
  8's Docker setup) to check whether the 512-socket Windows limitation
  disappears entirely off-platform — it's plausible this ceiling is
  Windows-specific and won't reproduce identically once deployed.
- This is the direct motivation for **Week 13-14** (scaling reads/writes,
  connection pooling tuning, load balancing across multiple instances) —
  a single process/machine, however configured, has a ceiling; horizontal
  scaling across machines is the actual long-term answer.

---

## Limitations of This Report

- All load/stress figures were transcribed from handwritten notes during
  testing; treat exact numbers as approximate rather than precise
  benchmarks.
- All testing was performed on a single Windows development machine
  against a local PostgreSql/dev database — results may differ meaningfully
  under Linux, containerized, or production-configured environments.