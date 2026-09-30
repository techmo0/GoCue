# Contextual Intent Engine (CIE)

## Product & Engineering Specification

**Goal:** Store intentions, not reminder times. Surface an intention
when the user's real-world context makes it actionable.

**MVP:** mobile-first, local-first, no LLM, no backend.

## 1. Core product loop

User adds `Buy toilet paper` and associates it with `MY_SUPERMARKET`.

A raw geofence entry does not immediately notify. After the phone
determines that the user genuinely stopped at the supermarket, the
engine surfaces all matching active intents together:

``` text
🛒 SUPERMARKET
□ Toilet paper
□ Milk
□ Batteries
```

User completes items or chooses `Remind next visit`.

``` text
INTENT + CONTEXT + REAL-WORLD SIGNALS
→ ACTIONABLE NOW
→ NOTIFICATION
```

The product succeeds when the user can state something once, forget it,
and have it return at the useful physical moment.

## 2. Principles

-   **Intent-first:** primary object is an intent, not a scheduled
    reminder.
-   **Semantic contexts:** use `SUPERMARKET`, `MY_SUPERMARKET`,
    `PHARMACY`, etc.; intents should not depend directly on coordinates.
-   **Explicit choice wins:** explicit selection \> learned preference
    \> nearest-place fallback.
-   **Local-first:** no account/cloud/LLM needed for MVP.
-   **Quiet by default:** minimize false positives and duplicate
    notifications.
-   **Explainable:** keep enough events to explain why something fired.

## 3. MVP scope

Implement:

-   create/edit/delete intents;
-   `ACTIVE`, `COMPLETED`, `ARCHIVED`;
-   semantic place requirements;
-   physical place management;
-   manually configured `MY_SUPERMARKET`;
-   background geofencing;
-   candidate/confirmed visits;
-   grouped notifications;
-   complete intent;
-   `Remind next visit`;
-   visit-level notification deduplication;
-   persistent event log;
-   debug/simulation screen.

Do NOT implement yet:

-   route optimization / Errand Compiler routing;
-   LLM/NLP classification;
-   temporary-home inference;
-   weather/calendar integration;
-   object tracking;
-   cloud sync;
-   opening-hours lookup;
-   generic rules DSL;
-   automatic place discovery.

## 4. Domain model

Core objects:

``` text
Intent
Requirement
Place
SemanticPlace
Visit
Suppression
Event
ContextSnapshot
```

### Intent

``` text
id
title
status: ACTIVE | COMPLETED | ARCHIVED
createdAt
completedAt?
```

Temporary suppression is not an intent status.

### Requirement

MVP:

``` text
type: PLACE_ROLE | SEMANTIC_PLACE
operator: EQUALS
value: SUPERMARKET | MY_SUPERMARKET | ...
```

Future types may include `TIME_WINDOW`, `PLACE_OPEN`, `MOVEMENT`,
`DEADLINE`, `CARRYING_OBJECT`, `WEATHER`, `DEVICE_STATE`.

Use pluggable requirement evaluators.

### Place

``` text
id
name
latitude
longitude
radiusMeters
role
source
createdAt
updatedAt
```

Initial roles: `HOME`, `SUPERMARKET`, `PHARMACY`, `GYM`, `POST_OFFICE`,
`HARDWARE_STORE`, `WORK`, `CUSTOM`.

### Semantic places

``` text
MY_SUPERMARKET
MY_PHARMACY
MY_GYM
MY_DHL
PERMANENT_HOME
CURRENT_HOME
TEMPORARY_HOME
```

These aliases resolve to physical places. Changing `MY_SUPERMARKET` must
not require editing all grocery intents.

### Visit

``` text
id
placeId
state: CANDIDATE | CONFIRMED | ENDED
enteredAt
confirmedAt?
exitedAt?
```

### Suppression

MVP supports `UNTIL_NEXT_VISIT`, scoped to a visit rather than a timer.

## 5. Mandatory architecture boundary

**Intent logic must never directly consume GPS.**

