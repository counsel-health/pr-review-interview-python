# Product constraints

This document is the source of truth for the small set of product rules
the codebase is expected to honor. Code may rely on these; the schema in
`backend/migrations/` is shaped to express them where it can.

## Threads, patients, and physicians

- **A thread has exactly one patient, and that patient never changes.**
  Every thread is owned by a single patient (`threads.patient_id`). The
  patient is fixed for the life of the thread — there is no reassignment,
  merge, or "switch patient" operation. An inbound message that doesn't
  match the thread's patient is a routing error, not a signal to mutate
  the thread.
- **A thread can have multiple physicians.** The care team on a thread is
  the set of rows in `threads_physicians` for that thread. Physicians can
  be added or removed over time. (Patients cannot.)

## Inbound and the work queue

- **Patient-inbound drives the queue.** "Unread for the care team," the
  care-team alert, and the response-time (SLA) clock are triggered **only**
  by patient-authored messages. A physician's own reply *clears* unread —
  it never sets it or restarts the clock.

## Message authorship

- Every message has exactly one author. The schema enforces this with a
  `CHECK` on `messages`: exactly one of `author_patient_id` /
  `author_physician_id` is set. Application code should never write both
  or neither.
