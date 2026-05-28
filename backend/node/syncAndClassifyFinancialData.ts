import { GoogleGenAI } from "@google/genai";
import { google } from "googleapis";

export type TrackedSpreadsheet = {
  year: number;
  id: string;
};

export type FinancialClassificationPrediction = {
  input_title: string;
  input_category: string;
  cleaned_merchant: string;
  allocation_type: "Needs" | "Wants" | "Savings";
  confidence_score: number;
};

type UniqueTransactionPair = {
  input_title: string;
  input_category: string;
};

type GeminiClassificationResponse = {
  predictions: FinancialClassificationPrediction[];
};

type SyncAndClassifyOptions = {
  batchSize?: number;
  model?: string;
  existingPredictions?: FinancialClassificationPrediction[];
  onProgress?: (message: string) => void;
  onBatchComplete?: (
    predictions: FinancialClassificationPrediction[],
    metadata: { batchIndex: number; totalBatches: number }
  ) => Promise<void> | void;
};

const SHEETS_READONLY_SCOPE = "https://www.googleapis.com/auth/spreadsheets.readonly";

const ai = new GoogleGenAI({
  apiKey: process.env.GEMINI_API_KEY,
});

const SYSTEM_INSTRUCTION = `
You are an expert financial data engineer specializing in the Indonesian market.
Analyze the input array of transaction pairs.
Your sole task is to assign an accurate 50/30/20 budget allocation type
("Needs", "Wants", or "Savings") to each pair based on financial rules and
clean up the merchant name.

Indonesian context:
- "Kopi", "Cafe", "Gojek/Grab Food", "Jajan", snacks, restaurants,
  entertainment, beauty, cosmetics, and non-essential shopping are usually Wants.
- "PLN", "Listrik", "Sewa Apartemen", "Sembako", rent, electricity, water,
  internet, insurance, groceries, health, and essential transportation are usually Needs.
- "Bibit", "Ajaib", "Saham", "Investasi", "Reksadana", deposits, emergency
  funds, and explicit saving transfers are Savings.

Return only raw JSON. Do not include markdown, explanations, or prose.
The JSON must match:
{
  "predictions": [
    {
      "input_title": "string",
      "input_category": "string",
      "cleaned_merchant": "string",
      "allocation_type": "Needs" | "Wants" | "Savings",
      "confidence_score": number
    }
  ]
}
`;

const normalizeHeader = (value: unknown) => (
  String(value ?? "").trim().toLowerCase()
);

const findColumnIndex = (headers: unknown[], columnName: string) => (
  headers.findIndex((header) => normalizeHeader(header) === columnName.toLowerCase())
);

const buildCompositeKey = (title: string, category: string) => (
  `${title.trim().toLowerCase()}::${category.trim().toLowerCase()}`
);

const quoteSheetName = (sheetName: string) => (
  `'${sheetName.replaceAll("'", "''")}'`
);

const chunkArray = <T,>(items: T[], size: number) => {
  const chunks: T[][] = [];

  for (let index = 0; index < items.length; index += size) {
    chunks.push(items.slice(index, index + size));
  }

  return chunks;
};

const sleep = (ms: number) => (
  new Promise((resolve) => {
    setTimeout(resolve, ms);
  })
);

const isRetryableGeminiError = (error: unknown) => {
  const status = (error as { status?: number })?.status;

  return status === 429 || status === 500 || status === 502
    || status === 503 || status === 504;
};

const parseGeminiResponse = (text: string): GeminiClassificationResponse => {
  const parsed = JSON.parse(text) as GeminiClassificationResponse;

  if (!parsed || !Array.isArray(parsed.predictions)) {
    throw new Error("Gemini response is missing the predictions array.");
  }

  return parsed;
};

const getServiceAccountCredentials = () => {
  const rawJson = process.env.GOOGLE_SERVICE_ACCOUNT_JSON?.trim();
  const rawBase64 = process.env.GOOGLE_SERVICE_ACCOUNT_JSON_BASE64?.trim();

  if (rawBase64) {
    return JSON.parse(Buffer.from(rawBase64, "base64").toString("utf-8"));
  }

  if (rawJson) {
    return JSON.parse(rawJson);
  }

  return undefined;
};

const getGoogleSheetsAuth = () => {
  const credentials = getServiceAccountCredentials();

  if (credentials) {
    return new google.auth.GoogleAuth({
      credentials,
      scopes: [SHEETS_READONLY_SCOPE],
    });
  }

  if (process.env.GOOGLE_APPLICATION_CREDENTIALS) {
    return new google.auth.GoogleAuth({
      keyFile: process.env.GOOGLE_APPLICATION_CREDENTIALS,
      scopes: [SHEETS_READONLY_SCOPE],
    });
  }

  return new google.auth.GoogleAuth({
    scopes: [SHEETS_READONLY_SCOPE],
  });
};

const validatePrediction = (
  prediction: FinancialClassificationPrediction
) => (
  prediction
  && typeof prediction.input_title === "string"
  && typeof prediction.input_category === "string"
  && typeof prediction.cleaned_merchant === "string"
  && ["Needs", "Wants", "Savings"].includes(prediction.allocation_type)
  && typeof prediction.confidence_score === "number"
);