``` text
OS location/geofence APIs
        ↓
Presence Engine
        ↓
Context Snapshot
        ↓
Requirement Evaluators
        ↓
Intent Engine
        ↓
Eligible Intents
        ↓
Notification Coordinator
```

Good: `Buy toilet paper requires MY_SUPERMARKET`.

Bad: intent directly stores a latitude/longitude condition.

## 6. Suggested implementation

Prefer native mobile development.

**iOS:** Swift + SwiftUI + Core Location + UserNotifications +
SwiftData/Core Data/SQLite.

**Android:** Kotlin + Jetpack Compose + Android Geofencing API + Room +
notification APIs.

Logical modules:

``` text
App
├── Domain
├── Persistence
├── Location
│   ├── GeofenceManager
│   ├── PresenceEngine
│   └── PlaceResolver
├── Engine
│   ├── ContextSnapshot
│   ├── RequirementEvaluator
│   └── IntentEvaluator
├── Notifications
└── UI
```

No backend for MVP.

## 7. Persistence proposal

Equivalent native models are fine.

``` sql
Intent(id, title, status, created_at, completed_at);
Requirement(id, intent_id, type, operator, value);
Place(id, name, latitude, longitude, radius_meters, role, source, created_at, updated_at);
SemanticPlaceBinding(semantic_name, place_id, source, confidence);
PlaceVisit(id, place_id, state, entered_at, confirmed_at, exited_at);
IntentSuppression(intent_id, mode, visit_id, created_at);
Event(id, type, timestamp, payload_json);
```

Add foreign keys and indexes.

## 8. Event model

Initial events:

``` text
INTENT_CREATED
INTENT_COMPLETED
INTENT_ARCHIVED
PLACE_CREATED
PLACE_UPDATED
PREFERRED_PLACE_CHANGED
PLACE_ENTERED
PLACE_DWELL_CONFIRMED
PLACE_EXITED
NOTIFICATION_SENT
NOTIFICATION_OPENED
NOTIFICATION_DISMISSED
INTENT_SUPPRESSED_UNTIL_NEXT_VISIT
```

Full event sourcing is unnecessary; this log is mainly for
observability, debugging and explanation.

## 9. ContextSnapshot

Evaluation consumes normalized state, not raw sensor callbacks.

``` json
{
  "place": {
    "id": "place_123",
    "roles": ["SUPERMARKET"],
    "semanticNames": ["MY_SUPERMARKET"]
  },
  "presence": {
    "state": "CONFIRMED",
    "visitId": "visit_456",
    "dwellSeconds": 75
  },
  "movement": {
    "speedMetersPerSecond": 0.4
  }
}
```

Future fields can be appended without changing `Intent`.

## 10. Intent Engine

Conceptual API:

``` text
evaluate(activeIntents, contextSnapshot) -> eligibleIntents
```

Algorithm:

``` text
for each ACTIVE intent:
    if suppressed for current visit:
        skip
    if all requirements match:
        mark eligible

group eligible intents by actionable place/context

if group was not already surfaced during this visit:
    request one grouped notification
```

Initial evaluators: `PlaceRoleEvaluator`, `SemanticPlaceEvaluator`.

The engine must be deterministic and heavily unit-tested.

## 11. Presence Engine

Highest-risk subsystem. It answers: **is the user genuinely able to act
here?**

MVP state machine:

``` text
OUTSIDE
  │ geofence enter
  ▼
CANDIDATE
  │ dwell threshold
  ▼
CONFIRMED
  │ geofence exit
  ▼
OUTSIDE
```

Never notify immediately on raw geofence entry.

MVP confirmation:

``` text
inside geofence AND dwell >= threshold
```

Use a configurable dwell threshold, initially perhaps 30--90 seconds.

Later:

``` text
inside geofence
AND dwell >= threshold
AND speed < threshold
AND acceptable location accuracy
```

Future signals can include activity recognition, Wi-Fi and visit
history. No ML is required.

## 12. Preferred supermarket

MVP:

