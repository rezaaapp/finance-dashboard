# Settings Dirty State UX Refactor

## Background

The v0.9.3 Settings page mixed persistent configuration with immediate operations. A global Save Changes button made it unclear whether Google connection, source sync, invitations, and other already-executed actions still required saving.

## UAT Findings and UX Problems

- The global save action had no visible scope.
- Configuration fields did not show whether they differed from the server baseline.
- Leaving Settings could silently discard edits.
- Technical environment information appeared before user settings.

## New Dirty State Workflow

The page keeps the latest loaded/saved values as a baseline. Financial cycle, budgeting mode, privacy mode, and each insight threshold are compared field-by-field. A responsive floating footer appears only when at least one field differs and displays the exact modified-field count.

Save calls only the configuration endpoint groups that contain changes. General configuration sends only changed keys; insight thresholds retain their existing complete PUT contract when any insight field changes. A successful save updates both baselines, clears dirty state, hides the footer, and shows `Configuration saved successfully.`

Discard restores both forms from the latest baseline and immediately hides the footer.

## Configuration vs Immediate Actions

Dirty state includes only persistent form fields. Google connect/disconnect, source test/save, Sync Now, Reset Synced Data, workspace invitations, and local-dev Factory Reset execute immediately and are excluded from the dirty counter.

## Navigation Protection

`beforeunload` protects refresh and browser exit while dirty. Dashboard view navigation is routed through a guard that offers Stay, Discard Changes, and Save & Leave. No dialog appears when the dirty count is zero.

## Information Architecture

User configuration remains first, integrations and workspace controls follow, and development environment/factory reset controls move to the bottom. Developer information is rendered only when system metadata reports `local-dev`.

## Testing Summary

Pure utility tests cover unchanged/changed fields, changed-only payload construction, immediate-action exclusion, discard restoration, and navigation-warning activation. Frontend lint/build and the backend regression suite cover integration and Safe Reset/Import Transparency regressions.

## Future Enhancement

A future router migration can replace the Dashboard view-state navigation guard with a standard route-blocker API while retaining the same dirty-state utility and modal contract.
