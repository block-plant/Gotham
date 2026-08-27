// ─── FIR Payload ────────────────────────────────────────────────────────────
// All fields are optional. The backend uses whatever is provided.
export interface FirPayload {
  CrimeHead_Name?: string;    // e.g. "THEFT"
  Beat_Name?: string;          // e.g. "AMINAGAD TOWN BEAT NO 1"
  UnitName?: string;           // e.g. "BAGALKOT TOWN PS"
  District_Name?: string;      // e.g. "BAGALKOT"
  ActSection?: string;         // e.g. "IPC 379, IPC 34" (comma-separated OK)
  IOName?: string;             // Investigating Officer name
  CrimeGroup?: string;         // e.g. "PROPERTY OFFENCES"
  MO_Description?: string;     // Free-text modus operandi description
  AccusedName?: string;        // Accused person(s), comma-separated
  VictimName?: string;         // Victim name (used for lookups)
  WeaponUsed?: string;         // e.g. "KNIFE"
  PlaceOfOccurrence?: string;  // Free-text address
  CrimeDateTime?: string;      // ISO datetime string (informational)
}

// ─── Gang Evaluation Payload ─────────────────────────────────────────────────
export interface GangPayload {
  fir_ids: string[];   // e.g. ["FIR_629293", "FIR_951598"]
  threshold?: number;  // 0–1, default 0.0 (return all)
}

// ─── Model Response Types ─────────────────────────────────────────────────────
export interface LinkResult {
  fir_id: string;
  probability: number;         // 0–1
  evidence: string[];          // ["Same MO", "Same Beat", ...]
}

export interface PairResult {
  fir_a: string;
  fir_b: string;
  probability: number;
  evidence: string[];
  is_high_confidence: boolean;
}

export interface QueryResponse {
  status: "ok" | "error";
  matched_entities: string[];    // Graph nodes successfully resolved
  unmatched_fields: string[];    // Fields that couldn't be found in graph
  results: LinkResult[];
  message?: string;
}

export interface GangResponse {
  status: "ok" | "error";
  pairs: PairResult[];
  message?: string;
}
