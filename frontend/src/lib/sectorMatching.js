// Maps a dealer's free-text product lines onto the sub-sectors listed in sector.json.
// A product matches a sub-sector when it equals the sub-sector name (case-insensitive)
// or contains one of the sub-sector's keywords as a whole word / phrase.

const SUB_SECTOR_KEYWORDS = {
  'Electrical Switches': ['switch', 'switches'],
  Switchgear: ['switchgear', 'ring main unit', 'rmu', 'breakers & switches'],
  'MCB & MCCB': ['mcb', 'mccb', 'breaker', 'breakers', 'circuit breaker'],
  'Distribution Boards': ['distribution board', 'distribution boards'],
  'Electrical Panels': ['panel', 'panels', 'enclosure', 'enclosures'],
  'Wires & Cables': ['wire', 'wires', 'cable', 'cables'],
  'Industrial Cables': ['industrial cable', 'industrial cables'],
  'House Wires': ['house wire', 'house wires'],
  Transformers: ['transformer', 'transformers'],
  Motors: ['motors', 'electric motor'],
  Generators: ['generator', 'generators', 'genset'],
  'Electrical Control Equipment': ['control products', 'control equipment', 'motor starter', 'motor starters'],
  Contactors: ['contactor', 'contactors'],
  Relays: ['relay', 'relays'],
  Capacitors: ['capacitor', 'capacitors'],
  'Electrical Accessories': ['din rail', 'accessories', 'terminal block'],
  'Modular Switches': ['modular switch', 'modular switches'],
  'Sockets & Plugs': ['socket', 'sockets', 'plug', 'plugs'],
  Fans: ['fan', 'fans', 'ceiling fan'],
  'Exhaust Fans': ['exhaust fan', 'exhaust fans'],
  'LED Bulbs': ['led bulb', 'led bulbs'],
  'LED Lights': ['led light', 'led lights', 'led panel'],
  'Commercial Lighting': ['commercial lighting'],
  'Industrial Lighting': ['industrial lighting', 'high bay'],
  'Street Lighting': ['street lighting', 'street light'],
  'Solar Lighting': ['solar lighting', 'solar light'],
  Batteries: ['battery', 'batteries'],
  Inverters: ['inverter', 'inverters'],
  UPS: ['ups'],
  Stabilizers: ['stabilizer', 'stabilizers', 'stabiliser'],
  'Power Quality Equipment': ['power quality', 'harmonic filter', 'surge protection'],
  'Earthing Products': ['earthing', 'grounding'],
  'Lightning Protection': ['lightning protection', 'lightning'],
};

const escapeRegExp = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

const matcherCache = new Map();
function matcherFor(subSector) {
  if (!matcherCache.has(subSector)) {
    const terms = [subSector, ...(SUB_SECTOR_KEYWORDS[subSector] || [])].map((t) => escapeRegExp(t.toLowerCase()));
    matcherCache.set(subSector, new RegExp(`(^|[^a-z0-9])(${terms.join('|')})($|[^a-z0-9])`, 'i'));
  }
  return matcherCache.get(subSector);
}

/** Does one product string belong to the given sub-sector? */
export function productMatchesSubSector(product, subSector) {
  if (!product) return false;
  return matcherFor(subSector).test(product.toLowerCase());
}

/**
 * Sub-sectors (from the provided list) that the dealer's products map to.
 * @param {import('@/types/dealer').Dealer} dealer
 * @param {string[]} subSectors
 */
export function dealerSubSectors(dealer, subSectors) {
  const products = Array.isArray(dealer.product) ? dealer.product : [];
  return subSectors.filter((sub) => products.some((p) => productMatchesSubSector(p, sub)));
}
