import type { PoolClient } from "pg";
import { withTransaction } from "../db.js";

export type UserProfile = {
  id: string;
  email: string;
  name: string;
  avatar_url: string | null;
  created_at: Date;
  updated_at: Date;
};

export type Workspace = {
  id: string;
  name: string;
  subscription_status: "free" | "premium";
  created_at: Date;
  updated_at: Date;
};

export type WorkspaceMember = {
  id: string;
  workspace_id: string;
  user_id: string;
  role: "owner" | "member";
  created_at: Date;
  updated_at: Date;
};

export type WorkspaceConfiguration = {
  id: string;
  workspace_id: string;
  google_sheet_id: string | null;
  created_at: Date;
  updated_at: Date;
};

export type WorkspaceBootstrap = {
  user: UserProfile;
  workspace: Workspace;
  membership: WorkspaceMember;
  configuration: WorkspaceConfiguration;
};

type SeedWorkspaceInput = {
  email: string;
  name: string;
  avatarUrl?: string | null;
  workspaceName: string;
};

export const upsertUser = async (
  client: PoolClient,
  input: { email: string; name: string; avatarUrl?: string | null }
) => {
  const result = await client.query<UserProfile>(
    `
      insert into users (email, name, avatar_url)
      values ($1, $2, $3)
      on conflict (email)
      do update set
        name = excluded.name,
        avatar_url = coalesce(excluded.avatar_url, users.avatar_url)
      returning id, email, name, avatar_url, created_at, updated_at
    `,
    [input.email.toLowerCase(), input.name, input.avatarUrl ?? null]
  );

  return result.rows[0];
};

const findOwnedWorkspace = async (
  client: PoolClient,
  input: { userId: string; workspaceName: string }
) => {
  const result = await client.query<Workspace>(
    `
      select w.id, w.name, w.subscription_status, w.created_at, w.updated_at
      from workspaces w
      inner join workspace_members wm on wm.workspace_id = w.id
      where wm.user_id = $1
        and wm.role = 'owner'
        and lower(w.name) = lower($2)
      limit 1
    `,
    [input.userId, input.workspaceName]
  );

  return result.rows[0] ?? null;
};

const createWorkspace = async (client: PoolClient, workspaceName: string) => {
  const result = await client.query<Workspace>(
    `
      insert into workspaces (name, subscription_status)
      values ($1, 'free')
      returning id, name, subscription_status, created_at, updated_at
    `,
    [workspaceName]
  );

  return result.rows[0];
};

const upsertOwnerMembership = async (
  client: PoolClient,
  input: { workspaceId: string; userId: string }
) => {
  const result = await client.query<WorkspaceMember>(
    `
      insert into workspace_members (workspace_id, user_id, role)
      values ($1, $2, 'owner')
      on conflict (workspace_id, user_id)
      do update set role = 'owner'
      returning id, workspace_id, user_id, role, created_at, updated_at
    `,
    [input.workspaceId, input.userId]
  );

  return result.rows[0];
};

const upsertWorkspaceConfiguration = async (
  client: PoolClient,
  workspaceId: string
) => {
  const result = await client.query<WorkspaceConfiguration>(
    `
      insert into workspace_configurations (workspace_id, google_sheet_id)
      values ($1, null)
      on conflict (workspace_id)
      do update set google_sheet_id = workspace_configurations.google_sheet_id
      returning id, workspace_id, google_sheet_id, created_at, updated_at
    `,
    [workspaceId]
  );

  return result.rows[0];
};

export const createInitialWorkspaceForUser = async (
  input: SeedWorkspaceInput
): Promise<WorkspaceBootstrap> => withTransaction(async (client) => {
  const user = await upsertUser(client, {
    email: input.email,
    name: input.name,
    avatarUrl: input.avatarUrl,
  });

  const existingWorkspace = await findOwnedWorkspace(client, {
    userId: user.id,
    workspaceName: input.workspaceName,
  });
  const workspace = existingWorkspace ?? await createWorkspace(client, input.workspaceName);
  const membership = await upsertOwnerMembership(client, {
    workspaceId: workspace.id,
    userId: user.id,
  });
  const configuration = await upsertWorkspaceConfiguration(client, workspace.id);

  return {
    user,
    workspace,
    membership,
    configuration,
  };
});
