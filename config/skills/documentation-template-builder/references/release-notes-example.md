# RELEASE-004: v2.3.0 — Real-Time Collaboration

**Status:** ✅ Released  
**Release Date:** May 20, 2026  
**Type:** RELEASE (Release Notes)  
**Affects:** All users on Pro and Teams tiers

---

## Summary

v2.3.0 ships real-time collaborative editing — the most-requested feature from our enterprise customers. Multiple teammates can now edit the same document simultaneously with live cursors and instant conflict resolution. This release also includes a 40% improvement to search speed and fixes three critical bugs reported in the last two weeks.

---

## What's New

### Real-Time Collaborative Editing
Multiple users can now edit a document at the same time. Changes appear instantly (<200ms) with no manual refresh. Each user gets a color-coded cursor so you always know who's editing what.  
→ [Setup guide](docs/GUIDE-012-REALTIME_COLLAB.md)

### Live Presence Indicators
See who's currently in a document: their avatar, name, and edit position appear in the top-right corner. Users who go inactive for 30 seconds are dimmed automatically.

### Conflict Resolution UI
When two users edit the same line simultaneously, the merge preview modal shows both versions side by side. Choose which to keep — or manually combine them. All merge decisions are logged in the change history.  
→ [How conflict resolution works](docs/GUIDE-013-CONFLICT_RESOLUTION.md)

---

## Improvements

- **Search:** Full-text search results now load 40% faster (trigram index upgrade; no action required)
- **Session restore:** Documents reopen to your last cursor position instead of the top of the file
- **Mobile:** Pinch-to-zoom now works reliably on iPad Safari (regression introduced in v2.1.0)
- **Accessibility:** All new collaboration UI elements have ARIA labels and keyboard navigation

---

## Bug Fixes

| Issue | Affected users | Severity |
|-------|---------------|----------|
| Document autosave silently failed when offline; data appeared saved but wasn't | All users on Safari | Critical |
| Clicking "Share" on a read-only document showed an incorrect "Edit access granted" toast | Users on Free tier | High |
| Search returned duplicate results when a document was renamed mid-session | Power users with large workspaces | Medium |

---

## Breaking Changes

> ⚠️ **Action required if you use the Documents API**

**API:** `GET /api/v1/documents/{id}/collaborators` now returns `{ users: [...] }` instead of a bare array. Update your API client before upgrading.

```python
# Before (v2.2.x)
collaborators = response.json()  # was a list

# After (v2.3.0)
collaborators = response.json()["users"]  # now wrapped
```

→ [Full migration guide](docs/GUIDE-014-V2_3_MIGRATION.md)

**Webhook:** The `document.updated` webhook payload now includes a `collaboration_session_id` field. Existing consumers can safely ignore it — no breaking change — but you may want to use it for audit logging.

---

## Upgrade Notes

**SaaS users:** No action required. v2.3.0 is deployed automatically.

**Self-hosted users:**
```bash
pip install --upgrade nova-agent==2.3.0
nova migrate          # applies one new DB migration: adds document_edits table
nova verify           # runs health checks; should print "OK" for all checks
```

The migration adds one table (`document_edits`) and one index. On a 10GB database it takes approximately 30 seconds with no downtime.

---

## Known Issues

| Issue | Workaround | Fix target |
|-------|------------|-----------|
| Conflict resolution modal occasionally renders behind the sidebar on Firefox 124 | Press Escape and reopen the modal | v2.3.1 (May 27) |
| Live cursors don't appear in read-only shared links (viewers can't be seen by editors) | Upgrade viewer to Pro for full presence | v2.4.0 |

---

## What's Next

v2.3.1 (May 27) — Firefox rendering fix + performance patch for large documents (>500KB)  
v2.4.0 (June) — Comments and inline annotations, version history UI

---

## Related Documentation

| Document | Purpose |
|----------|---------|
| [RELEASE-003 v2.2.0](RELEASE-003-v2_2_0.md) | Previous release |
| [GUIDE-012 Real-Time Collab Setup](GUIDE-012-REALTIME_COLLAB.md) | Setup and usage guide for the new feature |
| [GUIDE-014 v2.3 Migration Guide](GUIDE-014-V2_3_MIGRATION.md) | API upgrade instructions |
| [CHANGELOG.md](../../CHANGELOG.md) | Full version history |
