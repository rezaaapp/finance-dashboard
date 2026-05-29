import { closeDatabase, query, withTransaction } from "./db.js";

type UserWithoutWorkspace = {
  id: string;
  name: string;
  email: string;
};

const main = async () => {
  const users = await query<UserWithoutWorkspace>(`
    select u.id, u.name, u.email
    from users u
    left join workspace_members wm on wm.user_id = u.id
    where wm.id is null
    order by u.created_at asc
  `);

  if (users.rows.length === 0) {
    console.log("No users need workspace backfill.");
    return;
  }

  console.log(`Backfilling ${users.rows.length} user workspace(s)...`);

  await withTransaction(async (client) => {
    for (const user of users.rows) {
      const workspace = await client.query<{ id: string }>(
        `
          insert into workspaces (name, subscription_status)
          values ($1, 'free')
          returning id
        `,
        [`${user.name}'s Household`]
      );
      const workspaceId = workspace.rows[0].id;

      await client.query(
        `
          insert into workspace_members (workspace_id, user_id, role)
          values ($1, $2, 'owner')
          on conflict (workspace_id, user_id)
          do update set role = 'owner'
        `,
        [workspaceId, user.id]
      );

      await client.query(
        `
          insert into workspace_configurations (workspace_id, google_sheet_id)
          values ($1, null)
          on conflict (workspace_id)
          do nothing
        `,
        [workspaceId]
      );

      console.log(`Created workspace for ${user.email}.`);
    }
  });

  console.log("Workspace backfill complete.");
};

main()
  .catch((error) => {
    console.error(error instanceof Error ? error.message : error);
    process.exitCode = 1;
  })
  .finally(async () => {
    await closeDatabase();
  });
