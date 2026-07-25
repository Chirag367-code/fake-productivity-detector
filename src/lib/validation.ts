/**
 * Password Validation Utility
 *
 * Rules:
 *  - Minimum 4 characters
 *  - At least 2 numbers
 *  - At least 1 special character
 */

export interface PasswordValidation {
  valid: boolean;
  errors: string[];
}

const SPECIAL_CHARS = /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?`~]/;

export function validatePassword(password: string): PasswordValidation {
  const errors: string[] = [];

  if (password.length < 4) {
    errors.push("Must be at least 4 characters long");
  }

  const digitCount = (password.match(/\d/g) || []).length;
  if (digitCount < 2) {
    errors.push("Must contain at least 2 numbers");
  }

  if (!SPECIAL_CHARS.test(password)) {
    errors.push("Must contain at least 1 special character");
  }

  return { valid: errors.length === 0, errors };
}
