export const SETTINGS_FIELDS = [
  "payday_start_day",
  "auto_budget",
  "privacy_mode",
];

const comparable = (value) => (
  typeof value === "number" ? Number(value) : String(value ?? "")
);

export const changedFields = (draft = {}, saved = {}, fields = Object.keys(draft)) => (
  fields.filter((field) => comparable(draft[field]) !== comparable(saved[field]))
);

export const changedValues = (draft = {}, saved = {}, fields = Object.keys(draft)) => (
  Object.fromEntries(changedFields(draft, saved, fields).map((field) => [field, draft[field]]))
);

export const dirtySettingsSummary = ({ configuration, savedConfiguration, insights, savedInsights }) => {
  const configurationFields = changedFields(
    configuration,
    savedConfiguration,
    SETTINGS_FIELDS
  );
  const insightFields = changedFields(
    insights,
    savedInsights,
    Object.keys(insights || {}).filter((field) => field !== "source")
  );
  return {
    configurationFields,
    insightFields,
    count: configurationFields.length + insightFields.length,
  };
};

export const discardSettings = ({ savedConfiguration, savedInsights }) => ({
  configuration: { ...savedConfiguration },
  insights: { ...savedInsights },
});

export const shouldBlockSettingsNavigation = (dirtyCount) => Number(dirtyCount) > 0;
