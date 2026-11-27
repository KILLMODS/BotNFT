const RAW_BASE_ENV = (import.meta.env.VITE_BOT_API_URL || '').trim().replace(/\/+$/, '');

function getSafeBase(): string {
  if (!RAW_BASE_ENV) return '';
  if (
    typeof window !== 'undefined' &&
    window.location.protocol === 'https:' &&
    RAW_BASE_ENV.startsWith('http://') &&
    !RAW_BASE_ENV.startsWith('http://localhost') &&
    !RAW_BASE_ENV.startsWith('http://127.0.0.1')
  ) {
    return '';
  }
  return RAW_BASE_ENV;
}

export function resolveApiUrl(path: string): string {
  if (!path) return path;
  if (path.startsWith('data:') || path.startsWith('http://') || path.startsWith('https://')) {
    return path;
  }
  const base = getSafeBase();
  return base ? `${base}${path}` : path;
}

export function resolveAssetUrl(path: string | undefined | null): string {
  if (!path) return '';
  return resolveApiUrl(path);
}

export function resolveWsUrl(): string {
  const base = getSafeBase();
  if (base) {
    const wsBase = base.replace(/^https:/i, 'wss:').replace(/^http:/i, 'ws:');
    return `${wsBase}/ws`;
  }
  if (
    typeof window !== 'undefined' &&
    window.location.hostname !== 'localhost' &&
    window.location.hostname !== '127.0.0.1' &&
    !window.location.hostname.endsWith('.run.app')
  ) {
    return 'wss://bot-1794151795-2693-black-kot198.bothost.tech/ws';
  }
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${proto}//${window.location.host}/ws`;
}

export function getTelegramWebApp(): TelegramWebApp | undefined {
  return window.Telegram?.WebApp;
}

function buildAuthHeaders(): Record<string, string> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  const tg = getTelegramWebApp();
  if (tg?.initData) {
    headers['X-Telegram-Init-Data'] = tg.initData;
  } else {
    const savedId = localStorage.getItem('nnft_preview_uid') || '777001';
    headers['X-Dev-User-Id'] = savedId;
  }
  return headers;
}

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(resolveApiUrl(path), {
      ...init,
      headers: {
        ...buildAuthHeaders(),
        ...(init?.headers || {}),
      },
    });
  } catch {
    throw new Error(
      'Нет связи с сервером бота (порт 3000). Убедитесь, что бот запущен на хостинге.'
    );
  }

  const rawText = await res.text();
  let data: Record<string, unknown> | null = null;
  if (rawText) {
    try {
      data = JSON.parse(rawText) as Record<string, unknown>;
    } catch {
      data = null;
    }
  }

  if (!res.ok || data?.ok === false) {
    const errMsg =
      (typeof data?.error === 'string' && data.error) ||
      (res.status >= 502
        ? `Сервер бота (порт 3000) не отвечает (${res.status}). Проверьте, запущен ли бот.`
        : `Ошибка запроса (${res.status})`);
    throw new Error(errMsg);
  }
  if (!data) {
    throw new Error('Сервер вернул некорректный ответ (порт 3000).');
  }
  return data as T;
}

/**
 * Cleanly parses decimal numbers typed with comma (",") or dot (".") and optional spaces.
 */
export function parseDecimal(raw: string | number | null | undefined): number {
  if (typeof raw === 'number') return Number.isFinite(raw) ? raw : 0;
  if (raw === null || raw === undefined) return 0;
  const cleaned = String(raw)
    .replace(/\s+/g, '')
    .replace(/,/g, '.')
    .replace(/^\+/, '');
  if (!cleaned || cleaned === '.') return 0;
  const n = Number(cleaned);
  return Number.isFinite(n) ? n : 0;
}

/**
 * Filters raw input while preserving user's "," or "." decimal separator cleanly.
 */
export function sanitizeDecimalInput(raw: string): string {
  let out = '';
  let hasSep = false;
  for (const ch of raw.replace(/\s+/g, '')) {
    if (ch >= '0' && ch <= '9') {
      out += ch;
    } else if ((ch === '.' || ch === ',') && !hasSep) {
      out += out.length === 0 ? '0.' : '.';
      hasSep = true;
    }
  }
  return out;
}

function formatGroupedDecimal(val: number, maxDigits: number): string {
  if (!Number.isFinite(val)) return '0';
  const fixed = val.toFixed(maxDigits).replace(/\.?0+$/, '');
  const [intPart, decPart] = fixed.split('.');
  const groupedInt = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
  return decPart !== undefined ? `${groupedInt}.${decPart}` : groupedInt;
}

export function formatStars(val: number): string {
  const num = Math.round(val || 0);
  if (Math.abs(num) >= 1_000_000_000) {
    return `${(num / 1_000_000_000).toFixed(2).replace(/\.?0+$/, '')} млрд`;
  }
  if (Math.abs(num) >= 10_000_000) {
    return `${(num / 1_000_000).toFixed(2).replace(/\.?0+$/, '')} млн`;
  }
  return String(num).replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
}

export function formatTon(val: number, digits = 2): string {
  if (!Number.isFinite(val)) return '0';
  if (val > 0 && val < 0.001) return val.toFixed(6).replace(/\.?0+$/, '');
  return formatGroupedDecimal(val, digits);
}

declare global {
  interface TelegramWebApp {
    initData?: string;
    initDataUnsafe?: {
      user?: {
        id: number;
        first_name?: string;
        last_name?: string;
        username?: string;
        photo_url?: string;
      };
    };
    ready?: () => void;
    expand?: () => void;
    setHeaderColor?: (color: string) => void;
    setBackgroundColor?: (color: string) => void;
    HapticFeedback?: {
      impactOccurred: (style: 'light' | 'medium' | 'heavy') => void;
      notificationOccurred: (type: 'error' | 'success' | 'warning') => void;
    };
  }

  interface Window {
    Telegram?: {
      WebApp?: TelegramWebApp;
    };
  }
}
