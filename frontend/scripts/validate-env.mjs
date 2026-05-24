const apiUrl = process.env.VITE_API_URL || process.env.VITE_API_BASE_URL;

if (!apiUrl) {
  console.error(
    "Missing VITE_API_URL or VITE_API_BASE_URL. Set it before building for production."
  );
  process.exit(1);
}

if (/localhost|127\.0\.0\.1|0\.0\.0\.0/.test(apiUrl)) {
  console.error(
    `Production API URL must not point to localhost: ${apiUrl}`
  );
  process.exit(1);
}

try {
  new URL(apiUrl);
} catch {
  console.error(`Production API URL is not a valid URL: ${apiUrl}`);
  process.exit(1);
}

console.log(`Using production API URL: ${apiUrl}`);
