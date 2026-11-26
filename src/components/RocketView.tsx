import { useMemo, useState } from 'react';
import { Check, Rocket, Sparkles, Star, Users } from 'lucide-react';
import { apiRequest, formatStars, getTelegramWebApp, resolveAssetUrl } from '../api';
import type { CatalogData, CollectionItem, RocketState, UserProfile } from '../types';

interface RocketViewProps {
  user: UserProfile;
  collection: CollectionItem[];
  catalog: CatalogData;
  rocket: RocketState;
  wsConnected: boolean;
  onSync: (user: UserProfile, collection: CollectionItem[]) => void;
  onRocketUpdate: (next: RocketState) => void;
}

const FALLBACK_BASE_GIFTS = [
  { key: 'signet_ring', name: 'Signet Ring (Перстень)', stars: 3500, image_url: '/api/assets/gift/signet_ring' },
  { key: 'briefcase', name: 'Loot Bag (Дипломат)', stars: 6800, image_url: '/api/assets/gift/briefcase' },
  { key: 'sunglasses', name: "Durov's Glasses (Очки Дурова)", stars: 9500, image_url: '/api/assets/gift/sunglasses' },
  { key: 'gem_crystal', name: 'Astral Shard (Кристалл Алмаз)', stars: 12000, image_url: '/api/assets/gift/gem_crystal' },
  { key: 'heart_lock_key', name: 'Heart Locket (Сердце-замок)', stars: 22000, image_url: '/api/assets/gift/heart_lock_key' },
  { key: 'hockey_mask', name: 'Hockey Mask (Хоккейная маска)', stars: 26000, image_url: '/api/assets/gift/hockey_mask' },
  { key: 'cap_tg', name: "Durov's Cap (Кепка Дурова)", stars: 38000, image_url: '/api/assets/gift/cap_tg' },
  { key: 'bonded_ring', name: 'Bonded Ring (Кольцо)', stars: 40000, image_url: '/api/assets/gift/bonded_ring' },
  { key: 'hero_figure', name: 'Durov Figure (Фигурка Дурова)', stars: 42000, image_url: '/api/assets/gift/hero_figure' },
  { key: 'trophy_cup', name: 'Algorithm Cup (Кубок Чемпиона)', stars: 85000, image_url: '/api/assets/gift/trophy_cup' },
  { key: 'pepe_heart', name: 'Plush Pepe (Пепе с сердцем)', stars: 480000, image_url: '/api/assets/gift/pepe_heart' },
];

interface PrecomputedCandidate {
  natStars: number;
  title: string;
  backdropName: string;
  imageUrl: string;
  centerHex: string;
  edgeHex: string;
}

function buildSortedBasePool(catalog: CatalogData) {
  return (catalog.base_gifts && catalog.base_gifts.length > 0
    ? catalog.base_gifts
    : FALLBACK_BASE_GIFTS
  )
    .filter((g) => g.stars < 400000)
    .sort((a, b) => a.stars - b.stars);
}

function buildUpgradedCandidates(catalog: CatalogData, seed: number): PrecomputedCandidate[] {
  const list: PrecomputedCandidate[] = [];
  for (const g of catalog.upgradable_gifts) {
    const models = catalog.models_by_gift[g.key] || [];
    if (models.length === 0) continue;
    const mdef = models[Math.abs(seed) % models.length];
    const base = g.key === 'pepe_heart' ? g.base_stars : g.base_stars + g.upgrade_cost;
    for (const bdef of catalog.backdrops) {
      const monoMult =
        mdef.color_family &&
        bdef.color_family &&
        bdef.key !== 'rainbow' &&
        mdef.color_family === bdef.color_family
          ? catalog.mono_price_mult || 6
          : 1;
      const raw = base * bdef.price_mult * mdef.price_mult * monoMult * 1.5;
      let natStars = Math.max(150000, Math.round(raw / 5000) * 5000);
      if (g.key === 'pepe_heart') natStars = Math.max(750000, Math.round(raw / 10000) * 10000);
      else if (g.key === 'trophy_cup') natStars = Math.max(375000, Math.round(raw / 5000) * 5000);
      else if (g.key === 'heart_lock_key' || g.key === 'bonded_ring') natStars = Math.max(225000, Math.round(raw / 5000) * 5000);
      list.push({
        natStars,
        title: mdef.name,
        backdropName: `${g.title} · ${bdef.name}`,
        imageUrl: mdef.image_url,
        centerHex: bdef.center_hex,
        edgeHex: bdef.edge_hex,
      });
    }
  }
  return list.sort((a, b) => a.natStars - b.natStars);
}

