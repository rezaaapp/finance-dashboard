export const dashboardChartPalette = {
  navy: "var(--brand-primary)",
  sage: "var(--chart-positive)",
  sageLight: "var(--success-border)",
  gold: "var(--color-alert)",
  charcoal: "var(--text-primary)",
  muted: "var(--text-muted)",
  border: "var(--border)",
  surface: "var(--surface)",
  base: "var(--background)",
  darkBase: "var(--background)",
  darkSurface: "var(--surface)",
  darkBorder: "var(--border)",
  darkText: "var(--text-primary)",
  danger: "var(--chart-negative)",
};

export const categoricalChartColors = [
  dashboardChartPalette.navy,
  dashboardChartPalette.sage,
  dashboardChartPalette.gold,
  "var(--chart-4)",
  "var(--chart-1)",
  "var(--warning-border)",
  "var(--neutral-text)",
  "var(--neutral-border)",
];

export const financialTypeChartColors = {
  need: "var(--chart-1)",
  want: "var(--chart-2)",
  saving: "var(--chart-3)",
  income: "var(--chart-4)",
  uncategorized: "var(--neutral-border)",
};

export const chartTheme = {
  dark: {
    grid: "var(--chart-grid)",
    tick: "var(--chart-axis)",
    tooltipBg: "var(--chart-tooltip-bg)",
    tooltipBorder: "var(--chart-tooltip-border)",
    tooltipText: "var(--chart-tooltip-text)",
    legendText: "var(--chart-legend)",
    primary: "var(--chart-1)",
    secondary: "var(--chart-positive)",
    alert: dashboardChartPalette.gold,
    positive: "var(--chart-positive)",
    negative: "var(--chart-negative)",
  },
  light: {
    grid: "var(--chart-grid)",
    tick: "var(--chart-axis)",
    tooltipBg: "var(--chart-tooltip-bg)",
    tooltipBorder: "var(--chart-tooltip-border)",
    tooltipText: "var(--chart-tooltip-text)",
    legendText: "var(--chart-legend)",
    primary: dashboardChartPalette.navy,
    secondary: dashboardChartPalette.sage,
    alert: dashboardChartPalette.gold,
    positive: "var(--chart-positive)",
    negative: "var(--chart-negative)",
  },
};
