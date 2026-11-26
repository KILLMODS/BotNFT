import { useEffect, useMemo, useState } from 'react';
import { Check, ChevronDown, Gauge, Sparkles, X, Zap } from 'lucide-react';
import { apiRequest, formatStars, getTelegramWebApp, resolveAssetUrl } from '../api';
import type { BackdropDef, CatalogData, CollectionItem, GiftCatalogItem, ModelDef, UserProfile } from '../types';

interface UpgraderViewProps {
  user: UserProfile;
  collection: CollectionItem[];
  catalog: CatalogData;
  onSync: (user: UserProfile, collection: CollectionItem[]) => void;
}

function calcUpgradedStars(
  gift: GiftCatalogItem,
  model: ModelDef | null,
  backdrop: BackdropDef,
  catalog: CatalogData,
  valueBuffPct = 0
): number {
  const monoMult =
    model?.color_family &&
    backdrop.color_family &&
    backdrop.key !== 'rainbow' &&
    model.color_family === backdrop.color_family
      ? catalog.mono_price_mult || 6
      : 1;
  const valMult = 1 + Math.max(0, valueBuffPct) / 100;
  const base = gift.key === 'pepe_heart' ? gift.base_stars : gift.base_stars + gift.upgrade_cost;
  const raw = base * backdrop.price_mult * (model ? model.price_mult : 1.1) * monoMult * valMult * 1.5;
  if (gift.key === 'pepe_heart') return Math.max(750000, Math.round(raw / 10000) * 10000);
  if (gift.key === 'trophy_cup') return Math.max(375000, Math.round(raw / 5000) * 5000);
  if (gift.key === 'heart_lock_key' || gift.key === 'bonded_ring') return Math.max(225000, Math.round(raw / 5000) * 5000);
  return Math.max(150000, Math.round(raw / 5000) * 5000);
}

function findCheapestValidCombo(
  sourceStars: number,
  catalog: CatalogData,
  valueBuffPct: number,
  onlyGiftKey?: string,
  onlyModelName?: string
): { giftKey: string; modelName: string; backdropKey: string; stars: number } | null {
  let best: { giftKey: string; modelName: string; backdropKey: string; stars: number } | null = null;
  const gifts = onlyGiftKey
    ? catalog.upgradable_gifts.filter((g) => g.key === onlyGiftKey)
    : catalog.upgradable_gifts;
  for (const g of gifts) {
    const models = catalog.models_by_gift[g.key] || [];
    const filteredModels = onlyModelName ? models.filter((m) => m.name === onlyModelName) : models;
    const modelList = filteredModels.length > 0 ? filteredModels : [null];
    for (const m of modelList) {
      for (const b of catalog.backdrops) {
        const stars = calcUpgradedStars(g, m, b, catalog, valueBuffPct);
        if (stars > sourceStars) {
          if (!best || stars < best.stars) {
            best = {
              giftKey: g.key,
              modelName: m?.name || '',
              backdropKey: b.key,
              stars,
            };
          }
        }
      }
    }
  }
  return best;
}

