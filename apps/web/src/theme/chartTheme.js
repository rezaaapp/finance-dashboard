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

export const allocationChartColors = {
  Needs: "var(--chart-1)",
  Wants: "var(--chart-2)",
  Savings: "var(--chart-positive)",
};

export const sourceDanaChartColors = {
  bca: "var(--chart-1)",
  blu: "var(--chart-4)",
  gopay: "var(--chart-positive)",
  ovo: "var(--chart-2)",
  seabank: "var(--chart-negative)",
  jago: "var(--color-alert)",
};

export const heatmapTheme = {
  dark: {
    empty: "rgba(30, 41, 59, 0.72)",
    textStrong: "var(--chart-tooltip-text)",
    textDefault: "var(--color-text)",
    stops: [
      [15, 23, 42],
      [8, 145, 178],
      [20, 184, 166],
      [251, 191, 36],
    ],
  },
  light: {
    empty: "rgba(226, 232, 240, 0.72)",
    textStrong: "var(--info-text)",
    textDefault: "var(--color-text)",
    stops: [
      [224, 242, 254],
      [103, 232, 249],
      [20, 184, 166],
      [245, 158, 11],
    ],
  },
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
