import { spawn } from "child_process";
import path from "path";
import { NormalizedEntity } from "./nlp.service";
import { QueryResponse, GangResponse } from "../types/fir.types";

const PYTHON = process.env.PYTHON_PATH || "python";
const MODEL_PATH = path.resolve(
  process.cwd(),
  process.env.MODEL_PATH || "../MODEL"
);

// ─── Spawn Python bridge helper ────────────────────────────────────────────────
function spawnPython(args: string[], stdinData: string): Promise<string> {
  return new Promise((resolve, reject) => {
    const scriptPath = path.join(MODEL_PATH, "src", "models", "investigator.py");

    const proc = spawn(PYTHON, [scriptPath, ...args], {
      cwd: MODEL_PATH,
      env: { ...process.env, PYTHONIOENCODING: "utf-8" },
    });

    let stdout = "";
    let stderr = "";

    proc.stdout.on("data", (data: Buffer) => {
      stdout += data.toString();
    });

    proc.stderr.on("data", (data: Buffer) => {
      stderr += data.toString();
    });

    proc.on("close", (code) => {
      if (code !== 0) {
        reject(
          new Error(`Python bridge exited with code ${code}.\nStderr: ${stderr}`)
        );
      } else {
        resolve(stdout.trim());
      }
    });

    proc.on("error", (err) => {
      reject(new Error(`Failed to spawn Python: ${err.message}`));
    });

    // Write input JSON to Python stdin and close it
    if (stdinData) {
      proc.stdin.write(stdinData);
      proc.stdin.end();
    }
  });
}

// ─── Query a new FIR against the graph ────────────────────────────────────────
export async function queryFirEntities(
  entities: NormalizedEntity[]
): Promise<QueryResponse> {
  const graphKeys = entities.map((e) => e.graphKey);
  const inputPayload = JSON.stringify({ mode: "query", entities: graphKeys });

  try {
    const raw = await spawnPython(["--json-mode"], inputPayload);

    // Extract only the JSON portion from stdout (model may print boot messages)
    const lines = raw.split("\n");
    let jsonStr = "";
    for (let i = lines.length - 1; i >= 0; i--) {
      if (lines[i].trim().startsWith("{")) {
        jsonStr = lines.slice(i).join("\n");
        break;
      }
    }
    if (!jsonStr) {
      throw new Error(`No JSON found in Python output: ${raw}`);
    }
    return JSON.parse(jsonStr) as QueryResponse;
  } catch (err) {
    throw new Error(`Model service error: ${(err as Error).message}`);
  }
}

// ─── Evaluate a known list of FIR IDs as a gang ───────────────────────────────
export async function evaluateGang(
  firIds: string[],
  threshold: number
): Promise<GangResponse> {
  const inputPayload = JSON.stringify({
    mode: "gang",
    fir_ids: firIds,
    threshold,
  });

  try {
    const raw = await spawnPython(["--json-mode"], inputPayload);

    // Extract only the JSON portion from stdout (model may print boot messages)
    // We look for the first '{' that represents the start of the top-level object
    // A better approach is to find the LAST line that starts with '{' or parse the whole stdout backwards.
    // Let's just find the first '{' since the stdout might have boot logs before it.
    const lines = raw.split("\n");
    let jsonStr = "";
    for (let i = lines.length - 1; i >= 0; i--) {
      if (lines[i].trim().startsWith("{")) {
        jsonStr = lines.slice(i).join("\n");
        break;
      }
    }
    if (!jsonStr) {
      throw new Error(`No JSON found in Python output: ${raw}`);
    }
    return JSON.parse(jsonStr) as GangResponse;
  } catch (err) {
    throw new Error(`Model service error: ${(err as Error).message}`);
  }
}
