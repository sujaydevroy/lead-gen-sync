/**
 * @typedef {'Active' | 'Inactive' | 'Pending'} DealerStatus
 * @typedef {'Distributor' | 'Reseller' | 'Partner' | 'Service Center'} DealerType
 *
 * Shape of one record in dealers.json (the single dealer data source).
 * Fields that the source could not provide hold the literal string "Not Available".
 *
 * @typedef {Object} Dealer
 * @property {string} dealer_id
 * @property {string} dealer_name
 * @property {string} company_name
 * @property {DealerType} dealer_type
 * @property {DealerStatus} status
 * @property {string} contact_person
 * @property {string} region             Geographic zone within the country (North, South, ...)
 * @property {string} registration_no
 * @property {string} full_address
 * @property {string} city
 * @property {string} state
 * @property {string} postal_code
 * @property {string} email
 * @property {string} phone
 * @property {string} website
 * @property {string} country
 * @property {string} sector             Sector name as defined in sector.json
 * @property {string[]} product          Products / product lines handled by the dealer
 * @property {string} last_transaction_date
 * @property {string} last_transaction_amount
 * @property {string} currency
 * @property {string} source_url
 * @property {string} verification_date
 * @property {string} created_at
 * @property {boolean} is_demo           true for generated demo records
 */

/**
 * Filter state used by the dealer list. Every array is an OR-group; groups are AND-ed.
 *
 * @typedef {Object} DealerFilters
 * @property {string[]} countries
 * @property {string[]} regions
 * @property {DealerStatus[]} statuses
 * @property {DealerType[]} types
 * @property {string[]} sectors
 * @property {string[]} subSectors
 */

/**
 * @typedef {Object} DealerQuery
 * @property {string} [search]
 * @property {DealerFilters} [filters]
 * @property {number} [page]      1-based
 * @property {number} [pageSize]
 */

export const NOT_AVAILABLE = 'Not Available';

export const DEALER_STATUSES = ['Active', 'Inactive', 'Pending'];
export const DEALER_TYPES = ['Distributor', 'Reseller', 'Partner', 'Service Center'];
export const PAGE_SIZE_OPTIONS = [10, 20, 50];

/** @returns {DealerFilters} */
export const createEmptyDealerFilters = () => ({
  countries: [],
  regions: [],
  statuses: [],
  types: [],
  sectors: [],
  subSectors: [],
});

/** True when a field holds real data (not empty / "Not Available"). */
export const hasValue = (value) =>
  value !== undefined && value !== null && String(value).trim() !== '' && value !== NOT_AVAILABLE;