function lookupNftRewardFast(
  basePool: ReturnType<typeof buildSortedBasePool>,
  upgradedCandidates: PrecomputedCandidate[],
  targetValue: number,
  sourceStars: number,
  sourceIsUpgraded: boolean
) {
  if (!sourceIsUpgraded && targetValue < 400000) {
    let bestBase = null as (typeof basePool)[number] | null;
    for (const g of basePool) {
      if (g.stars <= targetValue) bestBase = g;
    }
    if (bestBase && bestBase.stars > sourceStars) {
      return {
        isUpgraded: false,
        title: bestBase.name,
        subtitle: 'Базовый NFT',
        stars: bestBase.stars,
        imageUrl: bestBase.image_url,
        centerHex: null as string | null,
        edgeHex: null as string | null,
      };
    }
    if (targetValue < 150000) {
      const nextBase =
        basePool.find((g) => g.stars >= Math.max(sourceStars, targetValue)) ||
        basePool[basePool.length - 1];
      return {
        isUpgraded: false,
        title: nextBase.name,
        subtitle: 'Базовый NFT',
        stars: nextBase.stars,
        imageUrl: nextBase.image_url,
        centerHex: null as string | null,
        edgeHex: null as string | null,
      };
    }
  }

  const minFloor = !sourceIsUpgraded ? 400000 : Math.max(150000, sourceStars);
  const rewardStars = Math.max(minFloor, Math.round(targetValue / 5000) * 5000);
  if (upgradedCandidates.length === 0) {
    return {
      isUpgraded: true,
      title: 'Улучшенный NFT',
      subtitle: 'Уникальная модель и фон',
      stars: rewardStars,
      imageUrl: '/api/assets/gift/pepe_heart',
      centerHex: '#363738',
      edgeHex: '#0E0F0F',
    };
  }
  let chosen = upgradedCandidates[0];
  let bestDiff = Math.abs(chosen.natStars - rewardStars);
  for (let i = 1; i < upgradedCandidates.length; i++) {
    const d = Math.abs(upgradedCandidates[i].natStars - rewardStars);
    if (d < bestDiff) {
      bestDiff = d;
      chosen = upgradedCandidates[i];
    }
  }
  return {
    isUpgraded: true,
    title: chosen.title,
    subtitle: chosen.backdropName,
    stars: rewardStars,
    imageUrl: chosen.imageUrl,
    centerHex: chosen.centerHex,
    edgeHex: chosen.edgeHex,
  };
}