export function UpgraderView({ user, collection, catalog, onSync }: UpgraderViewProps) {
  const availableItems = useMemo(
    () => collection.filter((it) => it.is_listed === 0),
    [collection]
  );

  const [sourceId, setSourceId] = useState<number>(() => availableItems[0]?.id || 0);
  const [targetGiftKey, setTargetGiftKey] = useState<string>(
    catalog.upgradable_gifts[0]?.key || 'pepe_heart'
  );
  const modelsForTarget = catalog.models_by_gift[targetGiftKey] || [];
  const [targetModelName, setTargetModelName] = useState<string>(
    modelsForTarget[0]?.name || ''
  );
  const [targetBackdropKey, setTargetBackdropKey] = useState<string>(
    catalog.backdrops[0]?.key || 'black'
  );

  const [spinSpeed, setSpinSpeed] = useState<'slow' | 'fast'>('slow');
  const [pickerMode, setPickerMode] = useState<'source' | 'target' | null>(null);
  const [spinning, setSpinning] = useState(false);
  const [spinChancePct, setSpinChancePct] = useState<number | null>(null);
  const [needleDeg, setNeedleDeg] = useState(0);
  const [resultMsg, setResultMsg] = useState<{ won: boolean; text: string } | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const selectedSource =
    availableItems.find((x) => x.id === sourceId) || availableItems[0] || null;

  const selectedTargetGift =
    catalog.upgradable_gifts.find((g) => g.key === targetGiftKey) ||
    catalog.upgradable_gifts[0];

  const selectedModel =
    modelsForTarget.find((m) => m.name === targetModelName) || modelsForTarget[0] || null;

  const selectedBackdrop =
    catalog.backdrops.find((b) => b.key === targetBackdropKey) ||
    catalog.backdrops[0];

  const sourceBuffPct = selectedSource?.buff_value_pct || 0;

  const estimatedTargetStars = useMemo(() => {
    if (!selectedTargetGift || !selectedBackdrop) return 0;
    return calcUpgradedStars(selectedTargetGift, selectedModel, selectedBackdrop, catalog, sourceBuffPct);
  }, [selectedTargetGift, selectedModel, selectedBackdrop, catalog, sourceBuffPct]);

  const isTargetValid = Boolean(
    selectedSource && estimatedTargetStars > selectedSource.display_stars
  );

  // Auto-snap to a valid target (> source.display_stars) whenever source NFT changes
  useEffect(() => {
    if (!selectedSource || spinning) return;
    if (estimatedTargetStars <= selectedSource.display_stars) {
      const valid =
        findCheapestValidCombo(selectedSource.display_stars, catalog, sourceBuffPct, targetGiftKey, targetModelName) ||
        findCheapestValidCombo(selectedSource.display_stars, catalog, sourceBuffPct, targetGiftKey) ||
        findCheapestValidCombo(selectedSource.display_stars, catalog, sourceBuffPct);
      if (valid) {
        setTargetGiftKey(valid.giftKey);
        setTargetModelName(valid.modelName);
        setTargetBackdropKey(valid.backdropKey);
      }
    }
  }, [selectedSource?.id, selectedSource?.display_stars, estimatedTargetStars, catalog, sourceBuffPct, spinning, targetGiftKey, targetModelName]);

  const chancePct = useMemo(() => {
    if (!selectedSource || estimatedTargetStars <= 0 || !isTargetValid) return 0;
    const raw = (selectedSource.display_stars / estimatedTargetStars) * 100;
    return Number(
      Math.max(1, Math.min(72, raw * (catalog.upgrader_chance_factor || 0.78))).toFixed(2)
    );
  }, [selectedSource, estimatedTargetStars, isTargetValid, catalog.upgrader_chance_factor]);

  const displayChancePct = spinning && spinChancePct !== null ? spinChancePct : chancePct;
  const radius = 92;
  const circumference = 2 * Math.PI * radius;
  const winArcLength = (displayChancePct / 100) * circumference;

  const animDurationMs = spinSpeed === 'fast' ? 550 : 2600;
  const fullSpinTurns = spinSpeed === 'fast' ? 360 * 2 : 360 * 5;

  const handleGiftChange = (key: string) => {
    setTargetGiftKey(key);
    const nextModels = catalog.models_by_gift[key] || [];
    const nextM = nextModels[0] || null;
    const nextG = catalog.upgradable_gifts.find((x) => x.key === key);
    if (selectedSource && nextG && selectedBackdrop) {
      const stars = calcUpgradedStars(nextG, nextM, selectedBackdrop, catalog, sourceBuffPct);
      if (stars <= selectedSource.display_stars) {
        const best = findCheapestValidCombo(selectedSource.display_stars, catalog, sourceBuffPct, key);
        if (best) {
          setTargetModelName(best.modelName);
          setTargetBackdropKey(best.backdropKey);
          return;
        }
      }
    }
    setTargetModelName(nextM?.name || '');
  };

  const handleModelChange = (mName: string) => {
    setTargetModelName(mName);
    if (selectedSource && selectedTargetGift && selectedBackdrop) {
      const nextM = modelsForTarget.find((m) => m.name === mName) || null;
      const stars = calcUpgradedStars(selectedTargetGift, nextM, selectedBackdrop, catalog, sourceBuffPct);
      if (stars <= selectedSource.display_stars) {
        const best = findCheapestValidCombo(selectedSource.display_stars, catalog, sourceBuffPct, selectedTargetGift.key, mName);
        if (best) {
          setTargetBackdropKey(best.backdropKey);
        }
      }
    }
  };

  const handleUpgrade = async () => {
    if (!selectedSource || !selectedTargetGift || spinning) return;
    if (!isTargetValid) {
      setErrorMsg('Целевой NFT должен быть дороже вашего текущего NFT.');
      return;
    }
    setErrorMsg(null);
    setResultMsg(null);
    setSpinning(true);

    try {
      const res = await apiRequest<{
        won: boolean;
        chance_pct: number;
        roll: number;
        target_stars: number;
        user: UserProfile;
        collection: CollectionItem[];
      }>('/api/upgrade', {
        method: 'POST',
        body: JSON.stringify({
          source_item_id: selectedSource.id,
          target_gift_key: selectedTargetGift.key,
          target_model_name: selectedModel?.name,
          target_backdrop_key: selectedBackdrop?.key,
        }),
      });

      setSpinChancePct(res.chance_pct);
      const winAngleLimit = (res.chance_pct / 100) * 360;
      const rawRollAngle = (res.roll / 100) * 360;
      const targetAngle = res.won
        ? winAngleLimit <= 6
          ? Math.max(0.8, Math.min(winAngleLimit - 0.8, winAngleLimit * 0.5))
          : Math.max(2, Math.min(winAngleLimit - 2, rawRollAngle))
        : Math.max(Math.min(358, winAngleLimit + 2.5), Math.min(358, rawRollAngle));
      setNeedleDeg((prev) => prev - (prev % 360) + fullSpinTurns + targetAngle);

      setTimeout(() => {
        setSpinning(false);
        setSpinChancePct(null);
        onSync(res.user, res.collection);
        const nextAvail = res.collection.filter((c) => c.is_listed === 0);
        setSourceId(nextAvail[0]?.id || 0);
        getTelegramWebApp()?.HapticFeedback?.notificationOccurred(
          res.won ? 'success' : 'error'
        );
        setResultMsg({
          won: res.won,
          text: res.won
            ? `Успех! Получен улучшенный ${selectedTargetGift.title} (${formatStars(res.target_stars)} ⭐)`
            : `Не повезло (${res.roll.toFixed(1)}% при шансе ${res.chance_pct.toFixed(1)}%). Попробуйте снова.`,
        });
      }, animDurationMs + 80);
    } catch (err) {
      setSpinning(false);
      setSpinChancePct(null);
      setErrorMsg(err instanceof Error ? err.message : 'Ошибка апгрейда');
    }
  };

  return (
    <div className="space-y-4">
      <section className="rounded-3xl border border-white/10 bg-zinc-900/90 p-5">
        <div className="flex items-center justify-between gap-2">
          <div className="min-w-0">
            <h2 className="text-lg font-bold tracking-tight text-white">Апгрейдер</h2>
            <p className="truncate text-xs text-zinc-400">
              Соберите редкий NFT с моделью и фоном
            </p>
          </div>
          <div className="shrink-0 rounded-2xl border border-white/10 bg-black/60 px-3 py-1.5 font-mono-num text-xs font-semibold text-zinc-200">
            {formatStars(user.balance_stars)} ⭐
          </div>
        </div>

        {/* Speed Toggle */}
        <div className="mt-4 flex items-center justify-center">
          <div className="inline-grid grid-cols-2 gap-1 rounded-2xl border border-white/10 bg-zinc-950 p-1">
            <button
              type="button"
              disabled={spinning}
              onClick={() => setSpinSpeed('slow')}
              className={`flex min-h-[36px] items-center gap-1.5 rounded-xl px-3.5 text-xs font-semibold transition-colors ${
                spinSpeed === 'slow' ? 'bg-white text-black' : 'text-zinc-400'
              }`}
            >
              <Gauge className="h-3.5 w-3.5" />
              <span>Медленный</span>
            </button>
            <button
              type="button"
              disabled={spinning}
              onClick={() => setSpinSpeed('fast')}
              className={`flex min-h-[36px] items-center gap-1.5 rounded-xl px-3.5 text-xs font-semibold transition-colors ${
                spinSpeed === 'fast' ? 'bg-white text-black' : 'text-zinc-400'
              }`}
            >
              <Zap className="h-3.5 w-3.5" />
              <span>Быстрый</span>
            </button>
          </div>
        </div>

        {/* Polished Circular Wheel */}
        <div className="mt-4 flex flex-col items-center">
          <div className="relative flex h-60 w-60 items-center justify-center">
            <svg viewBox="0 0 240 240" className="h-full w-full">
              {/* Rim Tick Marks */}
              {Array.from({ length: 36 }).map((_, i) => {
                const angle = (i * 10 * Math.PI) / 180;
                const x1 = 120 + Math.cos(angle) * 107;
                const y1 = 120 + Math.sin(angle) * 107;
                const x2 = 120 + Math.cos(angle) * (i % 3 === 0 ? 114 : 111);
                const y2 = 120 + Math.sin(angle) * (i % 3 === 0 ? 114 : 111);
                return (
                  <line
                    key={i}
                    x1={x1}
                    y1={y1}
                    x2={x2}
                    y2={y2}
                    stroke={i % 3 === 0 ? 'rgba(255,255,255,0.28)' : 'rgba(255,255,255,0.1)'}
                    strokeWidth={i % 3 === 0 ? '1.8' : '1'}
                    strokeLinecap="round"
                  />
                );
              })}

              {/* Base Track & Active Win Arc */}
              <g transform="rotate(-90 120 120)">
                <circle
                  cx="120"
                  cy="120"
                  r={radius}
                  fill="none"
                  stroke="#18181b"
                  strokeWidth="18"
                />
                <circle
                  cx="120"
                  cy="120"
                  r={radius}
                  fill="none"
                  stroke="#27272a"
                  strokeWidth="14"
                />
                <circle
                  cx="120"
                  cy="120"
                  r={radius}
                  fill="none"
                  stroke="#ffffff"
                  strokeWidth="14"
                  strokeLinecap="butt"
                  strokeDasharray={`${winArcLength} ${circumference}`}
                  className="transition-all duration-300"
                />
              </g>
            </svg>

            {/* Sharp Arrow Needle */}
            <div
              className="pointer-events-none absolute inset-0 flex items-start justify-center"
              style={{
                transform: `rotate(${needleDeg}deg)`,
                transitionProperty: 'transform',
                transitionDuration: `${animDurationMs}ms`,
                transitionTimingFunction: 'cubic-bezier(0.14, 0.92, 0.24, 1)',
              }}
            >
              <svg width="24" height="30" viewBox="0 0 24 30" className="mt-0.5 drop-shadow-[0_0_8px_rgba(255,255,255,0.85)]">
                <polygon points="12,26 4,4 20,4" fill="#ffffff" />
                <circle cx="12" cy="7" r="2.2" fill="#000000" />
              </svg>
            </div>

            {/* Center Telemetry */}
            <div className="absolute flex h-36 w-36 flex-col items-center justify-center rounded-full border border-white/10 bg-zinc-950/95 text-center shadow-inner">
              <span className="text-[10px] font-medium uppercase tracking-widest text-zinc-500">
                Шанс
              </span>
              <span className="mt-0.5 font-mono-num text-3xl font-bold tracking-tight text-white">
                {selectedSource ? `${displayChancePct.toFixed(1)}%` : '0%'}
              </span>
              <span className="mt-1 max-w-[120px] truncate font-mono-num text-[10px] text-zinc-400">
                {selectedSource
                  ? `${formatStars(selectedSource.display_stars)} → ${formatStars(estimatedTargetStars)}`
                  : 'Выберите NFT'}
              </span>
            </div>
          </div>
        </div>

        {resultMsg && (
          <div
            className={`mt-4 rounded-2xl border p-3.5 text-center text-xs font-medium ${
              resultMsg.won
                ? 'border-white/30 bg-white text-black'
                : 'border-white/10 bg-zinc-950 text-zinc-300'
            }`}
          >
            {resultMsg.text}
          </div>
        )}
        {errorMsg && (
          <div className="mt-4 rounded-2xl border border-rose-500/30 bg-rose-950/30 p-3 text-center text-xs text-rose-300">
            {errorMsg}
          </div>
        )}

        {/* Dual Slots */}
        <div className="mt-5 grid grid-cols-2 gap-3">
          {/* Slot 1: Your NFT */}
          <button
            type="button"
            disabled={spinning}
            onClick={() => setPickerMode('source')}
            className="flex min-h-[120px] flex-col justify-between rounded-3xl border border-white/10 bg-zinc-950 p-3.5 text-left transition-colors hover:border-white/25 active:scale-[0.98]"
          >
            <div className="flex items-center justify-between text-[11px] font-medium text-zinc-400">
              <span>Ваш NFT</span>
              <ChevronDown className="h-3.5 w-3.5" />
            </div>
            {selectedSource ? (
              <div className="mt-2 flex items-center gap-2.5">
                <img
                  src={resolveAssetUrl(selectedSource.image_url)}
                  alt={selectedSource.name}
                  className="h-12 w-12 shrink-0 rounded-xl bg-zinc-900 object-contain p-1"
                />
                <div className="min-w-0">
                  <p className="truncate text-xs font-semibold text-white">
                    {selectedSource.model_name || selectedSource.name}
                  </p>
                  <p className="mt-0.5 font-mono-num text-[11px] text-zinc-400">
                    {formatStars(selectedSource.display_stars)} ⭐
                  </p>
                </div>
              </div>
            ) : (
              <p className="my-auto text-xs text-zinc-500">Нет доступных NFT</p>
            )}
          </button>

          {/* Slot 2: Target NFT */}
          <button
            type="button"
            disabled={spinning}
            onClick={() => setPickerMode('target')}
            className="flex min-h-[120px] flex-col justify-between rounded-3xl border border-white/10 bg-zinc-950 p-3.5 text-left transition-colors hover:border-white/25 active:scale-[0.98]"
          >
            <div className="flex items-center justify-between text-[11px] font-medium text-zinc-400">
              <span>Цель (NFT + Фон)</span>
              <ChevronDown className="h-3.5 w-3.5" />
            </div>
            {selectedTargetGift && (
              <div className="mt-2 flex items-center gap-2.5">
                <div
                  className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl p-1"
                  style={
                    selectedBackdrop
                      ? {
                          background: `radial-gradient(circle, ${selectedBackdrop.center_hex}, ${selectedBackdrop.edge_hex})`,
                        }
                      : undefined
                  }
                >
                  <img
                    src={resolveAssetUrl(selectedModel?.image_url || selectedTargetGift.image_url)}
                    alt={selectedTargetGift.title}
                    className="h-10 w-10 object-contain"
                  />
                </div>
                <div className="min-w-0">
                  <p className="truncate text-xs font-semibold text-white">
                    {selectedModel?.name || selectedTargetGift.title}
                  </p>
                  <p className="mt-0.5 truncate text-[10px] text-zinc-400">
                    {selectedBackdrop?.name}
                  </p>
                  <p className="font-mono-num text-[11px] font-medium text-zinc-300">
                    {formatStars(estimatedTargetStars)} ⭐
                  </p>
                </div>
              </div>
            )}
          </button>
        </div>

        <button
          type="button"
          disabled={!selectedSource || !isTargetValid || spinning}
          onClick={handleUpgrade}
          className="mt-4 flex h-12 w-full items-center justify-center gap-2 rounded-2xl bg-white text-sm font-bold text-black transition-transform active:scale-[0.98] disabled:opacity-40"
        >
          <Sparkles className="h-4 w-4" />
          <span>
            {spinning
              ? 'Крутим колесо...'
              : !isTargetValid && selectedSource
              ? 'Выберите цель дороже вашего NFT'
              : `Улучшить за шанс ${chancePct.toFixed(1)}%`}
          </span>
        </button>
      </section>

      {/* Bottom Sheet Picker */}
      {pickerMode && (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/75 backdrop-blur-sm sm:items-center sm:p-4">
          <div className="flex max-h-[82vh] w-full max-w-lg flex-col rounded-t-3xl border border-white/15 bg-zinc-900 sm:rounded-3xl">
            <div className="flex items-center justify-between border-b border-white/10 px-5 py-4">
              <h3 className="text-base font-bold text-white">
                {pickerMode === 'source' ? 'Выберите ваш NFT' : 'Настройка цели апгрейда'}
              </h3>
              <button
                type="button"
                onClick={() => setPickerMode(null)}
                className="flex h-10 w-10 items-center justify-center rounded-full bg-zinc-800 text-zinc-300"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="flex-1 space-y-4 overflow-y-auto p-5">
              {pickerMode === 'source' ? (
                availableItems.length === 0 ? (
                  <p className="py-8 text-center text-sm text-zinc-500">
                    В инвентаре нет свободных NFT.
                  </p>
                ) : (
                  <div className="grid grid-cols-2 gap-3">
                    {availableItems.map((it) => {
                      const active = it.id === selectedSource?.id;
                      return (
                        <button
                          key={it.id}
                          type="button"
                          onClick={() => {
                            setSourceId(it.id);
                            setPickerMode(null);
                          }}
                          className={`flex items-center gap-2.5 rounded-2xl border p-3 text-left ${
                            active
                              ? 'border-white bg-zinc-800'
                              : 'border-white/10 bg-zinc-950'
                          }`}
                        >
                          <img
                            src={resolveAssetUrl(it.image_url)}
                            alt={it.name}
                            className="h-11 w-11 shrink-0 rounded-xl bg-zinc-900 object-contain p-1"
                          />
                          <div className="min-w-0 flex-1">
                            <p className="truncate text-xs font-semibold text-white">
                              {it.model_name || it.name}
                            </p>
                            <p className="font-mono-num text-[11px] text-zinc-400">
                              {formatStars(it.display_stars)} ⭐
                            </p>
                          </div>
                          {active && <Check className="h-4 w-4 shrink-0 text-white" />}
                        </button>
                      );
                    })}
                  </div>
                )
              ) : (
                <>
                  <div>
                    <label className="mb-2 block text-xs font-semibold uppercase tracking-wider text-zinc-400">
                      1. Тип подарка
                    </label>
                    <div className="flex gap-2 overflow-x-auto pb-1 no-scrollbar">
                      {catalog.upgradable_gifts.map((g) => {
                        const active = g.key === targetGiftKey;
                        const canReach = selectedSource
                          ? Boolean(findCheapestValidCombo(selectedSource.display_stars, catalog, sourceBuffPct, g.key))
                          : true;
                        return (
                          <button
                            key={g.key}
                            type="button"
                            disabled={!canReach}
                            onClick={() => handleGiftChange(g.key)}
                            className={`flex min-h-[44px] shrink-0 items-center gap-2 rounded-2xl border px-3.5 text-xs font-semibold disabled:cursor-not-allowed disabled:opacity-35 ${
                              active
                                ? 'border-white bg-white text-black'
                                : 'border-white/10 bg-zinc-950 text-zinc-300'
                            }`}
                          >
                            <img
                              src={resolveAssetUrl(g.image_url)}
                              alt={g.title}
                              className="h-6 w-6 object-contain"
                            />
                            <span>{g.title}</span>
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  <div>
                    <label className="mb-2 block text-xs font-semibold uppercase tracking-wider text-zinc-400">
                      2. Модель ({modelsForTarget.length})
                    </label>
                    <div className="grid max-h-44 grid-cols-2 gap-2 overflow-y-auto pr-1">
                      {modelsForTarget.map((m) => {
                        const active = m.name === selectedModel?.name;
                        const canReach = selectedSource && selectedTargetGift
                          ? Boolean(findCheapestValidCombo(selectedSource.display_stars, catalog, sourceBuffPct, selectedTargetGift.key, m.name))
                          : true;
                        return (
                          <button
                            key={m.name}
                            type="button"
                            disabled={!canReach}
                            onClick={() => handleModelChange(m.name)}
                            className={`flex min-h-[48px] items-center gap-2 rounded-2xl border p-2 text-left disabled:cursor-not-allowed disabled:opacity-35 ${
                              active
                                ? 'border-white bg-zinc-800'
                                : 'border-white/10 bg-zinc-950'
                            }`}
                          >
                            <img
                              src={resolveAssetUrl(m.image_url)}
                              alt={m.name}
                              className="h-8 w-8 shrink-0 object-contain"
                            />
                            <div className="min-w-0">
                              <p className="truncate text-xs font-semibold text-white">
                                {m.name}
                              </p>
                              <p className="font-mono-num text-[10px] text-zinc-400">
                                {canReach ? `x${m.price_mult}` : '≤ ваш NFT'}
                              </p>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  <div>
                    <label className="mb-2 block text-xs font-semibold uppercase tracking-wider text-zinc-400">
                      3. Фон
                    </label>
                    <div className="grid max-h-44 grid-cols-2 gap-2 overflow-y-auto pr-1">
                      {catalog.backdrops.map((b) => {
                        const active = b.key === selectedBackdrop?.key;
                        const comboStars =
                          selectedTargetGift
                            ? calcUpgradedStars(selectedTargetGift, selectedModel, b, catalog, sourceBuffPct)
                            : 0;
                        const isHigher = selectedSource ? comboStars > selectedSource.display_stars : true;
                        return (
                          <button
                            key={b.key}
                            type="button"
                            disabled={!isHigher}
                            onClick={() => setTargetBackdropKey(b.key)}
                            className={`flex min-h-[48px] items-center gap-2.5 rounded-2xl border p-2 text-left disabled:cursor-not-allowed disabled:opacity-35 ${
                              active
                                ? 'border-white bg-zinc-800'
                                : 'border-white/10 bg-zinc-950'
                            }`}
                          >
                            <span
                              className="h-7 w-7 shrink-0 rounded-xl border border-white/15"
                              style={{
                                background: `radial-gradient(circle, ${b.center_hex}, ${b.edge_hex})`,
                              }}
                            />
                            <div className="min-w-0">
                              <p className="truncate text-xs font-semibold text-white">
                                {b.name}
                              </p>
                              <p className="font-mono-num text-[10px] text-zinc-400">
                                {isHigher ? `${formatStars(comboStars)} ⭐` : '≤ ваш NFT'}
                              </p>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                </>
              )}
            </div>

            {pickerMode === 'target' && (
              <div className="border-t border-white/10 p-4">
                <button
                  type="button"
                  disabled={!isTargetValid}
                  onClick={() => setPickerMode(null)}
                  className="h-12 w-full rounded-2xl bg-white text-sm font-bold text-black disabled:opacity-40"
                >
                  {isTargetValid
                    ? `Готово · Шанс ${chancePct.toFixed(1)}%`
                    : 'Выберите цель дороже вашего NFT'}
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
