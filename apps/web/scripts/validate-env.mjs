import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

const modeIndex = process.argv.indexOf("--mode");
const mode = modeIndex >= 0 ? process.argv[modeIndex + 1] : "production";
const isLocalMode = mode === "local-dev" || mode === "local-prod";
const localEnv = {};
const envPath = resolve(
  process.cwd(),
  isLocalMode ? `.env.${mode}` : ".env",
);

if (existsSync(envPath)) {
  const envFile = readFileSync(envPath, "utf-8");

  for (const line of envFile.split(/\r?\n/)) {
    const match = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$/);

    if (match) {
      localEnv[match[1]] = match[2].replace(/^["']|["']$/g, "");
    }
  }
}

const apiUrl = process.env.VITE_API_URL
  || process.env.VITE_API_BASE_URL
  || localEnv.VITE_API_URL
  || localEnv.VITE_API_BASE_URL;
const apiMode = process.env.VITE_API_MODE || localEnv.VITE_API_MODE;

if (apiMode === "same-origin") {
  console.log("Using same-origin API mode for production build.");
  process.exit(0);
}

if (!apiUrl) {
  console.error(
    "Missing VITE_API_URL or VITE_API_BASE_URL. Set one to your backend URL, or set VITE_API_MODE=same-origin for Replit single-app deployment."
  );
  process.exit(1);
}

if (!isLocalMode && /localhost|127\.0\.0\.1|0\.0\.0\.0/.test(apiUrl)) {
  console.error(
    `Production API URL must not point to localhost: ${apiUrl}`
  );
  process.exit(1);
}

try {
  new URL(apiUrl);
} catch {
  console.error(`Production API URL is not a valid URL: ${apiUrl}`);
  process.exit(1);
}

console.log(`Using ${mode} API URL: ${apiUrl}`);
