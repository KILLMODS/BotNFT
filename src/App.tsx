import { useCallback, useEffect, useRef, useState } from 'react';
import {
  CandlestickChart as CandleIcon,
  ChevronRight,
  Gavel,
  Home,
  Rocket,
  Sparkles,
  User,
  X,
} from 'lucide-react';
import {
  apiRequest,
  formatStars,
  formatTon,
  getTelegramWebApp,
  resolveAssetUrl,
  resolveWsUrl,
} from './api';
import { SplashScreen } from './components/SplashScreen';
import { ProfileView } from './components/ProfileView';
import { UpgraderView } from './components/UpgraderView';
import { RocketView } from './components/RocketView';
import { ExchangeView } from './components/ExchangeView';
import type {
  AppTab,
  CatalogData,
  CollectionItem,
  MemecoinSummary,
  RocketState,
  UserProfile,
} from './types';

const INITIAL_ROCKET: RocketState = {
  phase: 'betting',
  round_id: 1,
  countdown_sec: 9.0,
  multiplier: 1.0,
  crash_point: null,
  bets: [],
  history: [],
};

export default function App() {
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [tab, setTab] = useState<AppTab>('home');
  const [auctionModalOpen, setAuctionModalOpen] = useState(false);

  const [user, setUser] = useState<UserProfile | null>(null);
  const [collection, setCollection] = useState<CollectionItem[]>([]);
  const [catalog, setCatalog] = useState<CatalogData | null>(null);
  const [coins, setCoins] = useState<MemecoinSummary[]>([]);
  const [rocket, setRocket] = useState<RocketState>(INITIAL_ROCKET);
  const [wsConnected, setWsConnected] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const fallbackTimerRef = useRef<number | null>(null);

  const loadInitialData = useCallback(async () => {
    try {
      const [meRes, coinsRes, rocketRes] = await Promise.all([
        apiRequest<{
          user: UserProfile;
          collection: CollectionItem[];
          catalog: CatalogData;
        }>('/api/me'),
        apiRequest<{ coins: MemecoinSummary[] }>('/api/coins'),
        apiRequest<{ rocket: RocketState }>('/api/rocket/state'),
      ]);
      setUser(meRes.user);
      setCollection(meRes.collection);
      setCatalog(meRes.catalog);
      setCoins(coinsRes.coins);
      setRocket(rocketRes.rocket);
      setLoadError(null);
    } catch (err) {
      setLoadError(
        err instanceof Error ? err.message : 'Не удалось подключиться к серверу бота'
      );
    } finally {
      setLoading(false);
    }
  }, []);

  const refreshCoins = useCallback(async () => {
    try {
      const res = await apiRequest<{ coins: MemecoinSummary[] }>('/api/coins');
      setCoins(res.coins);
    } catch {
      // Ignore transient refresh failures
    }
  }, []);

  useEffect(() => {
    const tg = getTelegramWebApp();
    if (tg) {
      tg.ready?.();
      tg.expand?.();
      tg.setHeaderColor?.('#000000');
      tg.setBackgroundColor?.('#000000');
    }
    const minSplash = new Promise((r) => setTimeout(r, 550));
    Promise.all([loadInitialData(), minSplash]).then(() => setLoading(false));
  }, [loadInitialData]);

  // WebSocket live connection to port 3000 with clean fallback sync if blocked
  useEffect(() => {
    let closedByEffect = false;
    let reconnectTimer: number | null = null;
    let fallbackTick = 0;
    let wsFailCount = 0;

    const startFallbackSync = () => {
      if (fallbackTimerRef.current !== null) return;
      fallbackTimerRef.current = window.setInterval(async () => {
        fallbackTick += 1;
        try {
          const r = await apiRequest<{ rocket: RocketState }>('/api/rocket/state');
          setRocket(r.rocket);
        } catch {
          // Ignore transient rocket poll errors
        }
        if (fallbackTick % 5 === 0) {
          try {
            const c = await apiRequest<{ coins: MemecoinSummary[] }>('/api/coins');
            setCoins(c.coins);
          } catch {
            // Ignore transient coins poll errors
          }
        }
      }, 650);
    };

    const stopFallbackSync = () => {
      if (fallbackTimerRef.current !== null) {
        window.clearInterval(fallbackTimerRef.current);
        fallbackTimerRef.current = null;
      }
    };

    const connect = () => {
      if (closedByEffect) return;
      try {
        const ws = new WebSocket(resolveWsUrl());
        wsRef.current = ws;

        ws.onopen = () => {
          wsFailCount = 0;
          setWsConnected(true);
          stopFallbackSync();
        };

        ws.onmessage = (ev) => {
          try {
            const msg = JSON.parse(ev.data);
            if (msg.type === 'rocket_state' || msg.type === 'rocket_tick') {
              setRocket(msg.data as RocketState);
            } else if (msg.type === 'coin_update') {
              const updated = msg.data as MemecoinSummary;
              setCoins((prev) =>
                prev.map((c) => (c.id === updated.id ? { ...c, ...updated } : c))
              );
            }
          } catch {
            // Ignore malformed WS message
          }
        };

        ws.onerror = () => {
          setWsConnected(false);
          startFallbackSync();
        };

        ws.onclose = () => {
          setWsConnected(false);
          startFallbackSync();
          if (!closedByEffect) {
            wsFailCount += 1;
            const delay = wsFailCount <= 2 ? 3000 : 15000;
            reconnectTimer = window.setTimeout(connect, delay);
          }
        };
      } catch {
        setWsConnected(false);
        startFallbackSync();
      }
    };

    connect();

    return () => {
      closedByEffect = true;
      stopFallbackSync();
      if (reconnectTimer !== null) window.clearTimeout(reconnectTimer);
      wsRef.current?.close();
    };
  }, []);

  if (loading) {
    return <SplashScreen />;
  }

  if (loadError || !user || !catalog) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-black px-6 text-center">
        <div className="w-full max-w-sm rounded-3xl border border-white/10 bg-zinc-900 p-6">
          <h1 className="text-lg font-bold text-white">Ошибка подключения</h1>
          <p className="mt-2 text-xs leading-relaxed text-zinc-400">
            {loadError || 'Профиль недоступен. Откройте Mini App через Telegram-бота.'}
          </p>
          <button
            type="button"
            onClick={() => {
              setLoading(true);
              loadInitialData();
            }}
            className="mt-5 h-12 w-full rounded-2xl bg-white text-sm font-bold text-black"
          >
            Повторить
          </button>
        </div>
      </div>
    );
  }

  const navItems: Array<{ id: AppTab; label: string; icon: typeof Home }> = [
    { id: 'home', label: 'Главная', icon: Home },
    { id: 'games', label: 'Игры', icon: Rocket },
    { id: 'upgrader', label: 'Апгрейдер', icon: Sparkles },
    { id: 'profile', label: 'Профиль', icon: User },
  ];

  return (
    <div className="min-h-screen bg-black text-zinc-100 pb-24">
      {/* Compact Top Bar */}
      <header className="sticky top-0 z-30 border-b border-white/10 bg-black/85 backdrop-blur-md pt-safe">
        <div className="mx-auto flex h-13 max-w-5xl items-center justify-between px-4">
          <button
            type="button"
            onClick={() => setTab('home')}
            className="flex min-h-[40px] items-center gap-2.5 text-left"
          >
            <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-white text-black font-bold text-xs">
              N
            </div>
            <span className="text-sm font-bold tracking-tight text-white">New NFT</span>
          </button>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setTab('exchange')}
              className="flex min-h-[36px] items-center gap-1.5 rounded-2xl border border-white/10 bg-zinc-900 px-3 font-mono-num text-xs font-semibold text-white"
            >
              <span>{formatTon(user.balance_tons, 2)} TON</span>
            </button>
            <button
              type="button"
              onClick={() => setTab('profile')}
              className="flex min-h-[36px] items-center gap-2 rounded-2xl border border-white/10 bg-zinc-900 px-3 font-mono-num text-xs font-semibold text-zinc-200"
            >
              <span>{formatStars(user.balance_stars)} ⭐</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Canvas */}
      <main className="mx-auto max-w-5xl px-4 pt-4">
        {tab === 'home' && (
          <div className="space-y-4">
            {/* Compact Profile Strip */}
            <section className="flex items-center justify-between rounded-3xl border border-white/10 bg-zinc-900/90 p-4">
              <div className="flex min-w-0 items-center gap-3">
                <img
                  src={resolveAssetUrl(user.avatar_url)}
                  alt={user.first_name}
                  className="h-12 w-12 shrink-0 rounded-full border border-white/15 bg-zinc-800 object-cover"
                />
                <div className="min-w-0">
                  <p className="truncate text-sm font-bold text-white">{user.first_name}</p>
                  <p className="mt-0.5 font-mono-num text-xs text-zinc-400">
                    Уровень {user.level} · NFT: {collection.length}
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setTab('profile')}
                className="flex h-11 items-center gap-1 rounded-2xl border border-white/10 bg-zinc-950 px-3.5 text-xs font-semibold text-zinc-200"
              >
                <span>Профиль</span>
                <ChevronRight className="h-3.5 w-3.5" />
              </button>
            </section>

            {/* Featured Large Button: Crypto Exchange */}
            <button
              type="button"
              onClick={() => setTab('exchange')}
              className="group relative flex w-full flex-col justify-between overflow-hidden rounded-[28px] border border-white/15 bg-gradient-to-br from-zinc-100 to-zinc-300 p-6 text-left text-black shadow-2xl transition-transform active:scale-[0.985]"
            >
              <div className="flex w-full items-start justify-between">
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-black text-white">
                  <CandleIcon className="h-6 w-6" />
                </div>
                <span className="rounded-xl bg-black/10 px-3 py-1 font-mono-num text-xs font-bold text-black">
                  {coins.length} монет
                </span>
              </div>
              <div className="mt-6 flex items-end justify-between gap-4">
                <div>
                  <h1 className="text-2xl font-extrabold tracking-tight text-black">
                    Криптобиржа
                  </h1>
                  <p className="mt-1 text-xs font-medium text-zinc-700">
                    Обмен ⭐ ↔ TON · Мемкоины · Свечные графики и сделки
                  </p>
                </div>
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-black text-white transition-transform group-hover:translate-x-0.5">
                  <ChevronRight className="h-5 w-5" />
                </div>
              </div>
            </button>

            {/* Quick Action Grid */}
            <section className="grid grid-cols-2 gap-3 lg:grid-cols-4">
              <button
                type="button"
                onClick={() => setTab('games')}
                className="flex min-h-[132px] flex-col justify-between rounded-3xl border border-white/10 bg-zinc-900/90 p-4 text-left transition-colors hover:border-white/25 active:scale-[0.98]"
              >
                <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-zinc-800 text-white">
                  <Rocket className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-sm font-bold text-white">Ракетка</p>
                  <p className="mt-0.5 font-mono-num text-xs text-zinc-400">
                    {rocket.phase === 'flying'
                      ? `В полёте ${rocket.multiplier.toFixed(2)}x`
                      : rocket.phase === 'betting'
                      ? `Старт ${rocket.countdown_sec.toFixed(0)}с`
                      : `Краш ${(rocket.crash_point || 1).toFixed(2)}x`}
                  </p>
                </div>
              </button>

              <button
                type="button"
                onClick={() => setTab('upgrader')}
                className="flex min-h-[132px] flex-col justify-between rounded-3xl border border-white/10 bg-zinc-900/90 p-4 text-left transition-colors hover:border-white/25 active:scale-[0.98]"
              >
                <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-zinc-800 text-white">
                  <Sparkles className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-sm font-bold text-white">Апгрейдер</p>
                  <p className="mt-0.5 text-xs text-zinc-400">Улучшить NFT</p>
                </div>
              </button>

              <button
                type="button"
                onClick={() => setTab('profile')}
                className="flex min-h-[132px] flex-col justify-between rounded-3xl border border-white/10 bg-zinc-900/90 p-4 text-left transition-colors hover:border-white/25 active:scale-[0.98]"
              >
                <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-zinc-800 text-white">
                  <User className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-sm font-bold text-white">Профиль</p>
                  <p className="mt-0.5 font-mono-num text-xs text-zinc-400">
                    {collection.length} подарков
                  </p>
                </div>
              </button>

              <button
                type="button"
                onClick={() => setAuctionModalOpen(true)}
                className="flex min-h-[132px] flex-col justify-between rounded-3xl border border-white/10 bg-zinc-900/90 p-4 text-left transition-colors hover:border-white/25 active:scale-[0.98]"
              >
                <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-zinc-800 text-zinc-300">
                  <Gavel className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-sm font-bold text-white">Аукцион</p>
                  <p className="mt-0.5 text-xs text-zinc-500">В разработке</p>
                </div>
              </button>
            </section>
          </div>
        )}

        {tab === 'games' && (
          <RocketView
            user={user}
            collection={collection}
            catalog={catalog}
            rocket={rocket}
            wsConnected={wsConnected}
            onSync={(nextUser, nextColl) => {
              setUser(nextUser);
              setCollection(nextColl);
            }}
            onRocketUpdate={setRocket}
          />
        )}

        {tab === 'upgrader' && (
          <UpgraderView
            user={user}
            collection={collection}
            catalog={catalog}
            onSync={(nextUser, nextColl) => {
              setUser(nextUser);
              setCollection(nextColl);
            }}
          />
        )}

        {tab === 'profile' && (
          <ProfileView
            user={user}
            collection={collection}
            onGoUpgrader={() => setTab('upgrader')}
            onGoExchange={() => setTab('exchange')}
          />
        )}

        {tab === 'exchange' && (
          <ExchangeView
            user={user}
            catalog={catalog}
            coins={coins}
            onRefreshAll={refreshCoins}
            onUserPatch={(patch) =>
              setUser((prev) => (prev ? { ...prev, ...patch } : prev))
            }
          />
        )}
      </main>

      {/* Fixed Bottom Navigation Bar */}
      <nav
        aria-label="Основная навигация"
        className="fixed bottom-0 left-0 right-0 z-40 border-t border-white/10 bg-zinc-950/90 backdrop-blur-xl pb-safe"
      >
        <div className="mx-auto grid h-16 max-w-5xl grid-cols-4 items-center px-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = tab === item.id;
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => setTab(item.id)}
                className="flex min-h-[44px] flex-col items-center justify-center gap-1 rounded-2xl transition-colors"
              >
                <Icon
                  className={`h-[22px] w-[22px] transition-colors ${
                    active ? 'text-white' : 'text-zinc-500'
                  }`}
                  strokeWidth={active ? 2.4 : 1.8}
                />
                <span
                  className={`text-[10px] font-semibold tracking-tight ${
                    active ? 'text-white' : 'text-zinc-500'
                  }`}
                >
                  {item.label}
                </span>
              </button>
            );
          })}
        </div>
      </nav>

      {/* Auction Unavailable Modal */}
      {auctionModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-sm">
          <div className="w-full max-w-sm rounded-3xl border border-white/15 bg-zinc-900 p-6 text-center">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-zinc-800 text-white">
              <Gavel className="h-6 w-6" />
            </div>
            <h3 className="mt-4 text-base font-bold text-white">Аукцион</h3>
            <p className="mt-2 text-xs leading-relaxed text-zinc-400">
              Аукцион пока не доступен и находится на этапе разработки.
            </p>
            <button
              type="button"
              onClick={() => setAuctionModalOpen(false)}
              className="mt-5 flex h-11 w-full items-center justify-center gap-1.5 rounded-2xl bg-white text-xs font-bold text-black"
            >
              <X className="h-4 w-4" />
              <span>Понятно</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
