import { Request, Response, NextFunction } from "express";
import { z, ZodError } from "zod";

// ─── FIR Query Schema ─────────────────────────────────────────────────────────
// At least ONE field must be present. All are optional strings.
const FirQuerySchema = z
  .object({
    CrimeHead_Name: z.string().min(1).optional(),
    Beat_Name: z.string().min(1).optional(),
    UnitName: z.string().min(1).optional(),
    District_Name: z.string().min(1).optional(),
    ActSection: z.string().min(1).optional(),
    IOName: z.string().min(1).optional(),
    CrimeGroup: z.string().min(1).optional(),
    MO_Description: z.string().min(1).optional(),
    AccusedName: z.string().min(1).optional(),
    VictimName: z.string().min(1).optional(),
    WeaponUsed: z.string().min(1).optional(),
    PlaceOfOccurrence: z.string().min(1).optional(),
    CrimeDateTime: z.string().optional(),
  })
  .refine(
    (data) => Object.values(data).some((v) => v !== undefined && v !== ""),
    { message: "At least one FIR field must be provided." }
  );

// ─── Gang Evaluation Schema ───────────────────────────────────────────────────
const GangSchema = z.object({
  fir_ids: z
    .array(z.string().regex(/^FIR_\d+$/, "Each entry must be a valid FIR ID like FIR_629293"))
    .min(2, "At least 2 FIR IDs required to evaluate gang links"),
  threshold: z.number().min(0).max(1).optional().default(0.0),
});

// ─── Middleware factories ─────────────────────────────────────────────────────
function makeValidator(schema: z.ZodTypeAny) {
  return (req: Request, res: Response, next: NextFunction): void => {
    try {
      req.body = schema.parse(req.body);
      next();
    } catch (err) {
      if (err instanceof ZodError) {
        res.status(400).json({
          status: "error",
          message: "Validation failed",
          errors: err.errors.map((e) => ({
            field: e.path.join("."),
            issue: e.message,
          })),
        });
        return;
      }
      next(err);
    }
  };
}

export const validateFirQuery = makeValidator(FirQuerySchema);
export const validateGang = makeValidator(GangSchema);
