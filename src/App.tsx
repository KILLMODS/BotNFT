import { useCallback, useEffect, useRef, useState } from 'react';
import {
  Bomb,
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
import { MinesView } from './components/MinesView';
import { ExchangeView } from './components/ExchangeView';
import type {
  AppTab,
  CatalogData,
  CollectionItem,
  GameSubMode,
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
  const [gameMode, setGameMode] = useState<GameSubMode>('rocket');
  const [auctionModalOpen, setAuctionModalOpen] = useState(false);

  const [user, setUser] = useState<UserProfile | null>(null);
  const [collection, setCollection] = useState<CollectionItem[]>([]);
  const [catalog, setCatalog] = useState<CatalogData | null>(null);
  const [coins, setCoins] = useState<MemecoinSummary[]>([]);
  const [rocket, setRocket] = useState<RocketState>(INITIAL_ROCKET);
  const [wsConnected, setWsConnected] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const fallbackTimerRef = useRef<number | null>(null);
  const tabRef = useRef<AppTab>(tab);
  tabRef.current = tab;
  const lastBgTickRef = useRef<number>(0);

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
      tg.setHeaderColor?.('#040507');
      tg.setBackgroundColor?.('#040507');
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
            if (msg.type === 'rocket_state') {
              const incoming = msg.data as RocketState;
              if (tabRef.current === 'games' || incoming.phase !== 'betting') {
                setRocket(incoming);
              } else {
                const now = Date.now();
                if (now - lastBgTickRef.current >= 900) {
                  lastBgTickRef.current = now;
                  setRocket(incoming);
                }
              }
            } else if (msg.type === 'rocket_tick') {
              if (tabRef.current === 'games') {
                setRocket(msg.data as RocketState);
              } else if (tabRef.current === 'home') {
                const now = Date.now();
                if (now - lastBgTickRef.current >= 800) {
                  lastBgTickRef.current = now;
                  setRocket(msg.data as RocketState);
                }
              }
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
      <div className="flex min-h-screen flex-col items-center justify-center px-6 text-center">
        <div className="glass-surface w-full max-w-sm rounded-[28px] p-6">
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
            className="mt-5 h-12 w-full rounded-2xl bg-white text-sm font-bold text-black transition-transform active:scale-[0.98]"
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

  const openGame = (mode: GameSubMode) => {
    setGameMode(mode);
    setTab('games');
  };

  return (
    <div className="min-h-screen text-zinc-100 pb-28">
      {/* Liquid Glass Top Header */}
      <header className="sticky top-0 z-30 border-b border-white/[0.07] bg-[#06070a]/75 backdrop-blur-2xl pt-safe">
        <div className="mx-auto flex h-13 max-w-5xl items-center justify-between px-4">
          <button
            type="button"
            onClick={() => setTab('home')}
            className="flex min-h-[40px] items-center gap-2.5 text-left"
          >
            <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-white text-xs font-extrabold text-black shadow-sm">
              N
            </div>
            <span className="text-sm font-bold tracking-tight text-white">New NFT</span>
          </button>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setTab('exchange')}
              className="glass-chip flex min-h-[34px] items-center gap-1.5 rounded-full px-3 font-mono-num text-xs font-semibold text-white transition-transform active:scale-95"
            >
              <span>{formatTon(user.balance_tons, 2)} TON</span>
            </button>
            <button
              type="button"
              onClick={() => setTab('profile')}
              className="glass-chip flex min-h-[34px] items-center gap-1.5 rounded-full px-3 font-mono-num text-xs font-semibold text-zinc-200 transition-transform active:scale-95"
            >
              <span>{formatStars(user.balance_stars)} ⭐</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Canvas */}
      <main className="mx-auto max-w-5xl px-4 pt-4">
        {tab === 'home' && (
          <div className="space-y-3.5">
            {/* Compact Profile Strip */}
            <section className="glass-surface flex items-center justify-between rounded-[26px] p-3.5">
              <div className="flex min-w-0 items-center gap-3">
                <img
                  src={resolveAssetUrl(user.avatar_url)}
                  alt={user.first_name}
                  className="h-12 w-12 shrink-0 rounded-full border border-white/20 bg-zinc-900 object-cover"
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
                className="glass-chip flex h-10 items-center gap-1 rounded-2xl px-3.5 text-xs font-semibold text-zinc-100 transition-transform active:scale-95"
              >
                <span>Профиль</span>
                <ChevronRight className="h-3.5 w-3.5 text-zinc-400" />
              </button>
            </section>

            {/* Featured Light Liquid Glass Card: Crypto Exchange */}
            <button
              type="button"
              onClick={() => setTab('exchange')}
              className="glass-hero-light group relative flex w-full flex-col justify-between overflow-hidden rounded-[30px] p-5 text-left text-black transition-transform active:scale-[0.985]"
            >
              {/* Subtle translucent candlestick chart silhouette */}
              <svg
                aria-hidden="true"
                viewBox="0 0 220 120"
                className="pointer-events-none absolute top-0 right-0 h-full w-3/5 opacity-25"
                fill="none"
              >
                <path
                  d="M10 92 Q 55 84, 88 64 T 155 44 T 212 22"
                  stroke="#0f172a"
                  strokeWidth="2"
                  strokeLinecap="round"
                />
                <g fill="#0f172a">
                  <rect x="44" y="56" width="5" height="24" rx="2" />
                  <rect x="46" y="48" width="1.2" height="38" />
                  <rect x="64" y="44" width="5" height="28" rx="2" />
                  <rect x="66" y="38" width="1.2" height="42" />
                  <rect x="84" y="50" width="5" height="20" rx="2" opacity="0.55" />
                  <rect x="104" y="38" width="5" height="26" rx="2" />
                  <rect x="106" y="30" width="1.2" height="42" />
                  <rect x="124" y="28" width="5" height="28" rx="2" />
                  <rect x="144" y="34" width="5" height="20" rx="2" opacity="0.55" />
                  <rect x="164" y="22" width="5" height="26" rx="2" />
                  <rect x="166" y="14" width="1.2" height="42" />
                  <rect x="184" y="16" width="5" height="24" rx="2" />
                </g>
              </svg>

              <div className="relative z-10 flex w-full items-start justify-between">
                <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-black/90 text-white shadow-md">
                  <CandleIcon className="h-5 w-5" strokeWidth={1.9} />
                </div>
                <span className="rounded-full border border-black/10 bg-black/10 px-3 py-1 font-mono-num text-xs font-bold text-zinc-900 backdrop-blur-md">
                  {coins.length} монет
                </span>
              </div>

              <div className="relative z-10 mt-6 flex items-end justify-between gap-4">
                <div>
                  <h1 className="text-2xl font-extrabold tracking-tight text-zinc-950">
                    Криптобиржа
                  </h1>
                  <p className="mt-1 text-xs font-medium text-zinc-700">
                    Обмен ⭐ ↔ TON · Мемкоины · Свечные графики и сделки
                  </p>
                </div>
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-black text-white shadow-md transition-transform group-hover:translate-x-0.5">
                  <ChevronRight className="h-5 w-5" />
                </div>
              </div>
            </button>

            {/* Restrained Dark Liquid Glass Bento Grid */}
            <section className="grid grid-cols-2 gap-3 lg:grid-cols-6">
              {/* Rocket Tile */}
              <button
                type="button"
                onClick={() => openGame('rocket')}
                className="glass-surface group relative flex min-h-[136px] flex-col justify-between overflow-hidden rounded-[26px] p-4 text-left transition-all hover:border-white/25 active:scale-[0.98] lg:col-span-2"
              >
                <svg
                  aria-hidden="true"
                  viewBox="0 0 110 110"
                  className="pointer-events-none absolute -right-2 -bottom-2 h-24 w-24 opacity-[0.11] transition-opacity group-hover:opacity-[0.18]"
                  fill="none"
                >
                  <path d="M18 92 Q 52 72, 86 20" stroke="white" strokeWidth="2.5" strokeDasharray="4 4" />
                  <path d="M88 18 L66 26 L80 40 Z" fill="white" />
                </svg>

                <div className="glass-chip flex h-10 w-10 items-center justify-center rounded-2xl text-white">
                  <Rocket className="h-5 w-5" strokeWidth={1.8} />
                </div>
                <div className="relative z-10">
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

              {/* Mines Tile (New) */}
              <button
                type="button"
                onClick={() => openGame('mines')}
                className="glass-surface group relative flex min-h-[136px] flex-col justify-between overflow-hidden rounded-[26px] p-4 text-left transition-all hover:border-white/25 active:scale-[0.98] lg:col-span-2"
              >
                <svg
                  aria-hidden="true"
                  viewBox="0 0 100 100"
                  className="pointer-events-none absolute -right-1 -bottom-1 h-24 w-24 opacity-[0.1] transition-opacity group-hover:opacity-[0.17]"
                  fill="none"
                >
                  <rect x="20" y="20" width="16" height="16" rx="4" fill="white" />
                  <rect x="42" y="20" width="16" height="16" rx="4" stroke="white" strokeWidth="2" />
                  <rect x="64" y="20" width="16" height="16" rx="4" fill="white" />
                  <rect x="20" y="42" width="16" height="16" rx="4" stroke="white" strokeWidth="2" />
                  <circle cx="50" cy="50" r="8" fill="white" />
                  <rect x="64" y="42" width="16" height="16" rx="4" fill="white" />
                  <rect x="20" y="64" width="16" height="16" rx="4" fill="white" />
                  <rect x="42" y="64" width="16" height="16" rx="4" fill="white" />
                  <rect x="64" y="64" width="16" height="16" rx="4" stroke="white" strokeWidth="2" />
                </svg>

                <div className="glass-chip flex h-10 w-10 items-center justify-center rounded-2xl text-white">
                  <Bomb className="h-5 w-5" strokeWidth={1.8} />
                </div>
                <div className="relative z-10">
                  <p className="text-sm font-bold text-white">Мины</p>
                  <p className="mt-0.5 text-xs text-zinc-400">Поле 5×5 · Stars и NFT</p>
                </div>
              </button>

              {/* Upgrader Tile */}
              <button
                type="button"
                onClick={() => setTab('upgrader')}
                className="glass-surface group relative flex min-h-[136px] flex-col justify-between overflow-hidden rounded-[26px] p-4 text-left transition-all hover:border-white/25 active:scale-[0.98] lg:col-span-2"
              >
                <svg
                  aria-hidden="true"
                  viewBox="0 0 110 110"
                  className="pointer-events-none absolute -right-2 -bottom-2 h-24 w-24 opacity-[0.1] transition-opacity group-hover:opacity-[0.17]"
                  fill="none"
                >
                  <polygon points="55,14 90,34 90,74 55,94 20,74 20,34" stroke="white" strokeWidth="2.2" />
                  <polygon points="55,32 74,43 74,65 55,76 36,65 36,43" stroke="white" strokeWidth="1.8" />
                </svg>

                <div className="glass-chip flex h-10 w-10 items-center justify-center rounded-2xl text-white">
                  <Sparkles className="h-5 w-5" strokeWidth={1.8} />
                </div>
                <div className="relative z-10">
                  <p className="text-sm font-bold text-white">Апгрейдер</p>
                  <p className="mt-0.5 text-xs text-zinc-400">Улучшить NFT</p>
                </div>
              </button>

              {/* Profile Tile */}
              <button
                type="button"
                onClick={() => setTab('profile')}
                className="glass-surface group relative flex min-h-[136px] flex-col justify-between overflow-hidden rounded-[26px] p-4 text-left transition-all hover:border-white/25 active:scale-[0.98] lg:col-span-3"
              >
                <svg
                  aria-hidden="true"
                  viewBox="0 0 110 110"
                  className="pointer-events-none absolute -right-2 -bottom-2 h-24 w-24 opacity-[0.1] transition-opacity group-hover:opacity-[0.17]"
                  fill="none"
                >
                  <circle cx="55" cy="40" r="16" fill="white" />
                  <path d="M26 88 C26 68, 84 68, 84 88" fill="white" />
                </svg>

                <div className="glass-chip flex h-10 w-10 items-center justify-center rounded-2xl text-white">
                  <User className="h-5 w-5" strokeWidth={1.8} />
                </div>
                <div className="relative z-10">
                  <p className="text-sm font-bold text-white">Профиль</p>
                  <p className="mt-0.5 font-mono-num text-xs text-zinc-400">
                    {collection.length} подарков
                  </p>
                </div>
              </button>

              {/* Auction Tile */}
              <button
                type="button"
                onClick={() => setAuctionModalOpen(true)}
                className="glass-surface group relative col-span-2 flex min-h-[108px] flex-row items-center justify-between overflow-hidden rounded-[26px] p-4 text-left transition-all hover:border-white/25 active:scale-[0.98] lg:col-span-3 lg:min-h-[136px] lg:flex-col lg:items-start"
              >
                <svg
                  aria-hidden="true"
                  viewBox="0 0 110 110"
                  className="pointer-events-none absolute -right-1 -bottom-2 h-24 w-24 opacity-[0.09] transition-opacity group-hover:opacity-[0.15]"
                  fill="none"
                >
                  <rect x="44" y="24" width="32" height="16" rx="4" transform="rotate(-30 44 24)" fill="white" />
                  <rect x="52" y="44" width="8" height="36" rx="3" transform="rotate(-30 52 44)" fill="white" />
                  <rect x="24" y="82" width="44" height="8" rx="4" fill="white" />
                </svg>

                <div className="flex items-center gap-3 lg:flex-col lg:items-start lg:gap-0 lg:justify-between lg:h-full">
                  <div className="glass-chip flex h-10 w-10 items-center justify-center rounded-2xl text-zinc-300">
                    <Gavel className="h-5 w-5" strokeWidth={1.8} />
                  </div>
                  <div className="relative z-10 lg:mt-auto">
                    <p className="text-sm font-bold text-white">Аукцион</p>
                    <p className="mt-0.5 text-xs text-zinc-500">В разработке</p>
                  </div>
                </div>
                <ChevronRight className="relative z-10 h-4 w-4 text-zinc-500 lg:hidden" />
              </button>
            </section>
          </div>
        )}

        {tab === 'games' && (
          <div className="space-y-3.5">
            {/* Segmented Mode Switcher: Rocket | Mines */}
            <div className="glass-inset grid grid-cols-2 gap-1 rounded-[22px] p-1">
              <button
                type="button"
                onClick={() => setGameMode('rocket')}
                className={`flex h-10 items-center justify-center gap-2 rounded-[18px] text-xs font-semibold transition-all ${
                  gameMode === 'rocket'
                    ? 'bg-white text-black shadow-sm'
                    : 'text-zinc-400 hover:text-zinc-200'
                }`}
              >
                <Rocket className="h-3.5 w-3.5" />
                <span>Ракетка</span>
              </button>
              <button
                type="button"
                onClick={() => setGameMode('mines')}
                className={`flex h-10 items-center justify-center gap-2 rounded-[18px] text-xs font-semibold transition-all ${
                  gameMode === 'mines'
                    ? 'bg-white text-black shadow-sm'
                    : 'text-zinc-400 hover:text-zinc-200'
                }`}
              >
                <Bomb className="h-3.5 w-3.5" />
                <span>Мины</span>
              </button>
            </div>

            {gameMode === 'rocket' ? (
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
            ) : (
              <MinesView
                user={user}
                collection={collection}
                catalog={catalog}
                onSync={(nextUser, nextColl) => {
                  setUser(nextUser);
                  setCollection(nextColl);
                }}
              />
            )}
          </div>
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

      {/* Floating Apple Liquid Glass Bottom Navigation Capsule */}
      <nav
        aria-label="Основная навигация"
        className="fixed bottom-3 left-3 right-3 z-40 mx-auto max-w-xl"
        style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}
      >
        <div className="glass-dock grid h-16 grid-cols-4 items-center gap-1 rounded-[28px] px-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = tab === item.id;
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => setTab(item.id)}
                className={`flex h-12 flex-col items-center justify-center gap-0.5 rounded-[22px] transition-all ${
                  active ? 'bg-white/[0.11] text-white' : 'text-zinc-400 hover:text-zinc-200'
                }`}
              >
                <Icon
                  className={`h-5 w-5 transition-colors ${
                    active ? 'text-white' : 'text-zinc-400'
                  }`}
                  strokeWidth={active ? 2.2 : 1.75}
                />
                <span
                  className={`text-[10px] font-semibold tracking-tight ${
                    active ? 'text-white' : 'text-zinc-400'
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
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-md">
          <div className="glass-surface w-full max-w-sm rounded-[28px] p-6 text-center">
            <div className="glass-chip mx-auto flex h-12 w-12 items-center justify-center rounded-2xl text-white">
              <Gavel className="h-6 w-6" />
            </div>
            <h3 className="mt-4 text-base font-bold text-white">Аукцион</h3>
            <p className="mt-2 text-xs leading-relaxed text-zinc-400">
              Аукцион пока не доступен и находится на этапе разработки.
            </p>
            <button
              type="button"
              onClick={() => setAuctionModalOpen(false)}
              className="mt-5 flex h-11 w-full items-center justify-center gap-1.5 rounded-2xl bg-white text-xs font-bold text-black transition-transform active:scale-[0.98]"
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
