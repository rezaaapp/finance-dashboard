import assert from "node:assert/strict";
import test from "node:test";

import {
  createSystemInfoFallback,
  getEnvironmentPresentation,
  isUatProvisioningAllowed,
  normalizeSystemInfo,
  sanitizeApiUrl,
} from "./environment.js";

const frontend = {
  apiUrl: "http://127.0.0.1:8000",
  frontendPort: 5173,
  version: "v0.9.2-env-foundation",
};

test("local-dev environment renders the development presentation", () => {
  const info = normalizeSystemInfo({
    app_env: "local-dev",
    env_profile: "local-dev",
    db_target: "postgres-local",
    backend_port: 8000,
    database_host: "127.0.0.1",
    database_name: "finance_dashboard_local",
    latest_migration: "021_example.sql",
    migration_count: 24,
  }, frontend);

  assert.equal(info.appEnv, "local-dev");
  assert.equal(info.connected, true);
  assert.equal(info.frontendPort, 5173);
  assert.equal(getEnvironmentPresentation(info.appEnv).badgeLabel, "LOCAL-DEV");
  assert.equal(getEnvironmentPresentation(info.appEnv).tone, "dev");
});

test("local-prod environment renders the production simulation presentation", () => {
  const info = normalizeSystemInfo({
    app_env: "local-prod",
    env_profile: "local-prod",
    db_target: "supabase",
    backend_port: 8001,
    database_host: "aw***.supabase.com",
    database_name: "postgres",
  }, { ...frontend, apiUrl: "http://127.0.0.1:8001" });

  assert.equal(getEnvironmentPresentation(info.appEnv).badgeLabel, "LOCAL-PROD");
  assert.equal(getEnvironmentPresentation(info.appEnv).tone, "prod");
  assert.equal(info.apiUrl, "http://127.0.0.1:8001");
});

test("hosted UAT environment is preserved and clearly presented", () => {
  const info = normalizeSystemInfo({
    app_env: "uat",
    env_profile: "uat",
    db_target: "supabase",
    backend_port: 3127,
    database_host: "db***.supabase.co",
  }, { ...frontend, apiUrl: "/" });

  assert.equal(info.appEnv, "uat");
  assert.equal(info.backendPort, 3127);
  assert.equal(getEnvironmentPresentation(info.appEnv).badgeLabel, "UAT");
  assert.equal(getEnvironmentPresentation(info.appEnv).databaseLabel, "Supabase UAT");
});

test("provisioning allows UAT and denies mixed production identity", () => {
  assert.equal(isUatProvisioningAllowed({ appEnv: "uat", envProfile: "uat" }), true);
  assert.equal(isUatProvisioningAllowed({ appEnv: "prod", envProfile: "prod" }), false);
  assert.equal(isUatProvisioningAllowed({ appEnv: "prod", envProfile: "uat" }), false);
});

test("offline fallback remains usable and identifies an unknown environment", () => {
  const fallback = createSystemInfoFallback(frontend);

  assert.equal(fallback.appEnv, "unknown");
  assert.equal(fallback.connected, false);
  assert.equal(getEnvironmentPresentation(fallback.appEnv).badgeLabel, "UNKNOWN");
  assert.equal(fallback.apiUrl, "http://127.0.0.1:8000");
});

test("normalization never forwards secret fields or URL credentials", () => {
  const info = normalizeSystemInfo({
    app_env: "local-prod",
    database_url: "postgresql://admin:private@db.example.com/postgres",
    password: "private-password",
    token: "private-token",
    jwt_secret: "private-jwt",
  }, {
    apiUrl: "http://user:password@127.0.0.1:8001/private/path",
    version: "test-version",
  });
  const serialized = JSON.stringify(info);

  assert.equal(sanitizeApiUrl("http://user:password@127.0.0.1:8001/path"), "http://127.0.0.1:8001");
  assert.equal(serialized.includes("private-password"), false);
  assert.equal(serialized.includes("private-token"), false);
  assert.equal(serialized.includes("private-jwt"), false);
  assert.equal(serialized.includes("postgresql://"), false);
});