export async function syncAndClassifyFinancialData(
  sheets: TrackedSpreadsheet[],
  options: SyncAndClassifyOptions = {}
): Promise<FinancialClassificationPrediction[]> {
  if (!process.env.GEMINI_API_KEY) {
    throw new Error("GEMINI_API_KEY is not configured.");
  }

  const batchSize = options.batchSize ?? 100;
  const primaryModel = options.model ?? process.env.GEMINI_CLASSIFICATION_MODEL
    ?? "gemini-2.0-flash";
  const onBatchComplete = options.onBatchComplete ?? (() => undefined);
  const existingKeys = new Set(
    (options.existingPredictions ?? []).map((prediction) => (
      buildCompositeKey(prediction.input_title, prediction.input_category)
    ))
  );
  const modelCandidates = [
    primaryModel,
    "gemini-2.0-flash-lite",
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash",
  ].filter((model, index, models) => models.indexOf(model) === index);
  const onProgress = options.onProgress ?? (() => undefined);
  const auth = getGoogleSheetsAuth();
  const sheetsApi = google.sheets({ version: "v4", auth });
  const uniquePairsByKey = new Map<string, UniqueTransactionPair>();

  for (const trackedSheet of sheets) {
    const spreadsheet = await sheetsApi.spreadsheets.get({
      spreadsheetId: trackedSheet.id,
      fields: "sheets.properties.title",
    });

    const worksheetTitles = spreadsheet.data.sheets
      ?.map((sheet) => sheet.properties?.title)
      .filter((title): title is string => Boolean(title)) ?? [];

    for (const worksheetTitle of worksheetTitles) {
      const valuesResponse = await sheetsApi.spreadsheets.values.get({
        spreadsheetId: trackedSheet.id,
        range: quoteSheetName(worksheetTitle),
      });

      const rows = valuesResponse.data.values ?? [];

      if (rows.length < 2) {
        continue;
      }

      const headers = rows[0];
      const titleIndex = findColumnIndex(headers, "Nama Transaksi");
      const categoryIndex = findColumnIndex(headers, "Kategori");

      if (titleIndex === -1 || categoryIndex === -1) {
        continue;
      }

      for (const row of rows.slice(1)) {
        const title = String(row[titleIndex] ?? "").trim();
        const category = String(row[categoryIndex] ?? "").trim();

        if (!category) {
          continue;
        }

        if (!title) {
          continue;
        }

        const compositeKey = buildCompositeKey(title, category);

        if (!uniquePairsByKey.has(compositeKey)) {
          uniquePairsByKey.set(compositeKey, {
            input_title: title,
            input_category: category,
          });
        }
      }
    }
  }

  const uniquePairs = [...uniquePairsByKey.values()].filter((pair) => (
    !existingKeys.has(buildCompositeKey(pair.input_title, pair.input_category))
  ));
  onProgress(`Found ${uniquePairs.length} unique transaction pair(s).`);

  if (uniquePairs.length === 0) {
    return [];
  }

  try {
    const predictions: FinancialClassificationPrediction[] = [
      ...(options.existingPredictions ?? []),
    ];
    const batches = chunkArray(uniquePairs, batchSize);

    for (const [batchIndex, batch] of batches.entries()) {
      onProgress(`Classifying batch ${batchIndex + 1}/${batches.length}...`);
      const payload = JSON.stringify(batch, null, 2);
      let responseText = "";
      let lastError: unknown = null;

      for (const model of modelCandidates) {
        for (let attempt = 1; attempt <= 3; attempt += 1) {
          try {
            const response = await ai.models.generateContent({
              model,
              contents: [
                {
                  role: "user",
                  parts: [
                    {
                      text: `Classify this array of unique transaction pairs:\n${payload}`,
                    },
                  ],
                },
              ],
              config: {
                responseMimeType: "application/json",
                systemInstruction: SYSTEM_INSTRUCTION,
              },
            });

            responseText = response.text ?? "";
            lastError = null;
            break;
          } catch (error) {
            lastError = error;

            if (!isRetryableGeminiError(error) || attempt === 3) {
              break;
            }

            const delayMs = 1500 * attempt;
            onProgress(
              `Gemini retryable error on ${model}, attempt ${attempt}/3. Retrying in ${delayMs}ms...`
            );
            await sleep(delayMs);
          }
        }

        if (responseText || !isRetryableGeminiError(lastError)) {
          break;
        }

        onProgress(`Switching Gemini model after retryable failure: ${model}`);
      }

      if (lastError && !responseText) {
        throw lastError;
      }

      if (!responseText) {
        throw new Error("Gemini returned an empty response.");
      }

      const parsed = parseGeminiResponse(responseText);
      const validPredictions = parsed.predictions.filter(validatePrediction);

      if (validPredictions.length !== parsed.predictions.length) {
        console.warn("Some Gemini predictions were dropped due to invalid schema.");
      }

      predictions.push(...validPredictions);
      await onBatchComplete(predictions, {
        batchIndex,
        totalBatches: batches.length,
      });
      onProgress(`Finished batch ${batchIndex + 1}/${batches.length}.`);
    }

    return predictions;
  } catch (error) {
    console.error("Failed to sync and classify financial data.", error);

    throw new Error(
      `Gemini classification pipeline failed: ${
        error instanceof Error ? error.message : String(error)
      }`
    );
  }
}
