const LOWER = "abcdefghijkmnopqrstuvwxyz";
const UPPER = "ABCDEFGHJKLMNPQRSTUVWXYZ";
const DIGITS = "23456789";
const SYMBOLS = "!@#$%";

const randomCharacter = (characters) => {
  const values = new Uint32Array(1);
  globalThis.crypto.getRandomValues(values);
  return characters[values[0] % characters.length];
};

export const generateUatPassword = () => {
  const characters = [
    randomCharacter(UPPER),
    randomCharacter(LOWER),
    randomCharacter(DIGITS),
    randomCharacter(SYMBOLS),
    ...Array.from({ length: 6 }, () => randomCharacter(`${LOWER}${UPPER}${DIGITS}`)),
  ];

  for (let index = characters.length - 1; index > 0; index -= 1) {
    const values = new Uint32Array(1);
    globalThis.crypto.getRandomValues(values);
    const swapIndex = values[0] % (index + 1);
    [characters[index], characters[swapIndex]] = [characters[swapIndex], characters[index]];
  }

  return `Omon-${characters.join("")}`;
};

export const defaultWorkspaceName = (name) => {
  const normalizedName = String(name || "").trim();
  return normalizedName ? `${normalizedName}'s Household` : "";
};

export const buildCredentialText = ({ url, email, password, workspace }) => (
  `URL:\n${url}\n\nEmail:\n${email}\n\nPassword:\n${password}\n\nWorkspace:\n${workspace}\n\n`
  + "Silakan Login, buka Settings, Connect Google, tambahkan URL spreadsheet, Test Connection, Save Source, lalu Sync Now. Setelah itu buka Dashboard."
);
