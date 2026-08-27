import { Request, Response, NextFunction } from "express";

const API_KEY = process.env.API_KEY;

export function authMiddleware(
  req: Request,
  res: Response,
  next: NextFunction
): void {
  // Health check is public
  if (req.path === "/health") {
    next();
    return;
  }

  const providedKey = req.headers["x-api-key"];

  if (!API_KEY) {
    console.error("[AUTH] WARNING: No API_KEY set in .env — all requests denied.");
    res.status(500).json({ status: "error", message: "Server misconfiguration: API key not set." });
    return;
  }

  if (!providedKey || providedKey !== API_KEY) {
    res.status(401).json({ status: "error", message: "Unauthorized: Invalid or missing X-API-Key header." });
    return;
  }

  next();
}
