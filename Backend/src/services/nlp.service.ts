import { FirPayload } from "../types/fir.types";

// ─── Normalized Entity ─────────────────────────────────────────────────────────
export interface NormalizedEntity {
  prefix: string;       // e.g. "MO_", "BEAT_", "IO_"
  raw: string;          // e.g. "THEFT"
  graphKey: string;     // e.g. "MO_THEFT"
}

// ─── NLP Pre-Processing Service ───────────────────────────────────────────────
// Converts raw FIR JSON fields into a list of normalized graph-query entities.
// Fuzzy matching against the actual graph nodes is done in the Python bridge.

export function normalizeFirPayload(payload: FirPayload): NormalizedEntity[] {
  const entities: NormalizedEntity[] = [];

  // ── CrimeHead_Name → MO_ ──────────────────────────────────────────────────
  if (payload.CrimeHead_Name) {
    const val = payload.CrimeHead_Name.trim().toUpperCase();
    entities.push({ prefix: "MO_", raw: val, graphKey: `MO_${val}` });
  }

  // ── Beat_Name → BEAT_ ─────────────────────────────────────────────────────
  if (payload.Beat_Name) {
    const val = payload.Beat_Name.trim().toUpperCase();
    entities.push({ prefix: "BEAT_", raw: val, graphKey: `BEAT_${val}` });
  }

  // ── UnitName → UNIT_ ──────────────────────────────────────────────────────
  if (payload.UnitName) {
    const val = payload.UnitName.trim().toUpperCase();
    entities.push({ prefix: "UNIT_", raw: val, graphKey: `UNIT_${val}` });
  }

  // ── District_Name → DIST_ ─────────────────────────────────────────────────
  if (payload.District_Name) {
    const val = payload.District_Name.trim().toUpperCase();
    entities.push({ prefix: "DIST_", raw: val, graphKey: `DIST_${val}` });
  }

  // ── ActSection → ACT_ (comma-separated, split each) ───────────────────────
  if (payload.ActSection) {
    const acts = payload.ActSection
      .split(/[,;]/)
      .map((a) => a.trim().toUpperCase().replace(/\s+/g, "_"))
      .filter(Boolean);
    for (const act of acts) {
      entities.push({ prefix: "ACT_", raw: act, graphKey: `ACT_${act}` });
    }
  }

  // ── IOName → IO_ ──────────────────────────────────────────────────────────
  // IOName is the Investigating Officer. We query them as a graph node
  // because a shared IO across FIRs is a strong syndicate signal,
  // and a corrupt IO could themselves be a criminal network node.
  if (payload.IOName) {
    const val = payload.IOName.trim().toUpperCase();
    entities.push({ prefix: "IO_", raw: val, graphKey: `IO_${val}` });
  }

  // ── CrimeGroup → CG_ ──────────────────────────────────────────────────────
  if (payload.CrimeGroup) {
    const val = payload.CrimeGroup.trim().toUpperCase();
    entities.push({ prefix: "CG_", raw: val, graphKey: `CG_${val}` });
  }

  // ── AccusedName → IO_ (accused persons also queried as graph nodes) ────────
  // Comma-separated list of accused persons. Each is treated as a potential
  // graph node (criminals who appear in multiple FIRs are high-value links).
  if (payload.AccusedName) {
    const accused = payload.AccusedName
      .split(/[,;]/)
      .map((a) => a.trim().toUpperCase())
      .filter(Boolean);
    for (const person of accused) {
      entities.push({
        prefix: "IO_",
        raw: `${person} (accused)`,
        graphKey: `IO_${person}`,
      });
    }
  }

  // ── WeaponUsed → MO_ suffix hint (informational, best-effort match) ────────
  if (payload.WeaponUsed) {
    const val = payload.WeaponUsed.trim().toUpperCase();
    // Weapons don't have a dedicated prefix — we include as a free-text MO hint
    entities.push({ prefix: "MO_", raw: `weapon:${val}`, graphKey: `MO_${val}` });
  }

  return entities;
}

// ─── Deduplicate entities by graphKey ─────────────────────────────────────────
export function deduplicateEntities(entities: NormalizedEntity[]): NormalizedEntity[] {
  const seen = new Set<string>();
  return entities.filter((e) => {
    if (seen.has(e.graphKey)) return false;
    seen.add(e.graphKey);
    return true;
  });
}
