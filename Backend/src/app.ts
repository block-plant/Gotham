import express from "express";
import helmet from "helmet";
import cors from "cors";
import { authMiddleware } from "./middleware/auth.middleware";
import { rateLimitMiddleware } from "./middleware/rateLimit.middleware";
import { consoleLogger, fileLogger } from "./middleware/logger.middleware";
import firRoutes from "./routes/fir.routes";

const app = express();

// ─── Security Headers ──────────────────────────────────────────────────────────
app.use(helmet());

// ─── CORS ─────────────────────────────────────────────────────────────────────
const allowedOrigins = [
  process.env.FRONTEND_ORIGIN || "http://localhost:5500",
  "http://127.0.0.1:5500",
  "null", // Allow file:// opened HTML pages during development
];

app.use(
  cors({
    origin: (origin, callback) => {
      // Allow requests with no origin (curl, Postman, file://)
      if (!origin || allowedOrigins.includes(origin)) {
        callback(null, true);
      } else {
        callback(new Error(`CORS blocked for origin: ${origin}`));
      }
    },
    methods: ["GET", "POST"],
    allowedHeaders: ["Content-Type", "X-API-Key"],
  })
);

// ─── Body Parser ──────────────────────────────────────────────────────────────
app.use(express.json({ limit: "1mb" }));

// ─── Rate Limiting ────────────────────────────────────────────────────────────
app.use(rateLimitMiddleware);

// ─── Logging ──────────────────────────────────────────────────────────────────
app.use(consoleLogger);
app.use(fileLogger);

// ─── Health Check (public, no auth) ──────────────────────────────────────────
app.get("/health", (_req, res) => {
  res.json({ status: "ok", service: "Gotham GNN Investigator API", timestamp: new Date().toISOString() });
});

// ─── Auth (all routes below require X-API-Key) ────────────────────────────────
app.use(authMiddleware);

// ─── Routes ───────────────────────────────────────────────────────────────────
app.use("/api/fir", firRoutes);

// ─── 404 Handler ──────────────────────────────────────────────────────────────
app.use((_req, res) => {
  res.status(404).json({ status: "error", message: "Route not found." });
});

// ─── Global Error Handler ─────────────────────────────────────────────────────
app.use((err: Error, _req: express.Request, res: express.Response, _next: express.NextFunction) => {
  console.error("[Unhandled Error]", err.message);
  res.status(500).json({ status: "error", message: "Internal server error." });
});

export default app;
