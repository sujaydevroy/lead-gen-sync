/**
 * One normalised sales line parsed from an uploaded Excel sheet.
 *
 * @typedef {Object} SalesRecord
 * @property {string} id
 * @property {number} rowNumber      Row number in the source sheet (1-based, header = 1)
 * @property {string} customerName   Dealer / customer
 * @property {string} country
 * @property {string} location
 * @property {number} year
 * @property {number} month          1-12
 * @property {string} period         "YYYY-MM"
 * @property {string} product
 * @property {string} unit
 * @property {number|null} quantity
 * @property {number} amount         In the record's own currency
 * @property {string} currency       ISO code, upper-case
 *
 * @typedef {Object} SalesFilters
 * @property {string} currency          'ALL' or an ISO code present in the data
 * @property {string} reportingCurrency Currency that 'ALL' is converted into
 * @property {string} dateFrom          "YYYY-MM" or ''
 * @property {string} dateTo            "YYYY-MM" or ''
 * @property {string[]} customers
 * @property {string[]} products
 * @property {string[]} countries
 */

export const ALL_CURRENCIES = 'ALL';

/** @returns {SalesFilters} */
export const createDefaultSalesFilters = () => ({
  currency: ALL_CURRENCIES,
  reportingCurrency: 'USD',
  dateFrom: '',
  dateTo: '',
  customers: [],
  products: [],
  countries: [],
});
