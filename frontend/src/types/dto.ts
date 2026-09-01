/**
 * DTO types — the shape the API/UI layers consume. Distinct from the DB row
 * types (see src/server/dbTypes.ts). The repo layer is responsible for
 * mapping row → DTO; callers above the repo never see raw DB row shapes.
 */

export interface ApiUser {
  id: string;
  name: string;
  is_physician: boolean;
}

export type ThreadPriority = "low" | "normal" | "high";

/**
 * Frequently-updated, denormalized thread state stored in the `threads.metadata`
 * JSONB column.
 */
export interface ThreadMetadata {
  /**
   * Patient messages awaiting a physician reply. Incremented when a patient
   * sends a message and reset to 0 when a physician responds in the thread.
   */
  unrespondedPatientMessagesCount: number;
  /** Epoch ms of the last summary the queue job produced, or null if never. */
  lastSummaryGenerated: number | null;
  topicTags: string[];
  priority: ThreadPriority;
}

export interface ApiThread {
  id: string;
  title: string;
  /**
   * Participant ids on this thread. By product rule there is exactly one
   * patient (always present) and zero-or-more physicians.
   */
  users: string[];
  date_created: number;
  metadata: ThreadMetadata;
}

export interface ApiMessage {
  id: number;
  /** Author id — resolves to either a patient or a physician. */
  userId: string;
  threadId: string;
  message: string;
  timestamp: number;
  msgIndex: number;
}
