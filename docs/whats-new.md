# Maintaining Release Notes

The in-app What's New history reads `src/opentab/data/whats-new.json`, not this
document. Both frontends use the same bundled, offline content. User controls
are documented in [Keys and navigation](keys.md) and [Web](web.md).

## What To Include

Group short, user-facing changes under **New**, **Improved**, and **Fixed**.
Lead with what people can do: "Use OpenTab in your agent via MCP", not an
inventory of query types and interfaces. Hints should help someone try it.
Omit empty sections. A fix-only release is valid; there is no minimum number of
features or requirement for a headline, introduction, or promotional copy.

Include fixes users will notice: incorrect accounting, missing sessions,
crashes, or broken navigation. Explain changed numbers when relevant. Leave
internal refactors, dependency churn, and minor cosmetic changes to the full
GitHub notes. Describe the installed release, not later development work.

Each item requires plain-text `text`. Optional `availability` is `tui`, `web`,
or `both` (the default). Add a `hint` only when a short command or navigation
path helps discovery. Its `text` can accompany a `binding` with `context` and
`action`; the TUI resolves those through the user's current keymap.

## Releasing

1. Prepend a new entry to `releases` while updating `__version__` in
   `src/opentab/__init__.py`. Preserve every older entry; the history has no fixed
   retention limit.
2. Set the entry's `version`, `sections`, and official GitHub `release_url`. Commit
    the matching version and content together, and show the new in-app entry to Mo for
   approval. Reuse the summary when writing the full notes.
3. Run `python3 run_tests.py whats_new` and the normal checks. The resource test
   enforces that the installed release exists, versions are unique and links match;
   malformed or mismatched content is unavailable rather than shown for the wrong release.
4. Inspect the new entry and history navigation with `W` in both frontends,
   including an 80x24 terminal and a mobile browser. Keep notes concise enough to
   scan; let longer releases scroll.

## Announcements

The TUI queues a nonblocking hint after a known upgrade and the first paint,
without displacing existing startup notices. It says "Press W to see what's new"
(using the configured key) and stays visible for 10 seconds. An accent frame,
`NEW IN vX.Y.Z` label and highlighted shortcut distinguish it from ordinary
notifications. Opening the panel dismisses that toast, not other notices; the
announcement stays in notification history. It never opens the panel by itself.
Missing or invalid version history quietly establishes a baseline on normal exit;
equal versions and downgrades are silent. The last announced version is saved
with other preferences, preserving a newer marker from another process.

Demo and `--no-state` suppress automatic announcements and persistence. Manual
viewing still works. Headless CLI/MCP operations do not consume the announcement.
The browser is manual-only because viewing a report does not mean the viewer
upgraded OpenTab. No frontend polls for updates or downloads release notes; only
the explicit full-release action opens GitHub.
