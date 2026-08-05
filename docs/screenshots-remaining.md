# Screenshots Strategy

## Deliverable Phase 1 (Blocked)

**Problem:** No X server available in CLI-only Hermes agent environment to invoke headful Chrome DevTools automation.

## Options

1. **Manual screenshots:** User opens Ágora dashboard locally (`http://dashboard:service?tab=agora`) and adds screenshots to a `demo/` folder:
   ```bash
   demo/
   ├── channels-view.png
   ├── message-compose.png
   ├── agent-rail.png
   ├── decision-view.png
   └── cost-dashboard.png
   ```

2. **Architecture diagram + CLI preview:** Generate SVG architecture diagrams of key flows (channels/messages/agent lifecycle) and include in `docs/architecture.md`.

3. **Video recording:** User records 30-second screen recordings of key screens and uploads to project repo.

## Action Required

Please choose:
- [ ] A — Add manual screenshots in `demo/` folder (paths needed: `.png`, `.mp4`)
- [ ] B — Add architecture diagrams + flow documentation
- [ ] C — Both A + B

Once you confirm, I can generate:
- 2-4 authentic screenshots of dashboard UI
- Optional: CLI-based mockup image (if you provide screenshot of Hermes dashboard for reference)