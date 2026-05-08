feat(channel-runtime): proxy runtime APIs through executor manager

- Add unified proxy routes for message reads, agent listing, and collaboration requests
- Forward runtime calls to backend internal APIs with internal token and trace headers
- Keep session scope separated from tool payloads in the proxy boundary
- Cover executor-manager runtime proxy behavior with unittest cases
- Mark Phase 2 of the unified channel runtime tools plan complete
