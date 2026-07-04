import assert from "node:assert/strict";
import test from "node:test";

import {
  buildCredentialText,
  defaultWorkspaceName,
  generateUatPassword,
} from "./uatCredentials.js";

test("generated UAT password satisfies the provisioning strength contract", () => {
  const password = generateUatPassword();
  assert.match(password, /^Omon-/);
  assert.ok(password.length >= 10);
  assert.match(password, /[a-z]/);
  assert.match(password, /[A-Z]/);
  assert.match(password, /\d/);
  assert.match(password, /[!@#$%]/);
});

test("workspace default follows the tester name", () => {
  assert.equal(defaultWorkspaceName("Andi"), "Andi's Household");
  assert.equal(defaultWorkspaceName(""), "");
});

test("credential text includes the complete first-time path", () => {
  const text = buildCredentialText({
    url: "http://localhost:5173",
    email: "andi@example.com",
    password: "Omon-7Kp2xQ!",
    workspace: "Andi's Household",
  });
  assert.match(text, /andi@example\.com/);
  assert.match(text, /Test Connection/);
  assert.match(text, /Sync Now/);
});
