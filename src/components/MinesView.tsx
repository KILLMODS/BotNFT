import { useEffect, useMemo, useState } from 'react';
import { Bomb, Check, Diamond, Sparkles, Star } from 'lucide-react';
import {
  apiRequest,
  formatStars,
  getTelegramWebApp,
  parseDecimal,
  resolveAssetUrl,
  sanitizeDecimalInput,
} from '../api';
import { lookupNftRewardFast, buildSortedBasePool, buildUpgradedCandidates } from './RocketView';
import type { CatalogData, CollectionItem, MinesGame, UserProfile } from '../types';

interface MinesViewProps {
  user: UserProfile;
  collection: CollectionItem[];
  catalog: CatalogData;
  onSync: (user: UserProfile, collection: CollectionItem[]) => void;
}

const MINE_PRESETS = [3, 5, 10, 15, 20];

export function MinesView({ user, collection, catalog, onSync }: MinesViewProps) {
  const availableNfts = useMemo(
    () => collection.filter((c) => c.is_listed === 0),
    [collection]
  );

  const [game, setGame] = useState<MinesGame | null>(null);
  const [stakeType, setStakeType] = useState<'stars' | 'nft'>('stars');
  const [stakeStars, setStakeStars] = useState<string>('1000');
  const [minesCount, setMinesCount] = useState<number>(5);
  const [selectedNftId, setSelectedNftId] = useState<number>(() => availableNfts[0]?.id || 0);
  const [busy, setBusy] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [noticeMsg, setNoticeMsg] = useState<string | null>(null);

  useEffect(() => {
    apiRequest<{ game: MinesGame | null }>('/api/mines/state')
      .then((res) => {
        if (res.game) setGame(res.game);
      })
      .catch(() => {
        // Ignore initial load errors
      });
  }, []);

  const selectedNft =
    availableNfts.find((n) => n.id === selectedNftId) || availableNfts[0] || null;

  const sortedBasePool = useMemo(() => buildSortedBasePool(catalog), [catalog]);
  const previewSeed = game?.stake_type === 'nft' ? game.collection_item_id || 0 : selectedNft?.id || 0;
  const upgradedCandidates = useMemo(
    () => buildUpgradedCandidates(catalog, previewSeed),
    [catalog, previewSeed]
  );

  const activeNftPreview = useMemo(() => {
    if (game && game.stake_type === 'nft' && game.status === 'active') {
      const targetMult = game.revealed.length > 0 ? game.multiplier : game.next_multiplier;
      return lookupNftRewardFast(
        sortedBasePool,
        upgradedCandidates,
        Math.round(game.stake_stars * Math.max(1.05, targetMult)),
        game.stake_stars,
        Boolean(game.source_is_upgraded)
      );
    }
    if (!game?.status || game.status !== 'active') {
      if (stakeType === 'nft' && selectedNft) {
        return lookupNftRewardFast(
          sortedBasePool,
          upgradedCandidates,
          Math.round(selectedNft.display_stars * 1.45),
          selectedNft.display_stars,
          selectedNft.is_upgraded
        );
      }
    }
    return null;
  }, [game, stakeType, selectedNft, sortedBasePool, upgradedCandidates]);

  const isGameActive = game?.status === 'active';

  const handleStart = async () => {
    if (busy || isGameActive) return;
    setErrorMsg(null);
    setNoticeMsg(null);
    setBusy(true);
    try {
      const payload =
        stakeType === 'stars'
          ? {
              stake_type: 'stars',
              stake_stars: Math.round(parseDecimal(stakeStars)),
              mines_count: minesCount,
            }
          : {
              stake_type: 'nft',
              collection_item_id: selectedNft?.id || 0,
              mines_count: minesCount,
            };
      const res = await apiRequest<{
        game: MinesGame;
        user: UserProfile;
        collection: CollectionItem[];
      }>('/api/mines/start', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      setGame(res.game);
      onSync(res.user, res.collection);
      getTelegramWebApp()?.HapticFeedback?.impactOccurred('medium');
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Не удалось начать игру');
    } finally {
      setBusy(false);
    }
  };

  const handleReveal = async (cellIdx: number) => {
    if (busy || !isGameActive || game?.revealed.includes(cellIdx)) return;
    setErrorMsg(null);
    setBusy(true);
    try {
      const res = await apiRequest<{
        hit_mine: boolean;
        auto_won: boolean;
        payout_stars?: number;
        reward_name?: string;
        game: MinesGame;
        user: UserProfile;
        collection: CollectionItem[];
      }>('/api/mines/reveal', {
        method: 'POST',
        body: JSON.stringify({ cell: cellIdx }),
      });
      setGame(res.game);
      onSync(res.user, res.collection);
      if (res.hit_mine) {
        getTelegramWebApp()?.HapticFeedback?.notificationOccurred('error');
        setNoticeMsg('Мина! Ставка сгорела.');
      } else if (res.auto_won) {
        getTelegramWebApp()?.HapticFeedback?.notificationOccurred('success');
        setNoticeMsg(
          res.reward_name
            ? `Поле пройдено! Получен NFT: ${res.reward_name} (${formatStars(res.payout_stars || 0)} ⭐)`
            : `Поле пройдено! Выигрыш +${formatStars(res.payout_stars || 0)} ⭐`
        );
      } else {
        getTelegramWebApp()?.HapticFeedback?.impactOccurred('light');
      }
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Ошибка хода');
    } finally {
      setBusy(false);
    }
  };

  const handleCashout = async () => {
    if (busy || !isGameActive || (game?.revealed.length || 0) < 1) return;
    setErrorMsg(null);
    setBusy(true);
    try {
      const res = await apiRequest<{
        payout_stars: number;
        upgraded: boolean;
        reward_name?: string;
        game: MinesGame;
        user: UserProfile;
        collection: CollectionItem[];
      }>('/api/mines/cashout', {
        method: 'POST',
        body: JSON.stringify({}),
      });
      setGame(res.game);
      onSync(res.user, res.collection);
      getTelegramWebApp()?.HapticFeedback?.notificationOccurred('success');
      setNoticeMsg(
        res.reward_name
          ? `Вывод! Получен NFT: ${res.reward_name} (${formatStars(res.payout_stars)} ⭐)`
          : `Выведено +${formatStars(res.payout_stars)} ⭐ (${res.game.multiplier.toFixed(2)}x)`
      );
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Не удалось забрать выигрыш');
    } finally {
      setBusy(false);
    }
  };

  const revealedSet = useMemo(() => new Set(game?.revealed || []), [game?.revealed]);
  const minesSet = useMemo(() => new Set(game?.mines || []), [game?.mines]);

  return (
    <div className="space-y-3">
      <section className="glass-surface rounded-[28px] p-4">
        <div className="flex items-center justify-between gap-2">
          <div className="min-w-0">
            <h2 className="text-base font-bold tracking-tight text-white">Мины</h2>
            <p className="truncate text-[11px] text-zinc-400">
              Поле 5×5 · Алмазы повышают множитель
            </p>
          </div>
          <div className="glass-chip shrink-0 rounded-2xl px-3 py-1.5 font-mono-num text-xs font-semibold text-zinc-200">
            {formatStars(user.balance_stars)} ⭐
          </div>
        </div>

        {/* Multiplier Status Strip */}
        <div className="mt-3 grid grid-cols-3 gap-2">
          <div className="glass-inset rounded-2xl px-3 py-2 text-center">
            <p className="text-[10px] text-zinc-500">Мин</p>
            <p className="font-mono-num text-sm font-bold text-white">
              {game ? game.mines_count : minesCount}
            </p>
          </div>
          <div className="glass-inset rounded-2xl px-3 py-2 text-center">
            <p className="text-[10px] text-zinc-500">Текущий</p>
            <p className="font-mono-num text-sm font-bold text-white">
              {game ? `${game.multiplier.toFixed(2)}x` : '1.00x'}
            </p>
          </div>
          <div className="glass-inset rounded-2xl px-3 py-2 text-center">
            <p className="text-[10px] text-zinc-500">Следующий</p>
            <p className="font-mono-num text-sm font-bold text-emerald-400">
              {game ? `${game.next_multiplier.toFixed(2)}x` : '—'}
            </p>
          </div>
        </div>

        {/* 5x5 Tactile Glass Grid */}
        <div className="glass-inset mt-3 rounded-3xl p-3">
          <div className="mx-auto grid max-w-[340px] grid-cols-5 gap-2">
            {Array.from({ length: 25 }).map((_, idx) => {
              const isRevealed = revealedSet.has(idx);
              const isMine = minesSet.has(idx);
              const showMine =
                (game?.status === 'lost' || game?.status === 'won') && isMine;
              const showSafe = isRevealed && !isMine;
              const isHitMine = isRevealed && isMine;

              return (
                <button
                  key={idx}
                  type="button"
                  disabled={!isGameActive || isRevealed || busy}
                  onClick={() => handleReveal(idx)}
                  className={`flex aspect-square items-center justify-center rounded-2xl border transition-all duration-150 ${
                    isHitMine
                      ? 'border-rose-400/50 bg-rose-500/25 text-rose-300 scale-95'
                      : showMine
                      ? 'border-white/10 bg-zinc-900/70 text-zinc-400'
                      : showSafe
                      ? 'border-white/35 bg-white/18 text-white shadow-inner scale-[0.98]'
                      : isGameActive
                      ? 'border-white/12 bg-white/[0.06] text-zinc-400 hover:border-white/30 hover:bg-white/[0.11] active:scale-95'
                      : 'border-white/[0.06] bg-white/[0.03] text-zinc-600'
                  }`}
                >
                  {showMine ? (
                    <Bomb className="h-5 w-5" />
                  ) : showSafe ? (
                    <Diamond className="h-5 w-5 fill-white/25 text-white" />
                  ) : (
                    <span className="h-1.5 w-1.5 rounded-full bg-white/20" />
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Evolving NFT Prize Preview */}
        {activeNftPreview && (
          <div className="glass-inset mt-3 flex items-center justify-between gap-3 rounded-2xl p-3">
            <div className="flex min-w-0 items-center gap-2.5">
              <div
                className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-white/10 bg-white/5 p-1"
                style={
                  activeNftPreview.centerHex && activeNftPreview.edgeHex
                    ? {
                        background: `radial-gradient(circle, ${activeNftPreview.centerHex}, ${activeNftPreview.edgeHex})`,
                      }
                    : undefined
                }
              >
                <img
                  src={resolveAssetUrl(activeNftPreview.imageUrl)}
                  alt={activeNftPreview.title}
                  className="h-9 w-9 object-contain"
                />
              </div>
              <div className="min-w-0">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-zinc-400">
                  {isGameActive ? 'Текущий приз NFT' : 'Пример апгрейда'}
                </p>
                <p className="truncate text-xs font-bold text-white">{activeNftPreview.title}</p>
                <p className="truncate text-[10px] text-zinc-400">{activeNftPreview.subtitle}</p>
              </div>
            </div>
            <div className="shrink-0 text-right font-mono-num">
              <p className="text-xs font-bold text-white">
                {formatStars(activeNftPreview.stars)} ⭐
              </p>
              {activeNftPreview.isUpgraded && (
                <span className="text-[10px] font-semibold text-emerald-400">Upgraded</span>
              )}
            </div>
          </div>
        )}

        {noticeMsg && (
          <div className="glass-card mt-3 rounded-2xl p-2.5 text-center text-xs font-medium text-white">
            {noticeMsg}
          </div>
        )}
        {errorMsg && (
          <div className="mt-3 rounded-2xl border border-rose-500/30 bg-rose-950/35 p-2.5 text-center text-xs text-rose-300">
            {errorMsg}
          </div>
        )}

        {/* Controls */}
        {isGameActive && game ? (
          <button
            type="button"
            disabled={busy || game.revealed.length < 1}
            onClick={handleCashout}
            className="mt-3 flex h-12 w-full items-center justify-center gap-2 rounded-2xl bg-white text-sm font-bold text-black transition-transform active:scale-[0.98] disabled:opacity-40"
          >
            <Diamond className="h-4 w-4" />
            <span>
              {game.revealed.length < 1
                ? 'Откройте первую клетку'
                : game.stake_type === 'nft'
                ? `Забрать NFT · ${activeNftPreview?.title || ''} (${game.multiplier.toFixed(2)}x)`
                : `Забрать ${formatStars(Math.round(game.stake_stars * game.multiplier))} ⭐ (${game.multiplier.toFixed(2)}x)`}
            </span>
          </button>
        ) : (
          <div className="glass-inset mt-3 space-y-3 rounded-3xl p-3.5">
            {/* Stars vs NFT Stake Toggle */}
            <div className="grid grid-cols-2 gap-1.5 rounded-2xl bg-white/[0.04] p-1">
              <button
                type="button"
                onClick={() => setStakeType('stars')}
                className={`flex min-h-[40px] items-center justify-center gap-1.5 rounded-xl text-xs font-semibold transition-colors ${
                  stakeType === 'stars' ? 'bg-white text-black shadow' : 'text-zinc-400'
                }`}
              >
                <Star className="h-3.5 w-3.5" />
                <span>Stars</span>
              </button>
              <button
                type="button"
                onClick={() => setStakeType('nft')}
                className={`flex min-h-[40px] items-center justify-center gap-1.5 rounded-xl text-xs font-semibold transition-colors ${
                  stakeType === 'nft' ? 'bg-white text-black shadow' : 'text-zinc-400'
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
                  type="text"
                  inputMode="decimal"
                  value={stakeStars}
                  onChange={(e) => setStakeStars(sanitizeDecimalInput(e.target.value))}
                  className="glass-inset h-11 w-full rounded-2xl px-3.5 font-mono-num text-sm text-white outline-none focus:border-white/35"
                />
                <div className="mt-1.5 flex gap-1.5">
                  {[500, 2500, 10000, 50000].map((v) => (
                    <button
                      key={v}
                      type="button"
                      onClick={() => setStakeStars(String(v))}
                      className="glass-chip min-h-[32px] flex-1 rounded-xl font-mono-num text-[11px] font-semibold text-zinc-300"
                    >
                      {formatStars(v)}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div>
                <div className="mb-2 flex items-center justify-between text-[11px] text-zinc-400">
                  <span>Выберите ваш NFT</span>
                  <span>Улучшается при каждой клетке</span>
                </div>
                {availableNfts.length === 0 ? (
                  <p className="glass-inset rounded-2xl p-3 text-xs text-zinc-500">
                    Нет свободных NFT в инвентаре.
                  </p>
                ) : (
                  <div className="no-scrollbar flex gap-2 overflow-x-auto pb-1">
                    {availableNfts.map((n) => {
                      const active = n.id === selectedNft?.id;
                      return (
                        <button
                          key={n.id}
                          type="button"
                          onClick={() => setSelectedNftId(n.id)}
                          className={`relative flex w-28 shrink-0 flex-col items-center rounded-2xl border p-2.5 text-center transition-colors ${
                            active
                              ? 'border-white/50 bg-white/15'
                              : 'border-white/10 bg-white/[0.03]'
                          }`}
                        >
                          {active && (
                            <span className="absolute top-1.5 right-1.5 flex h-4 w-4 items-center justify-center rounded-full bg-white text-black">
                              <Check className="h-2.5 w-2.5" />
                            </span>
                          )}
                          <div
                            className="flex h-11 w-11 items-center justify-center rounded-xl bg-white/5 p-1"
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

            {/* Mines Count Selector */}
            <div>
              <div className="mb-1.5 flex items-center justify-between text-[11px] text-zinc-400">
                <span>Количество мин</span>
                <span className="font-mono-num font-bold text-white">{minesCount} из 25</span>
              </div>
              <div className="grid grid-cols-5 gap-1.5">
                {MINE_PRESETS.map((m) => (
                  <button
                    key={m}
                    type="button"
                    onClick={() => setMinesCount(m)}
                    className={`min-h-[34px] rounded-xl border font-mono-num text-xs font-semibold transition-colors ${
                      minesCount === m
                        ? 'border-white bg-white text-black'
                        : 'glass-chip text-zinc-300'
                    }`}
                  >
                    {m}
                  </button>
                ))}
              </div>
            </div>

            <button
              type="button"
              disabled={busy || (stakeType === 'nft' && !selectedNft)}
              onClick={handleStart}
              className="flex h-12 w-full items-center justify-center rounded-2xl bg-white text-sm font-bold text-black transition-transform active:scale-[0.98] disabled:opacity-40"
            >
              {busy
                ? 'Запуск...'
                : stakeType === 'nft'
                ? `Играть с ${selectedNft ? selectedNft.model_name || selectedNft.name : 'NFT'}`
                : `Начать игру (${minesCount} мин)`}
            </button>
          </div>
        )}
      </section>
    </div>
  );
}
