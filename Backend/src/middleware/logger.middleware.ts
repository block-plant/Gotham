import morgan from "morgan";
import fs from "fs";
import path from "path";

// Ensure logs directory exists
const logsDir = path.resolve(__dirname, "../../logs");
if (!fs.existsSync(logsDir)) {
  fs.mkdirSync(logsDir, { recursive: true });
}

// Write stream for file logging
const accessLogStream = fs.createWriteStream(
  path.join(logsDir, "access.log"),
  { flags: "a" } // append mode
);

// Console logger (dev format: colorized, concise)
export const consoleLogger = morgan("dev");

// File logger (combined format: full details)
export const fileLogger = morgan("combined", { stream: accessLogStream });