``` text
Settings → Places → Add/select place
→ Role: SUPERMARKET
→ Use as MY_SUPERMARKET
```

Store:

``` text
MY_SUPERMARKET → place_123
```

Distinguish:

``` text
Buy toilet paper → MY_SUPERMARKET
Buy emergency water → generic SUPERMARKET
```

## 13. Home model --- future, design now

Reserve:

``` text
PERMANENT_HOME
CURRENT_HOME
TEMPORARY_HOME
```

Normally `CURRENT_HOME = PERMANENT_HOME`.

Future heuristic can infer a temporary home from overnight stationary
location clusters. When `CURRENT_HOME` changes, home-relative places can
be resolved again:

``` text
CURRENT_HOME changed
→ resolve preferred/nearest supermarket
→ MY_SUPERMARKET may change
→ existing grocery intents remain unchanged
```

Inference must be transparent and manually overrideable.

Future resolution policy:

``` text
explicit MY_SUPERMARKET
> learned frequently visited supermarket near CURRENT_HOME
> nearest supermarket to CURRENT_HOME
```

Never silently override explicit choice.

## 14. Intent creation UX

Target: common intent in roughly 2--3 seconds.

``` text
What do you need to do?
[ Buy toilet paper ]

Where should this become relevant?
[ Supermarket ]
[ Pharmacy ]
[ Post office ]
[ Home ]
[ Choose place ]
```

Do not require date, time, priority, recurrence, project, tags or notes.

Later add widgets, shortcuts, share sheet and system voice integration.

## 15. Classification without LLMs

MVP: user selects context.

Later keep a local learned dictionary:

``` text
toilet paper → SUPERMARKET
milk         → SUPERMARKET
ibuprofen    → PHARMACY
```

A possible model is
`IntentTemplate(normalizedText, defaultRequirementType, defaultRequirementValue)`.

## 16. Notification behavior

Group matching intents into one notification:

``` text
🛒 SUPERMARKET
□ Toilet paper
□ Milk
□ Batteries
```

Desired actions: `OPEN LIST`/`DONE`, `REMIND NEXT VISIT`.

Individual item completion directly in the notification is optional for
MVP.

## 17. Remind Next Visit

It must:

1.  keep intent `ACTIVE`;
2.  suppress it for current `visitId`;
3.  prevent more notifications during current visit;
4.  expire/clear visit suppression after exit;
5.  allow notification during a later confirmed visit.

Do not implement as `snooze 1 hour`. The semantic unit is the visit.

## 18. Deduplication

-   one contextual notification per relevant intent group per confirmed
    visit;
-   reevaluation during same visit must not repeatedly notify;
-   completed intents disappear;
-   process/app restart must preserve visit-level deduplication;
-   define deterministic behavior for an intent created while already
    inside a matching place.

## 19. Debugging UI

Build early. Show:

``` text
Current semantic context
Current/last physical place
Presence state
Current visit ID
Geofence state
Active intents
Eligible intents
Suppressions
Recent events
Last notification reason
```

Development-only controls:

``` text
ENTER place
CONFIRM dwell
EXIT place
```

Most engine development should not require physically visiting a store.

## 20. Required tests

Engine:

-   `MY_SUPERMARKET` + active grocery intent → eligible;
-   home + grocery intent → not eligible;
-   wrong supermarket + requires `MY_SUPERMARKET` → not eligible;
-   another supermarket + generic `SUPERMARKET` → eligible;
-   completed intent → never eligible;
-   suppressed current visit → not eligible;
-   later visit → eligible again.

Visit/deduplication:

-   raw enter → no notification;
-   confirmed dwell → notification;
-   reevaluate same visit → no duplicate;
-   exit + new confirmed visit → may notify again;
-   `REMIND NEXT VISIT` → silence current visit, eligible next visit.

Persistence:

-   process killed during confirmed visit → no duplicate after restore;
-   completed intent survives restart;
-   semantic binding survives restart.

Edge cases:

