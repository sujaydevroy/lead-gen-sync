const COUNTRY_CODES = {
  India: 'IN',
  'United States': 'US',
  Germany: 'DE',
  'United Kingdom': 'GB',
  France: 'FR',
  Singapore: 'SG',
  Australia: 'AU',
  'United Arab Emirates': 'AE',
  Japan: 'JP',
  Canada: 'CA',
  Belgium: 'BE',
  Egypt: 'EG',
  Indonesia: 'ID',
  Nepal: 'NP',
  Bangladesh: 'BD',
  Turkey: 'TR',
  Vietnam: 'VN',
  Philippines: 'PH',
  Russia: 'RU',
  'Sri Lanka': 'LK',
};

export function countryCode(country) {
  return COUNTRY_CODES[country] || '';
}

/** Regional-indicator emoji flag, e.g. "IN" -> 🇮🇳. Empty string for unknown countries. */
export function countryFlag(country) {
  const code = countryCode(country);
  if (!code) return '';
  return String.fromCodePoint(...[...code].map((c) => 0x1f1e6 + c.charCodeAt(0) - 65));
}
