import { spawn } from "node:child_process";
import path from "node:path";

const repoRoot = process.cwd();

const runPythonMonthlyAllocation = () => (
  new Promise<unknown[]>((resolve, reject) => {
    const pythonPath = process.env.PYTHON_BIN
      || path.join(repoRoot, "backend", "venv", "Scripts", "python.exe");
    const scriptPath = path.join(
      repoRoot,
      "backend",
      "scripts",
      "data_processing.py"
    );
    const child = spawn(
      pythonPath,
      [scriptPath, "monthly-allocation"],
      {
        cwd: repoRoot,
        env: process.env,
      }
    );
    let stdout = "";
    let stderr = "";

    child.stdout.on("data", (chunk) => {
      stdout += chunk.toString();
    });

    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString();
    });

    child.on("error", reject);
    child.on("close", (code) => {
      if (code !== 0) {
        reject(new Error(stderr || `Python exited with code ${code}`));
        return;
      }

      try {
        resolve(JSON.parse(stdout));
      } catch (error) {
        reject(error);
      }
    });
  })
);

// Copy this handler into a Next.js route file such as:
// app/api/analytics/monthly-allocation/route.ts
export async function GET() {
  try {
    const data = await runPythonMonthlyAllocation();

    return Response.json(data);
  } catch (error) {
    return Response.json(
      {
        error: error instanceof Error ? error.message : "Unknown error",
      },
      {
        status: 500,
      }
    );
  }
}
