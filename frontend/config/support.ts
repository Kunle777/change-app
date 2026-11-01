// Fill these in before launch. Rows that depend on an empty value are hidden,
// so nothing in the app points at a dead link.
export const SUPPORT_EMAIL = '';
export const PRIVACY_POLICY_URL = '';
export const TERMS_URL = '';

export const HAS_HELP = Boolean(SUPPORT_EMAIL || PRIVACY_POLICY_URL || TERMS_URL);
