/**
 * @typedef {'Email' | 'Message' | 'Call' | 'Meeting'} CommunicationType
 * @typedef {'outbound' | 'inbound'} CommunicationDirection
 *
 * @typedef {Object} Attachment
 * @property {string} name
 * @property {number} size   bytes
 * @property {string} type   MIME type
 *
 * @typedef {Object} Communication
 * @property {string} id
 * @property {string} dealerId
 * @property {CommunicationType} type
 * @property {CommunicationDirection} direction
 * @property {string} sender
 * @property {string} recipient
 * @property {string} subject
 * @property {string} body
 * @property {string} status
 * @property {string} createdAt  ISO timestamp
 * @property {Attachment[]} attachments
 */

export const COMMUNICATION_TYPES = ['Email', 'Message', 'Call', 'Meeting'];
export const MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024;
