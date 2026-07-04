import assert from "node:assert/strict";
import test from "node:test";

import {
  changedValues,
  dirtySettingsSummary,
  discardSettings,
  shouldBlockSettingsNavigation,
} from "./settingsDirtyState.js";

test("dirty state appears only for changed configuration fields", () => {
  const saved = { payday_start_day: 1, auto_budget: true, privacy_mode: "normal" };
  assert.equal(dirtySettingsSummary({ configuration: saved, savedConfiguration: saved, insights: {}, savedInsights: {} }).count, 0);
  assert.equal(dirtySettingsSummary({ configuration: { ...saved, privacy_mode: "hide" }, savedConfiguration: saved, insights: {}, savedInsights: {} }).count, 1);
});

test("changed values contains only modified configuration", () => {
  assert.deepEqual(
    changedValues(
      { payday_start_day: 5, auto_budget: true, privacy_mode: "hide" },
      { payday_start_day: 1, auto_budget: true, privacy_mode: "hide" },
      ["payday_start_day", "auto_budget", "privacy_mode"]
    ),
    { payday_start_day: 5 }
  );
});

test("immediate action state is not part of dirty counter", () => {
  const summary = dirtySettingsSummary({
    configuration: { payday_start_day: 1, auto_budget: true, privacy_mode: "normal", syncing: true },
    savedConfiguration: { payday_start_day: 1, auto_budget: true, privacy_mode: "normal" },
    insights: {}, savedInsights: {},
  });
  assert.equal(summary.count, 0);
});

test("discard restores the last saved values", () => {
  const restored = discardSettings({
    savedConfiguration: { privacy_mode: "normal" },
    savedInsights: { need_warning_ratio: 80 },
  });
  assert.deepEqual(restored.configuration, { privacy_mode: "normal" });
  assert.deepEqual(restored.insights, { need_warning_ratio: 80 });
});

test("navigation warning is active only while settings are dirty", () => {
  assert.equal(shouldBlockSettingsNavigation(0), false);
  assert.equal(shouldBlockSettingsNavigation(2), true);
});
