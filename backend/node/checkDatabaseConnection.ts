import { closeDatabase, query } from "./db.js";

const main = async () => {
  console.log("Connecting to PostgreSQL...");
  const result = await query<{ now: Date }>("select now()");
  const now = result.rows[0].now;
  const timestamp = now instanceof Date ? now.toISOString() : String(now);

  console.log(`Database connection OK at ${timestamp}`);
};

main()
  .catch((error) => {
    console.error("Database connection failed.");

    if (error instanceof Error) {
      console.error(error.message);

      if (error.stack) {
        console.error(error.stack);
      }
    } else {
      console.error(JSON.stringify(error, null, 2));
    }

    process.exitCode = 1;
  })
  .finally(async () => {
    await closeDatabase();
  });
