import { useMemo, useState } from 'react';
import { ChevronDown, Check, Sparkles, X } from 'lucide-react';
import { apiRequest, formatStars, getTelegramWebApp, resolveAssetUrl } from '../api';
import type { CatalogData, CollectionItem, UserProfile } from '../types';

interface UpgraderViewProps {
  user: UserProfile;
  collection: CollectionItem[];
  catalog: CatalogData;
  onSync: (user: UserProfile, collection: CollectionItem[]) => void;
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

  const [pickerMode, setPickerMode] = useState<'source' | 'target' | null>(null);
  const [spinning, setSpinning] = useState(false);
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

  const estimatedTargetStars = useMemo(() => {
    if (!selectedTargetGift || !selectedBackdrop) return 0;
    const base =
      selectedTargetGift.key === 'pepe_heart'
        ? selectedTargetGift.base_stars
        : selectedTargetGift.base_stars + selectedTargetGift.upgrade_cost;
    const modelMult = selectedModel ? selectedModel.price_mult : 1.1;
    const buffMult = selectedSource ? 1 + (selectedSource.buff_value_pct || 0) / 100 : 1;
    const raw = base * selectedBackdrop.price_mult * modelMult * buffMult * 1.5;
    return Math.max(150000, Math.round(raw / 5000) * 5000);
  }, [selectedTargetGift, selectedModel, selectedBackdrop, selectedSource]);

  const chancePct = useMemo(() => {
    if (!selectedSource || estimatedTargetStars <= 0) return 0;
    const raw = (selectedSource.display_stars / estimatedTargetStars) * 100;
    return Number(
      Math.max(1, Math.min(72, raw * (catalog.upgrader_chance_factor || 0.78))).toFixed(2)
    );
  }, [selectedSource, estimatedTargetStars, catalog.upgrader_chance_factor]);

  const radius = 92;
  const circumference = 2 * Math.PI * radius;
  const winArcLength = (chancePct / 100) * circumference;

  const handleGiftChange = (key: string) => {
    setTargetGiftKey(key);
    const nextModels = catalog.models_by_gift[key] || [];
    setTargetModelName(nextModels[0]?.name || '');
  };

