import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const importLandingSource = readFileSync(
  new URL("./ImportLanding.jsx", import.meta.url),
  "utf8"
);

test("BCA import remains disabled and marked Coming Soon", () => {
  assert.match(importLandingSource, /const comingSoonProviders = \[[\s\S]*"BCA PDF"/);
  assert.match(
    importLandingSource,
    /comingSoonProviders\.map\([\s\S]*<ProviderBadge>Coming Soon<\/ProviderBadge>[\s\S]*<button[\s\S]*disabled/
  );
});