export function RocketView({
  user,
  collection,
  catalog,
  rocket,
  wsConnected,
  onSync,
  onRocketUpdate,
}: RocketViewProps) {
  const availableNfts = useMemo(
    () => collection.filter((c) => c.is_listed === 0),
    [collection]
  );

  const [stakeType, setStakeType] = useState<'stars' | 'nft'>('stars');
  const [stakeStars, setStakeStars] = useState<string>('1000');
  const [autoCashoutEnabled, setAutoCashoutEnabled] = useState<boolean>(false);
  const [autoCashout, setAutoCashout] = useState<string>('2.0');
  const [selectedNftId, setSelectedNftId] = useState<number>(() => availableNfts[0]?.id || 0);
  const [busy, setBusy] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [noticeMsg, setNoticeMsg] = useState<string | null>(null);

  const myBet = rocket.bets.find((b) => b.user_id === user.user_id);
  const selectedNft =
    availableNfts.find((n) => n.id === selectedNftId) || availableNfts[0] || null;

  const sortedBasePool = useMemo(() => buildSortedBasePool(catalog), [catalog]);
  const previewSeed = myBet?.stake_type === 'nft' ? myBet.user_id : selectedNft?.id || 0;
  const upgradedCandidates = useMemo(
    () => buildUpgradedCandidates(catalog, previewSeed),
    [catalog, previewSeed]
  );

  const activeNftForPreview = useMemo(() => {
    if (myBet && myBet.stake_type === 'nft' && myBet.status === 'active') {
      const liveMult = rocket.phase === 'flying' ? Math.max(1.25, rocket.multiplier) : 1.5;
      return lookupNftRewardFast(
        sortedBasePool,
        upgradedCandidates,
        Math.round(myBet.stake_stars * liveMult),
        myBet.stake_stars,
        Boolean(myBet.source_is_upgraded)
      );
    }
    if (stakeType === 'nft' && selectedNft) {
      return lookupNftRewardFast(
        sortedBasePool,
        upgradedCandidates,
        Math.round(selectedNft.display_stars * 1.5),
        selectedNft.display_stars,
        selectedNft.is_upgraded
      );
    }
    return null;
  }, [myBet, stakeType, selectedNft, rocket.phase, rocket.multiplier, sortedBasePool, upgradedCandidates]);

  const curveProgress = Math.min(1, Math.log(Math.max(1, rocket.multiplier)) / Math.log(8));
  const curveEndX = 40 + curveProgress * 260;
  const curveEndY = 128 - Math.pow(curveProgress, 1.35) * 98;

  const handlePlaceBet = async () => {
    if (busy) return;
    setErrorMsg(null);
    setNoticeMsg(null);
    setBusy(true);
    try {
      const minAuto = stakeType === 'nft' ? 1.25 : 1.1;
      const parsedAuto = Number(autoCashout || 0);
      const validAutoCashout =
        autoCashoutEnabled && Number.isFinite(parsedAuto) && parsedAuto >= minAuto
          ? Number(parsedAuto.toFixed(2))
          : null;

      const payload =
        stakeType === 'stars'
          ? {
              stake_type: 'stars',
              stake_stars: Number(stakeStars || 0),
              auto_cashout: validAutoCashout,
            }
          : {
              stake_type: 'nft',
              collection_item_id: selectedNft?.id || 0,
              auto_cashout: validAutoCashout,
            };

      const res = await apiRequest<{
        rocket: RocketState;
        user: UserProfile;
        collection: CollectionItem[];
      }>('/api/rocket/bet', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      onRocketUpdate(res.rocket);
      onSync(res.user, res.collection);
      getTelegramWebApp()?.HapticFeedback?.impactOccurred('medium');
      setNoticeMsg('Ставка принята в раунд!');
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Не удалось сделать ставку');
    } finally {
      setBusy(false);
    }
  };

  const handleCashout = async () => {
    if (busy) return;
    setErrorMsg(null);
    setBusy(true);
    try {
      const res = await apiRequest<{
        won: boolean;
        payout_stars: number;
        upgraded: boolean;
        reward_name?: string;
        rocket: RocketState;
        user: UserProfile;
        collection: CollectionItem[];
      }>('/api/rocket/cashout', {
        method: 'POST',
        body: JSON.stringify({}),
      });
      onRocketUpdate(res.rocket);
      onSync(res.user, res.collection);
      getTelegramWebApp()?.HapticFeedback?.notificationOccurred('success');
      setNoticeMsg(
        res.reward_name
          ? `Получен NFT: ${res.reward_name} (${formatStars(res.payout_stars)} ⭐)!`
          : `Забрано ${formatStars(res.payout_stars)} ⭐`
      );
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Не удалось забрать');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-3">
      {/* Compact Flight Stage + Immediate Action Controls */}
      <section className="rounded-3xl border border-white/10 bg-zinc-900/90 p-4">
        <div className="flex items-center justify-between gap-2">
          <div className="min-w-0">
            <h2 className="text-base font-bold tracking-tight text-white">Онлайн Ракетка</h2>
            <p className="truncate text-[11px] text-zinc-400">
              Раунд #{rocket.round_id} · {wsConnected ? 'Live поток' : 'Синхронизация'}
            </p>
          </div>
          <div className="shrink-0 rounded-2xl border border-white/10 bg-black/60 px-3 py-1.5 font-mono-num text-xs font-semibold text-zinc-200">
            {formatStars(user.balance_stars)} ⭐
          </div>
        </div>

        {/* History Strip */}
        <div className="mt-2.5 flex gap-1.5 overflow-x-auto pb-1 no-scrollbar">
          {rocket.history.slice(0, 12).map((h) => (
            <span
              key={`${h.round_id}-${h.crash_point}`}
              className={`shrink-0 rounded-xl border px-2 py-0.5 font-mono-num text-[11px] font-semibold ${
                h.crash_point >= 2
                  ? 'border-white/25 bg-white text-black'
                  : 'border-white/10 bg-zinc-950 text-zinc-400'
              }`}
            >
              {h.crash_point.toFixed(2)}x
            </span>
          ))}
        </div>

        {/* Compact Trajectory Graph */}
        <div className="relative mt-2.5 overflow-hidden rounded-3xl border border-white/10 bg-black p-3">
          <svg viewBox="0 0 340 142" className="h-36 w-full sm:h-40">
            <line x1="24" y1="128" x2="320" y2="128" stroke="rgba(255,255,255,0.1)" />
            <line x1="24" y1="16" x2="24" y2="128" stroke="rgba(255,255,255,0.1)" />
            {rocket.phase !== 'betting' && (
              <>
                <path
                  d={`M 24 128 Q ${(24 + curveEndX) * 0.55} 128 ${curveEndX} ${curveEndY}`}
                  fill="none"
                  stroke={rocket.phase === 'crashed' ? '#71717a' : '#ffffff'}
                  strokeWidth="3.2"
                  strokeLinecap="round"
                />
                <circle
                  cx={curveEndX}
                  cy={curveEndY}
                  r="5"
                  fill={rocket.phase === 'crashed' ? '#71717a' : '#ffffff'}
                />
              </>
            )}
          </svg>

          <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
            {rocket.phase === 'betting' ? (
              <>
                <span className="text-[11px] font-medium uppercase tracking-widest text-zinc-400">
                  Приём ставок
                </span>
                <span className="mt-0.5 font-mono-num text-3xl font-bold text-white sm:text-4xl">
                  {rocket.countdown_sec.toFixed(1)}s
                </span>
              </>
            ) : rocket.phase === 'flying' ? (
              <>
                <span className="text-[11px] font-medium uppercase tracking-widest text-zinc-400">
                  В полёте
                </span>
                <span className="mt-0.5 font-mono-num text-4xl font-extrabold tracking-tight text-white sm:text-5xl">
                  {rocket.multiplier.toFixed(2)}x
                </span>
              </>
            ) : (
              <>
                <span className="text-[11px] font-semibold uppercase tracking-widest text-zinc-500">
                  Краш
                </span>
                <span className="mt-0.5 font-mono-num text-4xl font-extrabold tracking-tight text-zinc-400 sm:text-5xl">
                  {(rocket.crash_point || rocket.multiplier).toFixed(2)}x
                </span>
              </>
            )}
          </div>
        </div>

        {/* Live Evolving NFT Target Card (shown during NFT bet or NFT mode) */}
        {activeNftForPreview && (
          <div className="mt-2.5 flex items-center justify-between gap-3 rounded-2xl border border-white/10 bg-zinc-950 p-3">
            <div className="flex min-w-0 items-center gap-2.5">
              <div
                className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-white/10 bg-zinc-900 p-1"
                style={
                  activeNftForPreview.centerHex && activeNftForPreview.edgeHex
                    ? {
                        background: `radial-gradient(circle, ${activeNftForPreview.centerHex}, ${activeNftForPreview.edgeHex})`,
                      }
                    : undefined
                }
              >
                <img
                  src={resolveAssetUrl(activeNftForPreview.imageUrl)}
                  alt={activeNftForPreview.title}
                  className="h-9 w-9 object-contain"
                />
              </div>
              <div className="min-w-0">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-zinc-400">
                  {myBet?.stake_type === 'nft'
                    ? activeNftForPreview.isUpgraded
                      ? 'Текущий улучшенный NFT'
                      : 'Текущий приз NFT'
                    : 'Пример при x1.50 (авто-рост)'}
                </p>
                <p className="truncate text-xs font-bold text-white">
                  {activeNftForPreview.title}
                </p>
                <p className="truncate text-[10px] text-zinc-400">
                  {activeNftForPreview.subtitle}
                </p>
              </div>
            </div>
            <div className="shrink-0 text-right font-mono-num">
              <p className="text-xs font-bold text-white">
                {formatStars(activeNftForPreview.stars)} ⭐
              </p>
              {activeNftForPreview.isUpgraded && (
                <span className="text-[10px] font-semibold text-emerald-400">Upgraded</span>
              )}
            </div>
          </div>
        )}

        {noticeMsg && (
          <div className="mt-2.5 rounded-2xl border border-white/20 bg-zinc-950 p-2.5 text-center text-xs font-medium text-white">
            {noticeMsg}
          </div>
        )}
        {errorMsg && (
          <div className="mt-2.5 rounded-2xl border border-rose-500/30 bg-rose-950/30 p-2.5 text-center text-xs text-rose-300">
            {errorMsg}
          </div>
        )}

        {/* Controls right below Stage */}
        {myBet && myBet.status === 'active' && rocket.phase === 'flying' ? (
          <button
            type="button"
            disabled={busy || (myBet.stake_type === 'nft' && rocket.multiplier < 1.25)}
            onClick={handleCashout}
            className="mt-3 flex h-12 w-full items-center justify-center gap-2 rounded-2xl bg-white text-sm font-bold text-black transition-transform active:scale-[0.98] disabled:opacity-45"
          >
            <Rocket className="h-4 w-4" />
            <span>
              {myBet.stake_type === 'nft'
                ? rocket.multiplier >= 1.25
                  ? `Забрать NFT · ${activeNftForPreview?.title || ''} (${rocket.multiplier.toFixed(2)}x)`
                  : `Забор NFT открывается с x1.25`
                : `Забрать ${formatStars(Math.round(myBet.stake_stars * rocket.multiplier))} ⭐ (${rocket.multiplier.toFixed(2)}x)`}
            </span>
          </button>
        ) : (
          <div className="mt-3 space-y-3 rounded-3xl border border-white/10 bg-zinc-950 p-3.5">
            {/* Two Modes Only: Stars vs NFT */}
            <div className="grid grid-cols-2 gap-2 rounded-2xl bg-zinc-900 p-1">
              <button
                type="button"
                onClick={() => setStakeType('stars')}
                className={`flex min-h-[40px] items-center justify-center gap-1.5 rounded-xl text-xs font-semibold transition-colors ${
                  stakeType === 'stars' ? 'bg-white text-black' : 'text-zinc-400'
                }`}
              >
                <Star className="h-3.5 w-3.5" />
                <span>Stars</span>
              </button>
              <button
                type="button"
                onClick={() => setStakeType('nft')}
                className={`flex min-h-[40px] items-center justify-center gap-1.5 rounded-xl text-xs font-semibold transition-colors ${
                  stakeType === 'nft' ? 'bg-white text-black' : 'text-zinc-400'
                }`}
              >
                <Sparkles className="h-3.5 w-3.5" />
                <span>NFT</span>
              </button>
            </div>

            {stakeType === 'stars' ? (
              <div>
                <label className="mb-1 block text-[11px] font-medium text-zinc-400">
                  Ставка (Stars ⭐)
                </label>
                <input
                  type="number"
                  min={50}
                  value={stakeStars}
                  onChange={(e) => setStakeStars(e.target.value)}
                  className="h-11 w-full rounded-2xl border border-white/10 bg-black px-3.5 font-mono-num text-sm text-white outline-none focus:border-white/40"
                />
                <div className="mt-1.5 flex gap-1.5">
                  {[500, 2500, 10000, 50000].map((v) => (
                    <button
                      key={v}
                      type="button"
                      onClick={() => setStakeStars(String(v))}
                      className="min-h-[32px] flex-1 rounded-xl border border-white/10 bg-zinc-900 font-mono-num text-[11px] font-semibold text-zinc-300"
                    >
                      {formatStars(v)}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div>
                <div className="mb-2 flex items-center justify-between text-[11px] text-zinc-400">
                  <span>Выберите ваш NFT для полёта</span>
                  <span>Забор с x1.25 · от 400K ⭐ — улучшенные</span>
                </div>
                {availableNfts.length === 0 ? (
                  <p className="rounded-2xl border border-white/10 bg-black p-3 text-xs text-zinc-500">
                    Нет свободных NFT в инвентаре.
                  </p>
                ) : (
                  <div className="flex gap-2 overflow-x-auto pb-1 no-scrollbar">
                    {availableNfts.map((n) => {
                      const active = n.id === selectedNft?.id;
                      return (
                        <button
                          key={n.id}
                          type="button"
                          onClick={() => setSelectedNftId(n.id)}
                          className={`relative flex w-28 shrink-0 flex-col items-center rounded-2xl border p-2.5 text-center transition-colors ${
                            active
                              ? 'border-white bg-zinc-800'
                              : 'border-white/10 bg-black'
                          }`}
                        >
                          {active && (
                            <span className="absolute right-1.5 top-1.5 flex h-4 w-4 items-center justify-center rounded-full bg-white text-black">
                              <Check className="h-2.5 w-2.5" />
                            </span>
                          )}
                          <div
                            className="flex h-11 w-11 items-center justify-center rounded-xl bg-zinc-900 p-1"
                            style={
                              n.backdrop_center_hex && n.backdrop_edge_hex
                                ? {
                                    background: `radial-gradient(circle, ${n.backdrop_center_hex}, ${n.backdrop_edge_hex})`,
                                  }
                                : undefined
                            }
                          >
                            <img
                              src={resolveAssetUrl(n.image_url)}
                              alt={n.name}
                              className="h-9 w-9 object-contain"
                            />
                          </div>
                          <p className="mt-1.5 w-full truncate text-[11px] font-semibold text-white">
                            {n.model_name || n.name}
                          </p>
                          <p className="font-mono-num text-[10px] text-zinc-400">
                            {formatStars(n.display_stars)} ⭐
                          </p>
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            )}

            {/* Shared Auto-Cashout Toggle (Stars & NFT, off by default) */}
            <div className="flex items-center justify-between gap-3 rounded-2xl border border-white/10 bg-black px-3.5 py-2.5">
              <label className="flex cursor-pointer items-center gap-2.5 select-none">
                <input
                  type="checkbox"
                  checked={autoCashoutEnabled}
                  onChange={(e) => setAutoCashoutEnabled(e.target.checked)}
                  className="h-4 w-4 accent-white rounded"
                />
                <div>
                  <p className="text-xs font-semibold text-white">Автовывод</p>
                  <p className="text-[10px] text-zinc-500">
                    {autoCashoutEnabled
                      ? `Сработает от x${stakeType === 'nft' ? '1.25' : '1.10'}`
                      : 'Выкл — забираете вручную'}
                  </p>
                </div>
              </label>

              {autoCashoutEnabled && (
                <div className="flex items-center gap-1.5">
                  <span className="font-mono-num text-xs text-zinc-400">x</span>
                  <input
                    type="number"
                    step="0.05"
                    min={stakeType === 'nft' ? 1.25 : 1.1}
                    value={autoCashout}
                    onChange={(e) => setAutoCashout(e.target.value)}
                    className="h-9 w-20 rounded-xl border border-white/15 bg-zinc-900 px-2.5 text-right font-mono-num text-xs font-bold text-white outline-none focus:border-white/40"
                  />
                </div>
              )}
            </div>

            <button
              type="button"
              disabled={
                busy ||
                rocket.phase !== 'betting' ||
                Boolean(myBet) ||
                (stakeType === 'nft' && !selectedNft)
              }
              onClick={handlePlaceBet}
              className="flex h-12 w-full items-center justify-center rounded-2xl bg-white text-sm font-bold text-black transition-transform active:scale-[0.98] disabled:opacity-40"
            >
              {myBet
                ? 'Ставка в этом раунде уже сделана'
                : rocket.phase !== 'betting'
                ? 'Дождитесь следующего раунда'
                : stakeType === 'nft'
                ? `Запустить ${selectedNft ? selectedNft.model_name || selectedNft.name : 'NFT'}`
                : 'Поставить Stars'}
            </button>
          </div>
        )}
      </section>

      {/* Online Players Bets */}
      <section className="rounded-3xl border border-white/10 bg-zinc-900/80 p-4">
        <div className="mb-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Users className="h-4 w-4 text-zinc-400" />
            <h3 className="text-sm font-semibold text-white">Ставки игроков онлайн</h3>
          </div>
          <span className="font-mono-num text-xs text-zinc-400">{rocket.bets.length} в раунде</span>
        </div>

        {rocket.bets.length === 0 ? (
          <p className="py-4 text-center text-xs text-zinc-500">
            Пока никто не поставил в текущем раунде.
          </p>
        ) : (
          <div className="space-y-2">
            {rocket.bets.map((b) => (
              <div
                key={b.user_id}
                className="flex items-center justify-between gap-2 rounded-2xl border border-white/10 bg-zinc-950 px-3.5 py-2.5"
              >
                <div className="flex min-w-0 items-center gap-2.5">
                  <img
                    src={resolveAssetUrl(b.avatar_url)}
                    alt={b.name}
                    className="h-8 w-8 shrink-0 rounded-full bg-zinc-800 object-cover"
                  />
                  <div className="min-w-0">
                    <p className="truncate text-xs font-semibold text-white">{b.name}</p>
                    <p className="truncate text-[11px] text-zinc-400">
                      {b.stake_type === 'nft'
                        ? `NFT · ${b.item_name || 'Подарок'} (${formatStars(b.stake_stars)} ⭐)`
                        : `${formatStars(b.stake_stars)} ⭐`}
                    </p>
                  </div>
                </div>
                <div className="shrink-0 text-right font-mono-num text-xs font-semibold">
                  {b.status === 'won' ? (
                    <span className="text-white">
                      {b.stake_type === 'nft' && b.target_gift_title
                        ? `${b.target_gift_title} (${b.cashout_mult}x)`
                        : `+${formatStars(b.payout_stars || 0)} ⭐ (${b.cashout_mult}x)`}
                    </span>
                  ) : b.status === 'lost' ? (
                    <span className="text-zinc-500">Краш</span>
                  ) : (
                    <span className="text-zinc-300">В игре</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