  const handleUpgrade = async () => {
    if (!selectedSource || !selectedTargetGift || spinning) return;
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

      const winAngleLimit = (res.chance_pct / 100) * 360;
      const targetAngle = res.won
        ? Math.max(8, Math.min(winAngleLimit - 6, (res.roll / 100) * 360))
        : Math.max(winAngleLimit + 12, Math.min(352, (res.roll / 100) * 360));
      const fullTurns = 360 * 4;
      setNeedleDeg((prev) => prev - (prev % 360) + fullTurns + targetAngle);

      setTimeout(() => {
        setSpinning(false);
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
      }, 2100);
    } catch (err) {
      setSpinning(false);
      setErrorMsg(err instanceof Error ? err.message : 'Ошибка апгрейда');
    }
  };

  return (
    <div className="space-y-4">
      {/* Header Card */}
      <section className="rounded-3xl border border-white/10 bg-zinc-900/90 p-5">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold tracking-tight text-white">Апгрейдер</h2>
            <p className="text-xs text-zinc-400">
              Соберите редкий NFT с моделью и фоном
            </p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-black/60 px-3 py-1.5 font-mono-num text-xs font-semibold text-zinc-200">
            Баланс: {formatStars(user.balance_stars)} ⭐
          </div>
        </div>

        {/* Circular Wheel */}
        <div className="mt-5 flex flex-col items-center">
          <div className="relative flex h-56 w-56 items-center justify-center">
            <svg viewBox="0 0 220 220" className="h-full w-full -rotate-90">
              <circle
                cx="110"
                cy="110"
                r={radius}
                fill="none"
                stroke="#27272a"
                strokeWidth="16"
              />
              <circle
                cx="110"
                cy="110"
                r={radius}
                fill="none"
                stroke="#ffffff"
                strokeWidth="16"
                strokeLinecap="round"
                strokeDasharray={`${winArcLength} ${circumference}`}
                className="transition-all duration-300"
              />
            </svg>

            {/* Needle */}
            <div
              className="pointer-events-none absolute inset-0 flex items-start justify-center transition-transform duration-[2000ms] ease-[cubic-bezier(0.16,1,0.3,1)]"
              style={{ transform: `rotate(${needleDeg}deg)` }}
            >
              <div className="mt-1.5 h-4 w-2 rounded-full bg-white shadow-[0_0_12px_rgba(255,255,255,0.85)]" />
            </div>

            {/* Center Telemetry */}
            <div className="absolute flex flex-col items-center text-center">
              <span className="text-[11px] font-medium uppercase tracking-wider text-zinc-500">
                Шанс
              </span>
              <span className="mt-0.5 font-mono-num text-3xl font-bold tracking-tight text-white">
                {selectedSource ? `${chancePct.toFixed(1)}%` : '0%'}
              </span>
              <span className="mt-1 font-mono-num text-[11px] text-zinc-400">
                {selectedSource ? `${formatStars(selectedSource.display_stars)} → ${formatStars(estimatedTargetStars)} ⭐` : 'Выберите NFT'}
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
            className="flex min-h-[126px] flex-col justify-between rounded-3xl border border-white/10 bg-zinc-950 p-3.5 text-left transition-colors hover:border-white/25 active:scale-[0.98]"
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
            className="flex min-h-[126px] flex-col justify-between rounded-3xl border border-white/10 bg-zinc-950 p-3.5 text-left transition-colors hover:border-white/25 active:scale-[0.98]"
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
          disabled={!selectedSource || spinning}
          onClick={handleUpgrade}
          className="mt-4 flex h-12 w-full items-center justify-center gap-2 rounded-2xl bg-white text-sm font-bold text-black transition-transform active:scale-[0.98] disabled:opacity-40"
        >
          <Sparkles className="h-4 w-4" />
          <span>{spinning ? 'Крутим колесо...' : `Улучшить за шанс ${chancePct.toFixed(1)}%`}</span>
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
                  {/* Target Gift Category */}
                  <div>
                    <label className="mb-2 block text-xs font-semibold uppercase tracking-wider text-zinc-400">
                      1. Тип подарка
                    </label>
                    <div className="flex gap-2 overflow-x-auto pb-1 no-scrollbar">
                      {catalog.upgradable_gifts.map((g) => {
                        const active = g.key === targetGiftKey;
                        return (
                          <button
                            key={g.key}
                            type="button"
                            onClick={() => handleGiftChange(g.key)}
                            className={`flex min-h-[44px] shrink-0 items-center gap-2 rounded-2xl border px-3.5 text-xs font-semibold ${
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

                  {/* Target Model */}
                  <div>
                    <label className="mb-2 block text-xs font-semibold uppercase tracking-wider text-zinc-400">
                      2. Модель ({modelsForTarget.length})
                    </label>
                    <div className="grid max-h-44 grid-cols-2 gap-2 overflow-y-auto pr-1">
                      {modelsForTarget.map((m) => {
                        const active = m.name === selectedModel?.name;
                        return (
                          <button
                            key={m.name}
                            type="button"
                            onClick={() => setTargetModelName(m.name)}
                            className={`flex min-h-[48px] items-center gap-2 rounded-2xl border p-2 text-left ${
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
                                x{m.price_mult}
                              </p>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* Target Backdrop */}
                  <div>
                    <label className="mb-2 block text-xs font-semibold uppercase tracking-wider text-zinc-400">
                      3. Фон
                    </label>
                    <div className="grid max-h-44 grid-cols-2 gap-2 overflow-y-auto pr-1">
                      {catalog.backdrops.map((b) => {
                        const active = b.key === selectedBackdrop?.key;
                        return (
                          <button
                            key={b.key}
                            type="button"
                            onClick={() => setTargetBackdropKey(b.key)}
                            className={`flex min-h-[48px] items-center gap-2.5 rounded-2xl border p-2 text-left ${
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
                                x{b.price_mult}
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
                  onClick={() => setPickerMode(null)}
                  className="h-12 w-full rounded-2xl bg-white text-sm font-bold text-black"
                >
                  Готово · Шанс {chancePct.toFixed(1)}%
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
