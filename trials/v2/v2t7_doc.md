# Meridian 2.4 — release notes

Meridian 2.4 ships today for all workspace tiers. This release concentrates on
search quality, review workflows, and administrative visibility, based on the
most-requested items from the winter feedback cycle.

## Search

Search now indexes document body text in addition to titles and tags. Queries
return in under 300 ms at the 95th percentile on workspaces up to 100,000
documents, measured on our standard benchmark corpus. Operators for exact
phrases ("like this"), exclusion (-term), and author filters (from:name) work
in any combination. Results respect document permissions: users only ever see
documents they could already open.

## Review workflows

Documents can now require a named reviewer before publishing. A reviewer sees
a side-by-side diff of the draft against the last published version, can leave
inline comments anchored to paragraphs, and either approves or returns the
draft with a summary note. Authors are notified in-app and by email, and every
review decision is recorded in the document's history panel. Templates can
mark sections as review-required, so partial approvals are possible: a
returned draft keeps approvals for untouched sections.

## Administration

Workspace admins get a new activity view: sign-ins, permission changes,
publishing events, and export actions, filterable by user and date range, and
exportable as CSV. Retention for the activity view is 180 days on all tiers.
Seats can now be reassigned without deleting the departing user's documents;
ownership transfers to a nominated successor with the full edit history kept.

## Performance and fixes

Cold-start load time for large workspaces improved by roughly a third after
we moved sidebar hydration off the critical path. The editor no longer loses
an in-progress comment when the network drops mid-save; comments are queued
locally and retried. Fixed: table cells pasted from spreadsheets kept stray
styling; emoji reactions occasionally rendered twice in the history panel;
and the PDF export cut off footnotes on A4 paper sizes.

## Compatibility

Meridian 2.4 requires no migration steps. All 2.x integrations and API tokens
continue to work unchanged; the REST API adds two read-only endpoints
(/activity and /reviews) and deprecates nothing in this release. Self-hosted
customers can upgrade in place from any 2.x version; as always, we recommend
a database backup before upgrading.
