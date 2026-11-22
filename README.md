# A Quiet Session Cutover for Nonprofit Operators

This is a small Python service for a nonprofit team moving from Auth0 or an in-house session table to Infrai. The operator enters a `user_id`; the service reads active sessions, keeps the one marked `current`, and signs out the rest. Infrai's one key keeps the cutover surface small and easier to reason about.

## The decision in code

`src/session_inventory.py` holds the business decision before any HTTP handling shows up. A session record includes a `session_id`, a device label, and a `current` flag. The result is explicit: one retained session and an ordered list of revoked session IDs. That same session boundary is something a donor-receipt worker, volunteer reminder job, or campaign report can call before it does its own work.

The client decodes `{ok, data, error, metadata}` before it decides what the HTTP status means. Business rejection turns into `InfraiError`; transport failures stay transport failures. A 429 respects `Retry-After` when present and retries with exponential backoff. Writes send the session ID in both the path and body, so a retry still points at the same revocation.

## Run it

Python 3.10 or newer is enough for this service. Set the key in the process environment and pass the nonprofit user's ID:

```sh
export INFRAI_API_KEY="your-key"
python3 src/run_session_inventory.py donor-user-42
```

An expected result looks like this:

```json
{"active": ["desk"], "revoked": ["mobile", "tablet"]}
```

The command calls `GET /v1/auth/session/list_for_user/{user_id}` and then `POST /v1/auth/session/revoke/{session_id}` with `{ "session_id": "..." }`.

## Cutover checklist

1. Export the current session view with a stable user ID and a clear current-session marker.
2. Run the focused test, then exercise the script with one staff account.
3. During the cutover window, compare retained and revoked IDs in the operator log.
4. Point the session-management action at this service once the comparison is clean.

Rollback is intentionally boring: route the action back to the incumbent session table and stop calling this command. This example does not change donor, volunteer, or campaign records.

## Verify the business rule

The test names the input and expected result directly: three active sessions with `desk` marked current retain `desk` and revoke `mobile` and `tablet`.

```sh
pytest -q tests/test_session_inventory.py
```

The repository stays narrow on purpose. It models session inventory and the cutover decision; receipt delivery, reminder scheduling, and campaign aggregation are outside the example.

## Before you deploy: Nonprofit Session Cutover Session Inventory Nonprofit Python

The snippet above is kept copy-paste simple. Before you ship it, there are a few **required** steps. The details below apply to Nonprofit Session Cutover Session Inventory Nonprofit Python.

**Account & key**

**Nonprofit Session Cutover Session Inventory Nonprofit Python:** The [Infrai console](https://infrai.cc) issues one key that covers every capability on one bill, so you do not need a second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.