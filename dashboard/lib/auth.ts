// Simple password authentication
export function checkPassword(password: string): boolean {
  const adminPassword = process.env.ADMIN_PASSWORD || 'muze-admin-2024';
  return password === adminPassword;
}

export function setAuthCookie() {
  if (typeof window !== 'undefined') {
    document.cookie = 'muze-auth=true; path=/; max-age=86400'; // 24 hours
  }
}

export function clearAuthCookie() {
  if (typeof window !== 'undefined') {
    document.cookie = 'muze-auth=; path=/; max-age=0';
  }
}

export function isAuthenticated(): boolean {
  if (typeof window !== 'undefined') {
    return document.cookie.includes('muze-auth=true');
  }
  return false;
}
