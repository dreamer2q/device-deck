# Contributing to DeviceDeck

DeviceDeck is an independent downstream project. The original ai-phone history,
MIT copyright and third-party notices remain. Historical upstream contribution
guidance is retained in `CONTRIBUTING.upstream.md`; it does not define this
repository's contribution workflow or override its LICENSE.

Keep changes scoped and describe the user-visible behavior, device/platform
assumptions and validation. AI-assisted contributions are welcome with the same
review, attribution and testing expectations as other changes.

- Use Python 3.11 and Node 22+; run relevant backend tests, web Node tests and the
  web build. Isolate database tests from live environments.
- Preserve continuous-input ordering, cancellation and ownership checks. A
  connection authorized once must not retain input after its lease is revoked.
- Validate rotation and reconnect behavior before changing the scrcpy protocol.
  Keep versioned server binaries and their notices aligned with the client.
- Performance claims need the measurement boundary, raw samples, device/network
  configuration and limitations. A network RTT or decoder queue is not physical
  interaction latency.
- Never publish credentials, private device identities, runtime configurations or
  real-user screenshots. Use private local configuration and sanitized fixtures.
- Do not run CI against production device hosts or expose signing material to
  pull-request workflows. Live device tests require explicitly selected lab
  devices and their leases.
- Update the PRD/iteration and deployment documentation when changing the public
  interface or service configuration.
