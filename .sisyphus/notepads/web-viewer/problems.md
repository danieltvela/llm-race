# Problems — Web Viewer

## F4 Scope Fidelity Check (2026-06-28)

- None blocking. Minor unresolved items:
  - `HEAD` requests to static files return 501; only `GET` is supported. This is acceptable for the current viewer but could be improved later.
  - CSV export includes a couple of extra columns (`tokens_per_second`, `total_tokens`) and uses `provider_name` rather than the spec's `provider` header. These deviations are small and do not affect functionality.
