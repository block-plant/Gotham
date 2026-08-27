import { Router } from "express";
import { queryFir, evalGang } from "../controllers/fir.controller";
import { validateFirQuery, validateGang } from "../middleware/validate.middleware";

const router = Router();

/**
 * POST /api/fir/query
 * Submit a new FIR (any subset of 12 fields) and get back
 * a list of historically linked FIRs with probabilities + evidence.
 */
router.post("/query", validateFirQuery, queryFir);

/**
 * POST /api/fir/gang
 * Provide a list of known FIR IDs to test whether they form
 * a hidden criminal syndicate. Returns pairwise link probabilities.
 */
router.post("/gang", validateGang, evalGang);

export default router;
