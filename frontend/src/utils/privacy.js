export const PRIVACY_MODES = {
  normal: "normal",
  hide: "hide",
  guest: "guest",
};

const DEFAULT_GUEST_MULTIPLIER = 0.75;

export const getGuestModeMultiplier = () => {
  const multiplier = Number(import.meta.env.VITE_GUEST_MODE_MULTIPLIER);

  return Number.isFinite(multiplier) && multiplier > 0
    ? multiplier
    : DEFAULT_GUEST_MULTIPLIER;
};

export const maskNumber = (value, privacyMode = PRIVACY_MODES.normal) => {
  const numericValue = Number(value || 0);

  if (privacyMode === PRIVACY_MODES.guest) {
    return Math.round(numericValue * getGuestModeMultiplier());
  }

  return numericValue;
};

export const formatPrivateRupiah = (
  value,
  privacyMode = PRIVACY_MODES.normal
) => {
  if (privacyMode === PRIVACY_MODES.hide) {
    return "Rp ••••••••";
  }

  return new Intl.NumberFormat("id-ID", {
    style: "currency",
    currency: "IDR",
    maximumFractionDigits: 0,
  }).format(maskNumber(value, privacyMode));
};

export const formatPrivateCompact = (
  value,
  privacyMode = PRIVACY_MODES.normal
) => {
  if (privacyMode === PRIVACY_MODES.hide) {
    return "•••";
  }

  return new Intl.NumberFormat("id-ID", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(maskNumber(value, privacyMode));
};

export const maskChartRows = (
  rows = [],
  keys = [],
  privacyMode = PRIVACY_MODES.normal
) => (
  rows.map((row) => {
    const maskedRow = { ...row };

    keys.forEach((key) => {
      if (key in maskedRow) {
        maskedRow[key] = maskNumber(maskedRow[key], privacyMode);
      }
    });

    return maskedRow;
  })
);
