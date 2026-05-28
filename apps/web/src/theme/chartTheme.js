export const dashboardChartPalette = {
  navy: "#002B45",
  sage: "#4A5D4E",
  sageLight: "#7C8E80",
  gold: "#F4D35E",
  charcoal: "#1A1A1A",
  muted: "#6B7280",
  border: "#E5E7EB",
  surface: "#FFFFFF",
  base: "#F8F9FA",
  darkBase: "#0B192C",
  darkSurface: "#112240",
  darkBorder: "rgba(226, 232, 240, 0.14)",
  darkText: "#F8FAFC",
  danger: "#D9534F",
};

export const categoricalChartColors = [
  dashboardChartPalette.navy,
  dashboardChartPalette.sage,
  dashboardChartPalette.gold,
  "#7A8D82",
  "#335C67",
  "#B6A15D",
  "#8C6E63",
  "#A3ADB8",
];

export const chartTheme = {
  dark: {
    grid: "rgba(226, 232, 240, 0.14)",
    tick: "#A8B3C3",
    tooltipBg: dashboardChartPalette.darkSurface,
    tooltipBorder: dashboardChartPalette.darkBorder,
    tooltipText: dashboardChartPalette.darkText,
    legendText: "#A8B3C3",
    primary: "#9DB6C4",
    secondary: "#9BB6A0",
    alert: dashboardChartPalette.gold,
  },
  light: {
    grid: "#D9E0E5",
    tick: dashboardChartPalette.muted,
    tooltipBg: dashboardChartPalette.surface,
    tooltipBorder: dashboardChartPalette.border,
    tooltipText: dashboardChartPalette.charcoal,
    legendText: dashboardChartPalette.muted,
    primary: dashboardChartPalette.navy,
    secondary: dashboardChartPalette.sage,
    alert: dashboardChartPalette.gold,
  },
};
