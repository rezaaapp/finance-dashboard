import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";

type RegistryEntry = string | {
  id?: string;
  name?: string;
};

const repoRoot = process.cwd();
const backendRoot = path.join(repoRoot, "backend");

const parseEnvLine = (line: string) => {
  const trimmedLine = line.trim();

  if (!trimmedLine || trimmedLine.startsWith("#")) {
    return null;
  }

  const separatorIndex = trimmedLine.indexOf("=");

  if (separatorIndex === -1) {
    return null;
  }

  const key = trimmedLine.slice(0, separatorIndex).trim();
  let value = trimmedLine.slice(separatorIndex + 1).trim();

  if (
    (value.startsWith('"') && value.endsWith('"'))
    || (value.startsWith("'") && value.endsWith("'"))
  ) {
    value = value.slice(1, -1);
  }

  return { key, value };
};

const loadEnvFile = async (filePath: string) => {
  try {
    const content = await readFile(filePath, "utf-8");

    content.split(/\r?\n/).forEach((line) => {
      const parsedLine = parseEnvLine(line);

      if (parsedLine && !process.env[parsedLine.key]) {
        process.env[parsedLine.key] = parsedLine.value;
      }
    });
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== "ENOENT") {
      throw error;
    }
  }
};

const getTrackedSheetsFromEnv = () => {
  const registryJson = process.env.GOOGLE_SHEET_REGISTRY_JSON;

  if (registryJson) {
    const registry = JSON.parse(registryJson) as Record<string, RegistryEntry>;

    return Object.entries(registry)
      .map(([year, entry]) => ({
        year: Number(year),
        id: typeof entry === "string" ? entry : entry.id,
      }))
      .filter((sheet): sheet is { year: number; id: string } => (
        Number.isInteger(sheet.year) && Boolean(sheet.id)
      ))
      .sort((a, b) => a.year - b.year);
  }

  const fallbackSheetId = process.env.GOOGLE_SPREADSHEET_ID;

  if (!fallbackSheetId) {
    return [];
  }

  return [{
    year: new Date().getFullYear(),
    id: fallbackSheetId,
  }];
};

const main = async () => {
  await loadEnvFile(path.join(repoRoot, ".env"));
  await loadEnvFile(path.join(backendRoot, ".env"));

  const sheets = getTrackedSheetsFromEnv();

  if (!process.env.GEMINI_API_KEY) {
    throw new Error("GEMINI_API_KEY is missing. Add it to .env or backend/.env.");
  }

  if (sheets.length === 0) {
    throw new Error("No tracked Google Sheets found in GOOGLE_SHEET_REGISTRY_JSON.");
  }

  const { syncAndClassifyFinancialData } = await import(
    "./syncAndClassifyFinancialData.js"
  );

  console.log(`Processing ${sheets.length} tracked spreadsheet(s)...`);

  const outputDir = path.join(backendRoot, "output");
  const outputPath = path.join(outputDir, "financial-classification-reference.json");
  const existingPredictions = await readFile(outputPath, "utf-8")
    .then((content) => {
      const parsed = JSON.parse(content) as {
        predictions?: Awaited<ReturnType<typeof syncAndClassifyFinancialData>>;
      };

      return parsed.predictions ?? [];
    })
    .catch(() => []);

  if (existingPredictions.length > 0) {
    console.log(`Resuming from ${existingPredictions.length} cached prediction(s).`);
  }

  const writePredictions = async (
    predictions: Awaited<ReturnType<typeof syncAndClassifyFinancialData>>,
    status: "partial" | "complete"
  ) => {
    await mkdir(outputDir, { recursive: true });
    await writeFile(
      outputPath,
      JSON.stringify({
        generated_at: new Date().toISOString(),
        status,
        total_predictions: predictions.length,
        predictions,
      }, null, 2),
      "utf-8"
    );
  };

  const predictions = await syncAndClassifyFinancialData(sheets, {
    batchSize: Number(process.env.GEMINI_CLASSIFICATION_BATCH_SIZE || 25),
    existingPredictions,
    onProgress: (message) => console.log(message),
    onBatchComplete: async (partialPredictions) => {
      await writePredictions(partialPredictions, "partial");
    },
  });

  await writePredictions(predictions, "complete");

  console.log(`Done. ${predictions.length} prediction(s) saved to ${outputPath}`);
};

main().catch((error) => {
  console.error(error instanceof Error ? error.message : error);
  process.exitCode = 1;
});
