import { closeDatabase } from "./db.js";
import { createInitialWorkspaceForUser } from "./repositories/workspaceRepository.js";

const seedUserEmail = process.env.SEED_USER_EMAIL || "demo.finance@example.com";
const seedUserName = process.env.SEED_USER_NAME || "Demo Finance User";
const seedWorkspaceName = process.env.SEED_WORKSPACE_NAME || "Demo Household";

const main = async () => {
  console.log("Seeding initial workspace...");

  const result = await createInitialWorkspaceForUser({
    email: seedUserEmail,
    name: seedUserName,
    workspaceName: seedWorkspaceName,
  });

  console.log("Seed complete.");
  console.log(`User: ${result.user.email} (${result.user.id})`);
  console.log(`Workspace: ${result.workspace.name} (${result.workspace.id})`);
  console.log(`Membership role: ${result.membership.role}`);
  console.log(
    `Google Sheet ID: ${result.configuration.google_sheet_id ?? "not configured yet"}`
  );
};

main()
  .catch((error) => {
    console.error("Seed failed.");

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