-   poor GPS accuracy;
-   driving past;
-   geofence-border oscillation;
-   overlapping places;
-   preferred-place changes;
-   location permission revoked;
-   notifications disabled;
-   device reboot;
-   referenced place deleted;
-   intent added while already at matching place.

## 21. Permissions and privacy

Explain background location before requesting it.

Suggested copy:

> CIE uses background location to surface an intent when you arrive at a
> relevant place. In the initial version, location-related data stays on
> this device.

Degraded modes:

-   no background location → intent management still works, background
    triggering unavailable;
-   notifications disabled → show clear remediation;
-   approximate location only → continue where possible and expose
    reduced reliability.

Privacy:

-   local storage by default;
-   avoid continuous GPS history when visit/geofence events suffice;
-   store only necessary data;
-   allow deletion of places, visits, events and intents;
-   future inferred home state must be transparent.

## 22. Future extensions that fit CIE

-   **Opening hours:** surface only when relevant place is open.
-   **Deadline fallback:** try opportunistically first; escalate to
    normal reminder when deadline approaches.
-   **Carry constraints:** `Return package` requires `MY_DHL` and
    `PACKAGE_WITH_ME`.
-   **Enter/leave contexts:** e.g. take trash when leaving home.
-   **Dynamic home:** travel changes `CURRENT_HOME`; home-relative
    places re-resolve.
-   **Any-of places:** toothpaste can be bought at supermarket OR
    drugstore.
-   **Non-location contexts:** call dentist when weekday + office
    hours + free quiet interval.
-   **Errand Compiler:** later module can look ahead at known trips and
    find cheap opportunities; it should consume CIE intents rather than
    replace CIE.

## 23. Explicit non-goals for V0

Do not turn V0 into:

-   a generic todo manager;
-   a calendar;
-   a route planner;
-   a shopping-price app;
-   an AI assistant;
-   a generic IFTTT clone.

First prove:

``` text
I state what I need once
→ I forget about it
→ at the useful physical moment it comes back
→ I do it
→ it disappears
```

## 24. Implementation order

### Milestone 0 --- pure domain prototype

Models, repositories/interfaces, requirement evaluators, intent
evaluator, visit suppression and unit tests. No GPS.

### Milestone 1 --- simulated end-to-end

Minimal UI plus simulated enter/dwell/exit. Verify grouping and
deduplication.

### Milestone 2 --- one real geofence

One manually configured `MY_SUPERMARKET`; wire OS callbacks into
Presence Engine.

### Milestone 3 --- harden real-world behavior

Tune dwell, process death/relaunch, permission changes, duplicate
prevention and battery behavior.

### Milestone 4 --- multiple places/roles

Pharmacy, post office, custom places; generic role vs preferred semantic
place.

### Milestone 5 --- fast capture

Local learned templates and OS quick-add entry points.

Only then consider automatic home/place inference.

## 25. MVP acceptance criteria

1.  User can configure `MY_SUPERMARKET`.
2.  User can add `Buy toilet paper` associated with it.
3.  Merely passing the store normally does not alert.
4.  A genuine visit reliably surfaces the intent.
5.  Multiple grocery intents are grouped.
6.  Completed intents stop alerting.
7.  `Remind next visit` silences current visit and works next time.
8.  Relaunch/process death does not cause obvious duplicates.
9.  Core logic is testable without GPS.
10. No backend or LLM is required.

## 26. Engineering priorities for the coding agent

Optimize in this order:

1.  domain-model correctness;
2.  contextual-trigger reliability;
3.  low notification noise;
4.  testability;
5.  fast intent capture;
6.  extensibility;
7.  visual polish.

Prefer boring deterministic code over clever abstractions.

Do not prematurely implement a generic rules DSL. Enums/interfaces for
requirement evaluators are enough initially.

Do not couple UI, geofence callbacks and intent evaluation.

Keep a persistent debug/event trail from the beginning.

When uncertain about a feature, preserve the core promise: **the user
states an intention once and the system resurfaces it only when it
becomes useful.**
