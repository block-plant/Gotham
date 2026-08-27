import { Request, Response } from "express";
import { FirPayload, GangPayload } from "../types/fir.types";
import { normalizeFirPayload, deduplicateEntities } from "../services/nlp.service";
import { queryFirEntities, evaluateGang } from "../services/model.service";

// ─── POST /api/fir/query ──────────────────────────────────────────────────────
export async function queryFir(req: Request, res: Response): Promise<void> {
  const payload = req.body as FirPayload;

  // 1. NLP pre-processing: normalize raw FIR fields → graph entity keys
  const rawEntities = normalizeFirPayload(payload);
  const entities = deduplicateEntities(rawEntities);

  if (entities.length === 0) {
    res.status(400).json({
      status: "error",
      message: "Could not extract any recognizable entities from the FIR payload.",
    });
    return;
  }

  // 2. Send to Python model bridge
  try {
    const result = await queryFirEntities(entities);
    res.json(result);
  } catch (err) {
    console.error("[FIR Controller] queryFir error:", err);
    res.status(500).json({
      status: "error",
      message: "Model inference failed. See server logs for details.",
    });
  }
}

// ─── POST /api/fir/gang ───────────────────────────────────────────────────────
export async function evalGang(req: Request, res: Response): Promise<void> {
  const { fir_ids, threshold = 0.0 } = req.body as GangPayload;

  try {
    const result = await evaluateGang(fir_ids, threshold);
    res.json(result);
  } catch (err) {
    console.error("[FIR Controller] evalGang error:", err);
    res.status(500).json({
      status: "error",
      message: "Gang evaluation failed. See server logs for details.",
    });
  }
}
