import { useEffect, useState, type ChangeEvent } from 'react';
import { ArrowLeft, ArrowRightLeft, Coins, Plus, Upload, X } from 'lucide-react';
import { apiRequest, formatStars, formatTon, getTelegramWebApp, resolveAssetUrl } from '../api';
import { CandlestickChart } from './CandlestickChart';
import type { CandleData, CatalogData, MemecoinSummary, TradeData, UserProfile } from '../types';

interface ExchangeViewProps {
  user: UserProfile;
  catalog: CatalogData;
  coins: MemecoinSummary[];
  onRefreshAll: () => Promise<void>;
  onUserPatch: (patch: Partial<UserProfile>) => void;
}

export function ExchangeView({
  user,
  catalog,
  coins,
  onRefreshAll,
  onUserPatch,
}: ExchangeViewProps) {
  const [selectedCoinId, setSelectedCoinId] = useState<number | null>(null);
  const [coinDetail, setCoinDetail] = useState<{
    coin: MemecoinSummary;
    candles: CandleData[];
    trades: TradeData[];
  } | null>(null);

  // Swap state
  const [swapDir, setSwapDir] = useState<'stars_to_ton' | 'ton_to_stars'>('stars_to_ton');
  const [swapAmt, setSwapAmt] = useState<string>('10000');
  const [swapBusy, setSwapBusy] = useState(false);

  // Trade state
  const [tradeSide, setTradeSide] = useState<'buy' | 'sell'>('buy');
  const [tradeAmt, setTradeAmt] = useState<string>('5');
  const [tradeBusy, setTradeBusy] = useState(false);

  // Create Memecoin modal
  const [createOpen, setCreateOpen] = useState(false);
  const [newName, setNewName] = useState('');
  const [newTicker, setNewTicker] = useState('');
  const [newImageB64, setNewImageB64] = useState('');
  const [createBusy, setCreateBusy] = useState(false);

  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [noticeMsg, setNoticeMsg] = useState<string | null>(null);

  const loadCoinDetail = async (id: number) => {
    try {
      const res = await apiRequest<{
        coin: MemecoinSummary;
        candles: CandleData[];
        trades: TradeData[];
      }>(`/api/coins/${id}`);
      setCoinDetail({ coin: res.coin, candles: res.candles, trades: res.trades });
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Ошибка загрузки монеты');
    }
  };

  useEffect(() => {
    if (selectedCoinId !== null) {
      loadCoinDetail(selectedCoinId);
    }
  }, [selectedCoinId, coins]);

  const handleSwap = async () => {
    if (swapBusy) return;
    setErrorMsg(null);
    setNoticeMsg(null);
    setSwapBusy(true);
    try {
      const res = await apiRequest<{
        balance_stars: number;
        balance_tons: number;
        swapped_tons: number;
        swapped_stars: number;
      }>('/api/exchange/swap', {
        method: 'POST',
        body: JSON.stringify({ direction: swapDir, amount: Number(swapAmt || 0) }),
      });
      onUserPatch({
        balance_stars: res.balance_stars,
        balance_tons: res.balance_tons,
      });
      getTelegramWebApp()?.HapticFeedback?.notificationOccurred('success');
      setNoticeMsg(
        swapDir === 'stars_to_ton'
          ? `Обмен выполнен: +${formatTon(res.swapped_tons, 4)} TON`
          : `Обмен выполнен: +${formatStars(res.swapped_stars)} ⭐`
      );
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Ошибка обмена');
    } finally {
      setSwapBusy(false);
    }
  };

  const handleImagePick = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 800 * 1024) {
      setErrorMsg('Файл слишком большой (максимум 800 КБ).');
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result === 'string') {
        setNewImageB64(reader.result);
        setErrorMsg(null);
      }
    };
    reader.readAsDataURL(file);
  };

  const handleCreateCoin = async () => {
    if (createBusy) return;
    setErrorMsg(null);
    setNoticeMsg(null);
    setCreateBusy(true);
    try {
      const res = await apiRequest<{ coin: MemecoinSummary; balance_tons: number }>(
        '/api/coins/create',
        {
          method: 'POST',
          body: JSON.stringify({
            name: newName,
            ticker: newTicker,
            image_b64: newImageB64,
          }),
        }
      );
      onUserPatch({ balance_tons: res.balance_tons });
      setCreateOpen(false);
      setNewName('');
      setNewTicker('');
      setNewImageB64('');
      await onRefreshAll();
      setSelectedCoinId(res.coin.id);
      getTelegramWebApp()?.HapticFeedback?.notificationOccurred('success');
      setNoticeMsg(`Мемкоин ${res.coin.name} ($${res.coin.ticker}) запущен!`);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Не удалось создать мемкоин');
    } finally {
      setCreateBusy(false);
    }
  };

  const handleTrade = async () => {
    if (!coinDetail || tradeBusy) return;
    setErrorMsg(null);
    setNoticeMsg(null);
    setTradeBusy(true);
    try {
      const res = await apiRequest<{
        balance_tons: number;
        coin: MemecoinSummary;
        candles: CandleData[];
        trades: TradeData[];
      }>(`/api/coins/${coinDetail.coin.id}/trade`, {
        method: 'POST',
        body: JSON.stringify({ side: tradeSide, amount: Number(tradeAmt || 0) }),
      });
      onUserPatch({ balance_tons: res.balance_tons });
      setCoinDetail({ coin: res.coin, candles: res.candles, trades: res.trades });
      await onRefreshAll();
      getTelegramWebApp()?.HapticFeedback?.impactOccurred('light');
      setNoticeMsg(
        tradeSide === 'buy' ? 'Покупка выполнена по рынку!' : 'Токены успешно проданы!'
      );
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Ошибка сделки');
    } finally {
      setTradeBusy(false);
    }
  };

  const canCreateCoin =
    user.level > catalog.memecoin_min_level &&
    user.balance_tons >= catalog.memecoin_create_ton_cost;

  // Coin Detail View
  if (selectedCoinId !== null && coinDetail) {
    const c = coinDetail.coin;
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <button
            type="button"
            onClick={() => {
              setSelectedCoinId(null);
              setCoinDetail(null);
              setErrorMsg(null);
            }}
            className="flex min-h-[44px] items-center gap-1.5 rounded-2xl border border-white/10 bg-zinc-900 px-3.5 text-xs font-semibold text-white"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>Назад к бирже</span>
          </button>
          <span className="rounded-2xl border border-white/10 bg-zinc-900 px-3 py-2 font-mono-num text-xs font-semibold text-zinc-200">
            {formatTon(user.balance_tons, 2)} TON
          </span>
        </div>

        {/* Coin Header */}
        <section className="rounded-3xl border border-white/10 bg-zinc-900/90 p-5">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <img
                src={resolveAssetUrl(c.image_url)}
                alt={c.name}
                className="h-12 w-12 shrink-0 rounded-2xl border border-white/10 bg-black object-cover"
              />
              <div className="min-w-0">
                <h2 className="truncate text-lg font-bold text-white">{c.name}</h2>
                <p className="font-mono-num text-xs text-zinc-400">
                  ${c.ticker} · Ликвидность {formatTon(c.reserve_ton, 1)} TON
                </p>
              </div>
            </div>
            <div className="text-right font-mono-num">
              <p className="text-base font-bold text-white">{formatTon(c.price_ton, 6)} TON</p>
              <p
                className={`text-xs font-semibold ${
                  c.change_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'
                }`}
              >
                {c.change_pct >= 0 ? `+${c.change_pct}%` : `${c.change_pct}%`}
              </p>
            </div>
          </div>

          <div className="mt-4 grid grid-cols-3 gap-2">
            <div className="rounded-2xl bg-zinc-950 p-3">
              <p className="text-[10px] uppercase tracking-wider text-zinc-500">Капитализация</p>
              <p className="mt-1 font-mono-num text-xs font-bold text-white">
                {formatTon(c.market_cap_ton, 1)} TON
              </p>
            </div>
            <div className="rounded-2xl bg-zinc-950 p-3">
              <p className="text-[10px] uppercase tracking-wider text-zinc-500">Объём</p>
              <p className="mt-1 font-mono-num text-xs font-bold text-white">
                {formatTon(c.volume_24h_ton, 1)} TON
              </p>
            </div>
            <div className="rounded-2xl bg-zinc-950 p-3">
              <p className="text-[10px] uppercase tracking-wider text-zinc-500">У вас</p>
              <p className="mt-1 font-mono-num text-xs font-bold text-white">
                {formatTon(c.my_balance, 2)} ${c.ticker}
              </p>
            </div>
          </div>
        </section>

        <CandlestickChart candles={coinDetail.candles} />

        {noticeMsg && (
          <div className="rounded-2xl border border-white/20 bg-zinc-900 p-3 text-center text-xs font-medium text-white">
            {noticeMsg}
          </div>
        )}
        {errorMsg && (
          <div className="rounded-2xl border border-rose-500/30 bg-rose-950/30 p-3 text-center text-xs text-rose-300">
            {errorMsg}
          </div>
        )}

        {/* Buy / Sell Terminal */}
        <section className="rounded-3xl border border-white/10 bg-zinc-900/90 p-5 space-y-3">
          <div className="grid grid-cols-2 gap-2 rounded-2xl bg-zinc-950 p-1">
            <button
              type="button"
              onClick={() => {
                setTradeSide('buy');
                setTradeAmt('5');
              }}
              className={`min-h-[44px] rounded-xl text-xs font-bold ${
                tradeSide === 'buy' ? 'bg-white text-black' : 'text-zinc-400'
              }`}
            >
              Купить
            </button>
            <button
              type="button"
              onClick={() => {
                setTradeSide('sell');
                setTradeAmt(c.my_balance > 0 ? String(c.my_balance) : '0');
              }}
              className={`min-h-[44px] rounded-xl text-xs font-bold ${
                tradeSide === 'sell' ? 'bg-white text-black' : 'text-zinc-400'
              }`}
            >
              Продать
            </button>
          </div>

          <div>
            <div className="mb-1.5 flex items-center justify-between text-xs text-zinc-400">
              <span>{tradeSide === 'buy' ? 'Сумма в TON' : `Количество $${c.ticker}`}</span>
              <span className="font-mono-num">
                Доступно:{' '}
                {tradeSide === 'buy'
                  ? `${formatTon(user.balance_tons, 2)} TON`
                  : `${formatTon(c.my_balance, 2)} $${c.ticker}`}
              </span>
            </div>
            <input
              type="number"
              step="any"
              min={0}
              value={tradeAmt}
              onChange={(e) => setTradeAmt(e.target.value)}
              className="h-12 w-full rounded-2xl border border-white/10 bg-black px-4 font-mono-num text-sm font-semibold text-white outline-none focus:border-white/40"
            />
            <div className="mt-2 flex gap-2">
              {[0.25, 0.5, 1].map((pct) => (
                <button
                  key={pct}
                  type="button"
                  onClick={() => {
                    const base = tradeSide === 'buy' ? user.balance_tons : c.my_balance;
                    setTradeAmt(String(Number((base * pct).toFixed(4))));
                  }}
                  className="min-h-[36px] flex-1 rounded-xl border border-white/10 bg-zinc-950 font-mono-num text-xs font-semibold text-zinc-300"
                >
                  {pct * 100}%
                </button>
              ))}
            </div>
          </div>

          <button
            type="button"
            disabled={tradeBusy}
            onClick={handleTrade}
            className="h-12 w-full rounded-2xl bg-white text-sm font-bold text-black transition-transform active:scale-[0.98] disabled:opacity-40"
          >
            {tradeBusy
              ? 'Исполняем ордер...'
              : tradeSide === 'buy'
              ? `Купить $${c.ticker}`
              : `Продать $${c.ticker}`}
          </button>
        </section>

        {/* Recent Trades */}
        {coinDetail.trades.length > 0 && (
          <section className="rounded-3xl border border-white/10 bg-zinc-900/80 p-4">
            <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-zinc-400">
              Последние сделки
            </h3>
            <div className="space-y-2">
              {coinDetail.trades.slice(0, 10).map((t) => (
                <div
                  key={t.id}
                  className="flex items-center justify-between rounded-2xl bg-zinc-950 px-3 py-2 text-xs font-mono-num"
                >
                  <span className={t.side === 'buy' ? 'font-semibold text-emerald-400' : 'font-semibold text-rose-400'}>
                    {t.side === 'buy' ? 'BUY' : 'SELL'}
                  </span>
                  <span className="text-zinc-200">{formatTon(t.ton_amount, 2)} TON</span>
                  <span className="text-zinc-400">{formatTon(t.token_amount, 1)} ${c.ticker}</span>
                </div>
              ))}
            </div>
          </section>
        )}
      </div>
    );
  }

  // Exchange Hub View
  return (
    <div className="space-y-4">
      {/* Balances + Swap */}
      <section className="rounded-3xl border border-white/10 bg-zinc-900/90 p-5">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold tracking-tight text-white">Криптобиржа</h2>
            <p className="text-xs text-zinc-400">
              Курс: 1 TON = {formatStars(catalog.ton_star_rate)} ⭐
            </p>
          </div>
          <button
            type="button"
            onClick={() => {
              setErrorMsg(null);
              setCreateOpen(true);
            }}
            className="flex min-h-[42px] items-center gap-1.5 rounded-2xl bg-white px-3.5 text-xs font-bold text-black transition-transform active:scale-95"
          >
            <Plus className="h-4 w-4" />
            <span>Создать мемкоин</span>
          </button>
        </div>

        {/* Swapper */}
        <div className="mt-4 rounded-3xl border border-white/10 bg-zinc-950 p-4 space-y-3">
          <div className="flex items-center justify-between text-xs text-zinc-400">
            <span className="font-semibold text-white">Обменник валют</span>
            <button
              type="button"
              onClick={() => {
                setSwapDir((d) => (d === 'stars_to_ton' ? 'ton_to_stars' : 'stars_to_ton'));
                setSwapAmt(swapDir === 'stars_to_ton' ? '10' : '10000');
              }}
              className="flex min-h-[36px] items-center gap-1.5 rounded-xl border border-white/10 bg-zinc-900 px-3 text-xs font-semibold text-zinc-200"
            >
              <ArrowRightLeft className="h-3.5 w-3.5" />
              <span>{swapDir === 'stars_to_ton' ? 'Stars → TON' : 'TON → Stars'}</span>
            </button>
          </div>

          <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-[1fr_auto]">
            <input
              type="number"
              min={0}
              step="any"
              value={swapAmt}
              onChange={(e) => setSwapAmt(e.target.value)}
              placeholder={swapDir === 'stars_to_ton' ? 'Количество Stars' : 'Количество TON'}
              className="h-12 w-full rounded-2xl border border-white/10 bg-black px-4 font-mono-num text-sm font-semibold text-white outline-none focus:border-white/40"
            />
            <button
              type="button"
              disabled={swapBusy}
              onClick={handleSwap}
              className="h-12 rounded-2xl bg-white px-6 text-xs font-bold text-black transition-transform active:scale-95 disabled:opacity-40"
            >
              {swapBusy ? 'Обмен...' : 'Обменять'}
            </button>
          </div>

          <div className="flex items-center justify-between text-[11px] font-mono-num text-zinc-400">
            <span>Stars: {formatStars(user.balance_stars)} ⭐</span>
            <span>TON: {formatTon(user.balance_tons, 2)} TON</span>
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
      </section>

      {/* Coins List ("Купить валюту") */}
      <section className="rounded-3xl border border-white/10 bg-zinc-900/80 p-4">
        <div className="mb-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Coins className="h-4 w-4 text-zinc-300" />
            <h3 className="text-sm font-semibold text-white">Купить валюту · Мемкоины</h3>
          </div>
          <span className="font-mono-num text-xs text-zinc-400">{coins.length} токенов</span>
        </div>

        {coins.length === 0 ? (
          <p className="py-6 text-center text-xs text-zinc-500">
            Мемкоины ещё не созданы. Станьте первым!
          </p>
        ) : (
          <div className="space-y-2.5">
            {coins.map((c) => (
              <button
                key={c.id}
                type="button"
                onClick={() => setSelectedCoinId(c.id)}
                className="flex w-full items-center justify-between rounded-2xl border border-white/10 bg-zinc-950 p-3.5 text-left transition-colors hover:border-white/25 active:scale-[0.99]"
              >
                <div className="flex min-w-0 items-center gap-3">
                  <img
                    src={resolveAssetUrl(c.image_url)}
                    alt={c.name}
                    className="h-11 w-11 shrink-0 rounded-2xl border border-white/10 bg-black object-cover"
                  />
                  <div className="min-w-0">
                    <p className="truncate text-sm font-bold text-white">{c.name}</p>
                    <p className="mt-0.5 font-mono-num text-[11px] text-zinc-400">
                      ${c.ticker} · MCap {formatTon(c.market_cap_ton, 1)} TON
                    </p>
                  </div>
                </div>
                <div className="shrink-0 text-right font-mono-num">
                  <p className="text-xs font-bold text-white">{formatTon(c.price_ton, 6)} TON</p>
                  <p
                    className={`mt-0.5 text-[11px] font-semibold ${
                      c.change_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'
                    }`}
                  >
                    {c.change_pct >= 0 ? `+${c.change_pct}%` : `${c.change_pct}%`}
                  </p>
                </div>
              </button>
            ))}
          </div>
        )}
      </section>

      {/* Create Memecoin Sheet */}
      {createOpen && (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/75 backdrop-blur-sm sm:items-center sm:p-4">
          <div className="w-full max-w-md rounded-t-3xl border border-white/15 bg-zinc-900 p-5 sm:rounded-3xl">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-white">Создать свой мемкоин</h3>
              <button
                type="button"
                onClick={() => setCreateOpen(false)}
                className="flex h-10 w-10 items-center justify-center rounded-full bg-zinc-800 text-zinc-300"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="mt-4 space-y-2 rounded-2xl border border-white/10 bg-zinc-950 p-3.5 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-zinc-400">Уровень выше {catalog.memecoin_min_level}</span>
                <span className={user.level > catalog.memecoin_min_level ? 'font-bold text-white' : 'text-rose-400'}>
                  Ваш: {user.level}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-zinc-400">Стоимость (20 млн ⭐ в TON)</span>
                <span className={user.balance_tons >= catalog.memecoin_create_ton_cost ? 'font-bold text-white' : 'text-rose-400'}>
                  {formatTon(catalog.memecoin_create_ton_cost, 0)} TON
                </span>
              </div>
            </div>

            <div className="mt-4 space-y-3">
              <div>
                <label className="mb-1 block text-xs text-zinc-400">Название монеты</label>
                <input
                  type="text"
                  maxLength={32}
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="Например: Durov Coin"
                  className="h-11 w-full rounded-2xl border border-white/10 bg-black px-3.5 text-sm text-white outline-none focus:border-white/40"
                />
              </div>

              <div>
                <label className="mb-1 block text-xs text-zinc-400">Тикер (2–8 символов)</label>
                <input
                  type="text"
                  maxLength={8}
                  value={newTicker}
                  onChange={(e) => setNewTicker(e.target.value.toUpperCase())}
                  placeholder="DUROV"
                  className="h-11 w-full rounded-2xl border border-white/10 bg-black px-3.5 font-mono-num text-sm uppercase text-white outline-none focus:border-white/40"
                />
              </div>

              <div>
                <label className="mb-1 block text-xs text-zinc-400">Аватар монеты (PNG/JPG/WEBP)</label>
                <label className="flex min-h-[56px] cursor-pointer items-center justify-center gap-2 rounded-2xl border border-dashed border-white/20 bg-black px-4 py-2 text-xs font-medium text-zinc-300">
                  {newImageB64 ? (
                    <img
                      src={newImageB64}
                      alt="Preview"
                      className="h-10 w-10 rounded-xl object-cover"
                    />
                  ) : (
                    <Upload className="h-4 w-4" />
                  )}
                  <span>{newImageB64 ? 'Изображение выбрано' : 'Загрузить изображение'}</span>
                  <input
                    type="file"
                    accept="image/png,image/jpeg,image/webp"
                    onChange={handleImagePick}
                    className="hidden"
                  />
                </label>
              </div>
            </div>

            {errorMsg && (
              <p className="mt-3 text-center text-xs text-rose-400">{errorMsg}</p>
            )}

            <button
              type="button"
              disabled={!canCreateCoin || createBusy || !newName.trim() || !newImageB64}
              onClick={handleCreateCoin}
              className="mt-5 h-12 w-full rounded-2xl bg-white text-sm font-bold text-black transition-transform active:scale-[0.98] disabled:opacity-40"
            >
              {createBusy ? 'Выпуск монеты...' : `Выпустить за ${formatTon(catalog.memecoin_create_ton_cost, 0)} TON`}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
