import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { Pool, type PoolClient, type QueryResult, type QueryResultRow } from "pg";

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

const loadEnvFile = (filePath: string) => {
  if (!existsSync(filePath)) {
    return;
  }

  const content = readFileSync(filePath, "utf-8");

  content.split(/\r?\n/).forEach((line) => {
    const parsedLine = parseEnvLine(line);

    if (parsedLine && !process.env[parsedLine.key]) {
      process.env[parsedLine.key] = parsedLine.value;
    }
  });
};

loadEnvFile(path.join(process.cwd(), ".env"));
loadEnvFile(path.join(process.cwd(), "backend", ".env"));

const databaseUrl = process.env.DATABASE_URL;

if (!databaseUrl) {
  throw new Error("DATABASE_URL is missing. Add it to .env or backend/.env.");
}

try {
  const parsedDatabaseUrl = new URL(databaseUrl);

  if (!["postgres:", "postgresql:"].includes(parsedDatabaseUrl.protocol)) {
    throw new Error(`Unsupported protocol: ${parsedDatabaseUrl.protocol}`);
  }
} catch (error) {
  const detail = error instanceof Error ? ` ${error.message}` : "";

  throw new Error(
    `DATABASE_URL is not a valid PostgreSQL connection URL.${detail}`
    + " Expected format: postgresql://USER:PASSWORD@HOST:PORT/DATABASE"
  );
}

const sslEnabled = process.env.DATABASE_SSL !== "false";
const rejectUnauthorized = process.env.DATABASE_SSL_REJECT_UNAUTHORIZED !== "false";

export const pool = new Pool({
  connectionString: databaseUrl,
  max: Number(process.env.DATABASE_POOL_MAX || 10),
  idleTimeoutMillis: Number(process.env.DATABASE_IDLE_TIMEOUT_MS || 30_000),
  connectionTimeoutMillis: Number(process.env.DATABASE_CONNECTION_TIMEOUT_MS || 10_000),
  ssl: sslEnabled ? { rejectUnauthorized } : false,
});

export const query = async <T extends QueryResultRow = QueryResultRow>(
  text: string,
  params: unknown[] = []
): Promise<QueryResult<T>> => pool.query<T>(text, params);

export const withTransaction = async <T>(
  callback: (client: PoolClient) => Promise<T>
): Promise<T> => {
  const client = await pool.connect();

  try {
    await client.query("begin");
    const result = await callback(client);
    await client.query("commit");
    return result;
  } catch (error) {
    await client.query("rollback");
    throw error;
  } finally {
    client.release();
  }
};

export const closeDatabase = async () => {
  await pool.end();
};
