import { useMemo, useState } from 'react';
import { Rocket, Sparkles, Star, Users } from 'lucide-react';
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
  const [autoCashout, setAutoCashout] = useState<string>('2.0');
  const [selectedNftId, setSelectedNftId] = useState<number>(() => availableNfts[0]?.id || 0);
  const [targetGiftKey, setTargetGiftKey] = useState<string>(
    catalog.upgradable_gifts[0]?.key || 'pepe_heart'
  );
  const targetModels = catalog.models_by_gift[targetGiftKey] || [];
  const [targetModelName, setTargetModelName] = useState<string>(
    targetModels[0]?.name || ''
  );
  const [targetBackdropKey, setTargetBackdropKey] = useState<string>(
    catalog.backdrops[0]?.key || 'black'
  );
  const [busy, setBusy] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [noticeMsg, setNoticeMsg] = useState<string | null>(null);

  const myBet = rocket.bets.find((b) => b.user_id === user.user_id);
  const selectedNft =
    availableNfts.find((n) => n.id === selectedNftId) || availableNfts[0] || null;
  const selectedGift =
    catalog.upgradable_gifts.find((g) => g.key === targetGiftKey) ||
    catalog.upgradable_gifts[0];
  const selectedModel =
    targetModels.find((m) => m.name === targetModelName) || targetModels[0] || null;
  const selectedBackdrop =
    catalog.backdrops.find((b) => b.key === targetBackdropKey) ||
    catalog.backdrops[0];

  const nftTargetStars = useMemo(() => {
    if (!selectedGift || !selectedBackdrop) return 0;
    const base =
      selectedGift.key === 'pepe_heart'
        ? selectedGift.base_stars
        : selectedGift.base_stars + selectedGift.upgrade_cost;
    const modelMult = selectedModel ? selectedModel.price_mult : 1.1;
    return Math.max(
      150000,
      Math.round((base * selectedBackdrop.price_mult * modelMult * 1.5) / 5000) * 5000
    );
  }, [selectedGift, selectedModel, selectedBackdrop]);

  const nftRequiredMult = useMemo(() => {
    if (!selectedNft || nftTargetStars <= 0) return 1.5;
    const penalty = catalog.rocket_upgrade_mult_penalty || 1.28;
    return Math.max(
      1.35,
      Number(((nftTargetStars / Math.max(1, selectedNft.display_stars)) * penalty).toFixed(2))
    );
  }, [selectedNft, nftTargetStars, catalog.rocket_upgrade_mult_penalty]);

  const curveProgress = Math.min(1, Math.log(Math.max(1, rocket.multiplier)) / Math.log(8));
  const curveEndX = 40 + curveProgress * 260;
  const curveEndY = 148 - Math.pow(curveProgress, 1.35) * 116;

  const handlePlaceBet = async () => {
    if (busy) return;
    setErrorMsg(null);
    setNoticeMsg(null);
    setBusy(true);
    try {
      const payload =
        stakeType === 'stars'
          ? {
              stake_type: 'stars',
              stake_stars: Number(stakeStars || 0),
              auto_cashout: Number(autoCashout || 0) >= 1.1 ? Number(autoCashout) : null,
            }
          : {
              stake_type: 'nft',
              collection_item_id: selectedNft?.id || 0,
              target_gift_key: targetGiftKey,
              target_model_name: selectedModel?.name,
              target_backdrop_key: selectedBackdrop?.key,
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
        res.upgraded
          ? `NFT улучшен в Ракетке (${formatStars(res.payout_stars)} ⭐)!`
          : `Забрано ${formatStars(res.payout_stars)} ⭐`
      );
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Не удалось забрать');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Flight Stage */}
      <section className="rounded-3xl border border-white/10 bg-zinc-900/90 p-5">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold tracking-tight text-white">Онлайн Ракетка</h2>
            <p className="text-xs text-zinc-400">
              Раунд #{rocket.round_id} · {wsConnected ? 'Live поток' : 'Синхронизация'}
            </p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-black/60 px-3 py-1.5 font-mono-num text-xs font-semibold text-zinc-200">
            {formatStars(user.balance_stars)} ⭐
          </div>
        </div>

        {/* History Strip */}
        <div className="mt-3 flex gap-1.5 overflow-x-auto pb-1 no-scrollbar">
          {rocket.history.slice(0, 12).map((h) => (
            <span
              key={`${h.round_id}-${h.crash_point}`}
              className={`shrink-0 rounded-xl border px-2.5 py-1 font-mono-num text-[11px] font-semibold ${
                h.crash_point >= 2
                  ? 'border-white/25 bg-white text-black'
                  : 'border-white/10 bg-zinc-950 text-zinc-400'
              }`}
            >
              {h.crash_point.toFixed(2)}x
            </span>
          ))}
        </div>

        {/* Trajectory Graph */}
        <div className="relative mt-4 overflow-hidden rounded-3xl border border-white/10 bg-black p-4">
          <svg viewBox="0 0 340 165" className="h-44 w-full">
            <line x1="28" y1="148" x2="320" y2="148" stroke="rgba(255,255,255,0.1)" />
            <line x1="28" y1="18" x2="28" y2="148" stroke="rgba(255,255,255,0.1)" />
            {rocket.phase !== 'betting' && (
              <>
                <path
                  d={`M 28 148 Q ${(28 + curveEndX) * 0.55} 148 ${curveEndX} ${curveEndY}`}
                  fill="none"
                  stroke={rocket.phase === 'crashed' ? '#71717a' : '#ffffff'}
                  strokeWidth="3.5"
                  strokeLinecap="round"
                />
                <circle
                  cx={curveEndX}
                  cy={curveEndY}
                  r="5.5"
                  fill={rocket.phase === 'crashed' ? '#71717a' : '#ffffff'}
                />
              </>
            )}
          </svg>

          <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
            {rocket.phase === 'betting' ? (
              <>
                <span className="text-xs font-medium uppercase tracking-widest text-zinc-400">
                  Приём ставок
                </span>
                <span className="mt-1 font-mono-num text-4xl font-bold text-white">
                  {rocket.countdown_sec.toFixed(1)}s
                </span>
              </>
            ) : rocket.phase === 'flying' ? (
              <>
                <span className="text-xs font-medium uppercase tracking-widest text-zinc-400">
                  В полёте
                </span>
                <span className="mt-1 font-mono-num text-5xl font-extrabold tracking-tight text-white">
                  {rocket.multiplier.toFixed(2)}x
                </span>
              </>
            ) : (
              <>
                <span className="text-xs font-semibold uppercase tracking-widest text-zinc-500">
                  Краш
                </span>
                <span className="mt-1 font-mono-num text-5xl font-extrabold tracking-tight text-zinc-400">
                  {(rocket.crash_point || rocket.multiplier).toFixed(2)}x
                </span>
              </>
            )}
          </div>
        </div>

        {noticeMsg && (
          <div className="mt-3 rounded-2xl border border-white/20 bg-zinc-950 p-3 text-center text-xs font-medium text-white">
            {noticeMsg}
          </div>
        )}
        {errorMsg && (
          <div className="mt-3 rounded-2xl border border-rose-500/30 bg-rose-950/30 p-3 text-center text-xs text-rose-300">
            {errorMsg}
          </div>
        )}

        {/* Controls */}
        {myBet && myBet.status === 'active' && rocket.phase === 'flying' ? (
          <button
            type="button"
            disabled={busy || (myBet.stake_type === 'nft' && rocket.multiplier < 1.3)}
            onClick={handleCashout}
            className="mt-4 flex h-13 w-full items-center justify-center gap-2 rounded-2xl bg-white text-sm font-bold text-black transition-transform active:scale-[0.98] disabled:opacity-45"
          >
            <Rocket className="h-4 w-4" />
            <span>
              {myBet.stake_type === 'nft'
                ? rocket.multiplier >= (myBet.target_mult || 99)
                  ? `Забрать апгрейд (${rocket.multiplier.toFixed(2)}x)`
                  : `Вернуть NFT (с x1.30) · цель x${myBet.target_mult}`
                : `Забрать ${formatStars(Math.round(myBet.stake_stars * rocket.multiplier))} ⭐ (${rocket.multiplier.toFixed(2)}x)`}
            </span>
          </button>
        ) : (
          <div className="mt-4 space-y-3 rounded-3xl border border-white/10 bg-zinc-950 p-4">
            {/* Mode Switch */}
            <div className="grid grid-cols-2 gap-2 rounded-2xl bg-zinc-900 p-1">
              <button
                type="button"
                onClick={() => setStakeType('stars')}
                className={`flex min-h-[44px] items-center justify-center gap-1.5 rounded-xl text-xs font-semibold transition-colors ${
                  stakeType === 'stars' ? 'bg-white text-black' : 'text-zinc-400'
                }`}
              >
                <Star className="h-3.5 w-3.5" />
                <span>Ставка Stars</span>
              </button>
              <button
                type="button"
                onClick={() => setStakeType('nft')}
                className={`flex min-h-[44px] items-center justify-center gap-1.5 rounded-xl text-xs font-semibold transition-colors ${
                  stakeType === 'nft' ? 'bg-white text-black' : 'text-zinc-400'
                }`}
              >
                <Sparkles className="h-3.5 w-3.5" />
                <span>Апгрейд NFT</span>
              </button>
            </div>

            {stakeType === 'stars' ? (
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <div>
                  <label className="mb-1 block text-[11px] font-medium text-zinc-400">
                    Сумма (Stars ⭐)
                  </label>
                  <input
                    type="number"
                    min={50}
                    value={stakeStars}
                    onChange={(e) => setStakeStars(e.target.value)}
                    className="h-11 w-full rounded-2xl border border-white/10 bg-black px-3.5 font-mono-num text-sm text-white outline-none focus:border-white/40"
                  />
                  <div className="mt-2 flex gap-1.5">
                    {[500, 2500, 10000, 50000].map((v) => (
                      <button
                        key={v}
                        type="button"
                        onClick={() => setStakeStars(String(v))}
                        className="min-h-[34px] flex-1 rounded-xl border border-white/10 bg-zinc-900 font-mono-num text-[11px] font-semibold text-zinc-300"
                      >
                        {formatStars(v)}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="mb-1 block text-[11px] font-medium text-zinc-400">
                    Авто-вывод (x)
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    min={1.1}
                    value={autoCashout}
                    onChange={(e) => setAutoCashout(e.target.value)}
                    className="h-11 w-full rounded-2xl border border-white/10 bg-black px-3.5 font-mono-num text-sm text-white outline-none focus:border-white/40"
                  />
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                <div>
                  <label className="mb-1 block text-[11px] font-medium text-zinc-400">
                    Ваш NFT для ставки
                  </label>
                  {availableNfts.length === 0 ? (
                    <p className="rounded-2xl border border-white/10 bg-black p-3 text-xs text-zinc-500">
                      Нет свободных NFT в инвентаре.
                    </p>
                  ) : (
                    <select
                      value={selectedNft?.id || 0}
                      onChange={(e) => setSelectedNftId(Number(e.target.value))}
                      className="h-11 w-full rounded-2xl border border-white/10 bg-black px-3 text-xs font-medium text-white outline-none"
                    >
                      {availableNfts.map((n) => (
                        <option key={n.id} value={n.id}>
                          {n.model_name || n.name} ({formatStars(n.display_stars)} ⭐)
                        </option>
                      ))}
                    </select>
                  )}
                </div>

                <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                  <div>
                    <label className="mb-1 block text-[11px] text-zinc-400">Цель NFT</label>
                    <select
                      value={targetGiftKey}
                      onChange={(e) => {
                        const k = e.target.value;
                        setTargetGiftKey(k);
                        setTargetModelName((catalog.models_by_gift[k] || [])[0]?.name || '');
                      }}
                      className="h-11 w-full rounded-2xl border border-white/10 bg-black px-3 text-xs text-white outline-none"
                    >
                      {catalog.upgradable_gifts.map((g) => (
                        <option key={g.key} value={g.key}>
                          {g.title}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="mb-1 block text-[11px] text-zinc-400">Модель</label>
                    <select
                      value={selectedModel?.name || ''}
                      onChange={(e) => setTargetModelName(e.target.value)}
                      className="h-11 w-full rounded-2xl border border-white/10 bg-black px-3 text-xs text-white outline-none"
                    >
                      {targetModels.map((m) => (
                        <option key={m.name} value={m.name}>
                          {m.name}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="mb-1 block text-[11px] text-zinc-400">Фон</label>
                    <select
                      value={selectedBackdrop?.key || ''}
                      onChange={(e) => setTargetBackdropKey(e.target.value)}
                      className="h-11 w-full rounded-2xl border border-white/10 bg-black px-3 text-xs text-white outline-none"
                    >
                      {catalog.backdrops.map((b) => (
                        <option key={b.key} value={b.key}>
                          {b.name}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                {selectedNft && (
                  <div className="flex items-center justify-between rounded-2xl border border-white/10 bg-black/70 px-3.5 py-2.5 text-xs">
                    <span className="text-zinc-400">Цель апгрейда ({formatStars(nftTargetStars)} ⭐)</span>
                    <span className="font-mono-num font-bold text-white">
                      нужно {nftRequiredMult.toFixed(2)}x
                    </span>
                  </div>
                )}
              </div>
            )}

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
                ? 'Дождитесь начала следующего раунда'
                : stakeType === 'nft'
                ? `Запустить апгрейд NFT на x${nftRequiredMult.toFixed(2)}`
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
                className="flex items-center justify-between rounded-2xl border border-white/10 bg-zinc-950 px-3.5 py-2.5"
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
                        ? `NFT → ${b.target_gift_title} (x${b.target_mult})`
                        : `${formatStars(b.stake_stars)} ⭐`}
                    </p>
                  </div>
                </div>
                <div className="shrink-0 text-right font-mono-num text-xs font-semibold">
                  {b.status === 'won' ? (
                    <span className="text-white">
                      +{formatStars(b.payout_stars || 0)} ⭐ ({b.cashout_mult}x)
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
