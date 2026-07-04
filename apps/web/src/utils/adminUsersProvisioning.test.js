import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { fileURLToPath } from "node:url";

const source = readFileSync(
  fileURLToPath(new URL("../pages/AdminUsers.jsx", import.meta.url)),
  "utf8",
);

test("UAT create form exposes password generation and workspace fields", () => {
  assert.match(source, /Workspace Name/);
  assert.match(source, /Password/);
  assert.match(source, /generateUatPassword/);
  assert.match(source, /Tampilkan password/);
});

test("UAT create submits the provisioning fields", () => {
  assert.match(source, /provisionAdminTestUser\(payload\)/);
  assert.match(source, /payload\.password = formData\.password/);
  assert.match(source, /payload\.workspace_name = formData\.workspaceName\.trim\(\)/);
});

test("success credential is one-time UI state with copy guidance", () => {
  assert.match(source, /User berhasil dibuat\./);
  assert.match(source, /Password hanya ditampilkan sekarang/);
  assert.match(source, /navigator\.clipboard\.writeText/);
  assert.match(source, /Credential berhasil disalin\./);
  assert.match(source, /setCreatedCredential\(null\)/);
});

test("validation errors are user-readable", () => {
  assert.match(source, /Password dan Workspace Name wajib diisi\./);
  assert.match(source, /Email tersebut sudah terdaftar\./);
});
