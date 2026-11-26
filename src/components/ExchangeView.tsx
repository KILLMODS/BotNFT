import { useEffect, useMemo, useState, type ChangeEvent } from 'react';
import {
  ArrowLeft,
  ArrowRightLeft,
  ArrowUpDown,
  CheckCircle2,
  Coins,
  Plus,
  Send,
  ShieldAlert,
  Upload,
  X,
} from 'lucide-react';
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

function formatCompactNum(val: number, decimals = 2): string {
  const n = Number(val || 0);
  if (!Number.isFinite(n)) return '0';
  const abs = Math.abs(n);
  if (abs >= 1_000_000_000) return `${(n / 1_000_000_000).toFixed(decimals)}B`;
  if (abs >= 1_000_000) return `${(n / 1_000_000).toFixed(decimals)}M`;
  if (abs >= 10_000) return `${(n / 1_000).toFixed(1)}K`;
  if (abs >= 100) return n.toLocaleString('en-US', { maximumFractionDigits: 1 });
  return n.toLocaleString('en-US', { maximumFractionDigits: decimals });
}

function formatTokenPrice(tonPrice: number): string {
  const n = Number(tonPrice || 0);
  if (n <= 0) return '0';
  if (n < 0.0001) return n.toFixed(7);
  if (n < 0.01) return n.toFixed(6);
  if (n < 1) return n.toFixed(4);
  return n.toFixed(3);
}

function formatStarEquivalent(stars: number): string {
  if (stars >= 100) return formatStars(Math.round(stars));
  if (stars >= 1) return stars.toFixed(2);
  return stars.toFixed(3);
}

export function ExchangeView({
  user,
  catalog,
  coins,
  onRefreshAll,
  onUserPatch,
}: ExchangeViewProps) {
  const [subView, setSubView] = useState<'hub' | 'swapper'>('hub');
  const [selectedCoinId, setSelectedCoinId] = useState<number | null>(null);
  const [coinDetail, setCoinDetail] = useState<{
    coin: MemecoinSummary;
    candles: CandleData[];
    trades: TradeData[];
  } | null>(null);

  // Dedicated Swapper state
  const [swapDir, setSwapDir] = useState<'stars_to_ton' | 'ton_to_stars'>('stars_to_ton');
  const [swapAmt, setSwapAmt] = useState<string>('10000');
  const [swapBusy, setSwapBusy] = useState(false);

  // Token-based Trade state
  const [tradeSide, setTradeSide] = useState<'buy' | 'sell'>('buy');
  const [tradeTokensAmt, setTradeTokensAmt] = useState<string>('1000');
  const [tradeBusy, setTradeBusy] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);

  // Transfer Memecoin modal
  const [transferOpen, setTransferOpen] = useState(false);
  const [transferRecipient, setTransferRecipient] = useState('');
  const [transferAmount, setTransferAmount] = useState('');
  const [transferBusy, setTransferBusy] = useState(false);

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

  const swapNumeric = Math.max(0, Number(swapAmt || 0));
  const swapReceiveAmount = useMemo(() => {
    const rate = catalog.ton_star_rate || 1000;
    if (!Number.isFinite(swapNumeric) || swapNumeric <= 0) return 0;
    return swapDir === 'stars_to_ton'
      ? Number((swapNumeric / rate).toFixed(4))
      : Math.round(swapNumeric * rate);
  }, [swapNumeric, swapDir, catalog.ton_star_rate]);

  const handleFlipSwap = () => {
    const nextDir = swapDir === 'stars_to_ton' ? 'ton_to_stars' : 'stars_to_ton';
    setSwapDir(nextDir);
    setSwapAmt(nextDir === 'stars_to_ton' ? '10000' : '10');
    setErrorMsg(null);
    setNoticeMsg(null);
  };

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

  // Smooth uncapped bonding curve quote calculation for token-based buy & sell
  const tradeQuote = useMemo(() => {
    if (!coinDetail) return null;
    const c = coinDetail.coin;
    const tokQty = Number(tradeTokensAmt || 0);
    if (!Number.isFinite(tokQty) || tokQty <= 0) {
      return { valid: false, reason: 'Введите количество токенов больше 0', tonCost: 0, grossTon: 0, feeTon: 0, netTon: 0 };
    }
    const curPrice = Math.max(0.00001, c.price_ton);
    const slope = 0.0002 / Math.max(100_000_000, c.total_supply);

    if (tradeSide === 'buy') {
      if (tokQty < 1) {
        return { valid: false, reason: 'Минимум — 1 токен', tonCost: 0, grossTon: 0, feeTon: 0, netTon: 0 };
      }
      const newPrice = Math.max(0.00001, curPrice + slope * tokQty);
      const tonCost = Number(Math.max(0.000001, tokQty * (curPrice + newPrice) * 0.5).toFixed(6));
      if (tonCost > user.balance_tons + 1e-9) {
        return { valid: false, reason: `Недостаточно TON (нужно ${tonCost.toFixed(4)} TON)`, tonCost, grossTon: 0, feeTon: 0, netTon: 0 };
      }
      return { valid: true, reason: '', tonCost, grossTon: 0, feeTon: 0, netTon: 0 };
    } else {
      if (tokQty > c.my_balance + 1e-6) {
        return { valid: false, reason: 'Недостаточно токенов на балансе', tonCost: 0, grossTon: 0, feeTon: 0, netTon: 0 };
      }
      const newPrice = Math.max(0.00005, curPrice - slope * tokQty);
      const grossTon = Math.max(0, tokQty * (curPrice + newPrice) * 0.5);
      const feeTon = grossTon * 0.15;
      const netTon = grossTon * 0.85;
      if (netTon < 0.000001) {
        return { valid: false, reason: 'Слишком маленькое количество для продажи', tonCost: 0, grossTon, feeTon, netTon };
      }
      return { valid: true, reason: '', tonCost: 0, grossTon, feeTon, netTon };
    }
  }, [coinDetail, tradeSide, tradeTokensAmt, user.balance_tons]);

  const handleOpenTradeConfirm = () => {
    setErrorMsg(null);
    setNoticeMsg(null);
    if (!tradeQuote?.valid) {
      setErrorMsg(tradeQuote?.reason || 'Проверьте сумму сделки.');
      return;
    }
    setConfirmOpen(true);
  };

  const handleConfirmTrade = async () => {
    if (!coinDetail || tradeBusy) return;
    setErrorMsg(null);
    setNoticeMsg(null);
    setTradeBusy(true);
    try {
      const res = await apiRequest<{
        balance_tons: number;
        ton_amount?: number;
        fee_ton?: number;
        tokens_delta?: number;
        user?: UserProfile;
        coin: MemecoinSummary;
        candles: CandleData[];
        trades: TradeData[];
      }>(`/api/coins/${coinDetail.coin.id}/trade`, {
        method: 'POST',
        body: JSON.stringify({
          side: tradeSide,
          amount: Number(tradeTokensAmt || 0),
          unit: 'tokens',
        }),
      });
      if (res.user) {
        onUserPatch(res.user);
      } else {
        onUserPatch({ balance_tons: res.balance_tons });
      }
      setCoinDetail({ coin: res.coin, candles: res.candles, trades: res.trades });
      setConfirmOpen(false);
      await onRefreshAll();
      getTelegramWebApp()?.HapticFeedback?.notificationOccurred('success');
      const finalTon = Number(res.ton_amount ?? res.trades?.[0]?.ton_amount ?? (tradeSide === 'buy' ? tradeQuote?.tonCost : tradeQuote?.netTon) ?? 0);
      if (tradeSide === 'buy') {
        setNoticeMsg(
          `Куплено ${formatCompactNum(res.tokens_delta || Number(tradeTokensAmt), 2)} $${res.coin.ticker} за ${finalTon.toFixed(4)} TON`
        );
      } else {
        setNoticeMsg(
          `Продано ${formatCompactNum(res.tokens_delta || Number(tradeTokensAmt), 2)} $${res.coin.ticker} · получено +${finalTon.toFixed(4)} TON`
        );
      }
    } catch (err) {
      setConfirmOpen(false);
      setErrorMsg(err instanceof Error ? err.message : 'Ошибка сделки');
    } finally {
      setTradeBusy(false);
    }
  };

  const handleTransferCoin = async () => {
    if (!coinDetail || transferBusy) return;
    const amt = Number(transferAmount || 0);
    const rec = transferRecipient.trim();
    if (!rec) {
      setErrorMsg('Укажите @username или Telegram ID получателя.');
      return;
    }
    if (!Number.isFinite(amt) || amt <= 0) {
      setErrorMsg('Укажите количество токенов больше 0.');
      return;
    }
    if (amt > coinDetail.coin.my_balance + 1e-6) {
      setErrorMsg('Недостаточно токенов на балансе.');
      return;
    }
    setErrorMsg(null);
    setNoticeMsg(null);
    setTransferBusy(true);
    try {
      const res = await apiRequest<{
        transferred_amount: number;
        recipient_label: string;
        coin: MemecoinSummary;
        candles: CandleData[];
        trades: TradeData[];
      }>(`/api/coins/${coinDetail.coin.id}/transfer`, {
        method: 'POST',
        body: JSON.stringify({
          recipient: rec,
          amount: amt,
        }),
      });
      setCoinDetail({ coin: res.coin, candles: res.candles, trades: res.trades });
      setTransferOpen(false);
      setTransferRecipient('');
      setTransferAmount('');
      await onRefreshAll();
      getTelegramWebApp()?.HapticFeedback?.notificationOccurred('success');
      setNoticeMsg(
        `Переведено ${formatCompactNum(res.transferred_amount, 2)} $${res.coin.ticker} → ${res.recipient_label}`
      );
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Не удалось выполнить перевод');
    } finally {
      setTransferBusy(false);
    }
  };

  const canCreateCoin =
    user.level > catalog.memecoin_min_level &&
    user.balance_tons >= catalog.memecoin_create_ton_cost;

  // 1. Coin Detail Terminal
  if (selectedCoinId !== null && coinDetail) {
    const c = coinDetail.coin;
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between gap-2">
          <button
            type="button"
            onClick={() => {
              setSelectedCoinId(null);
              setCoinDetail(null);
              setConfirmOpen(false);
              setErrorMsg(null);
              setNoticeMsg(null);
            }}
            className="flex min-h-[42px] items-center gap-1.5 rounded-2xl border border-white/10 bg-zinc-900 px-3.5 text-xs font-semibold text-white"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>К бирже</span>
          </button>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => {
                setErrorMsg(null);
                setNoticeMsg(null);
                setTransferAmount(c.my_balance > 0 ? String(Math.floor(c.my_balance)) : '');
                setTransferOpen(true);
              }}
              className="flex min-h-[42px] items-center gap-1.5 rounded-2xl border border-white/15 bg-zinc-900 px-3 text-xs font-semibold text-white transition-transform active:scale-95"
            >
              <Send className="h-3.5 w-3.5" />
              <span>Передать монету</span>
            </button>
            <span className="truncate rounded-2xl border border-white/10 bg-zinc-900 px-3 py-2 font-mono-num text-xs font-semibold text-zinc-200">
              {formatTon(user.balance_tons, 2)} TON
            </span>
          </div>
        </div>

        {/* Coin Header & Overflow-safe 2x2 Stats */}
        <section className="rounded-3xl border border-white/10 bg-zinc-900/90 p-4 sm:p-5">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 flex-1 items-center gap-3">
              <img
                src={resolveAssetUrl(c.image_url)}
                alt={c.name}
                className="h-12 w-12 shrink-0 rounded-2xl border border-white/10 bg-black object-cover"
              />
              <div className="min-w-0">
                <h2 className="truncate text-base font-bold text-white sm:text-lg">{c.name}</h2>
                <p className="truncate font-mono-num text-xs text-zinc-400">
                  ${c.ticker} · {c.holders_count} держат.
                </p>
              </div>
            </div>
            <div className="shrink-0 text-right font-mono-num">
              <p className="text-sm font-bold text-white sm:text-base">
                {formatTokenPrice(c.price_ton)} TON
              </p>
              <p
                className={`text-xs font-semibold ${
                  c.change_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'
                }`}
              >
                {c.change_pct >= 0 ? `+${c.change_pct}%` : `${c.change_pct}%`}
              </p>
            </div>
          </div>

          <div className="mt-4 grid grid-cols-2 gap-2.5">
            <div className="min-w-0 rounded-2xl bg-zinc-950 p-3">
              <p className="text-[10px] uppercase tracking-wider text-zinc-500">Цена за 1 токен</p>
              <p className="mt-1 truncate font-mono-num text-xs font-bold text-white">
                {formatTokenPrice(c.price_ton)} TON
              </p>
              <p className="truncate font-mono-num text-[10px] text-zinc-400">
                ≈ {formatStarEquivalent(c.price_stars)} ⭐
              </p>
            </div>
            <div className="min-w-0 rounded-2xl bg-zinc-950 p-3">
              <p className="text-[10px] uppercase tracking-wider text-zinc-500">Капитализация</p>
              <p className="mt-1 truncate font-mono-num text-xs font-bold text-white">
                {formatCompactNum(c.market_cap_ton, 2)} TON
              </p>
              <p className="truncate font-mono-num text-[10px] text-zinc-400">
                Эмиссия: {formatCompactNum(c.total_supply, 0)}
              </p>
            </div>
            <div className="min-w-0 rounded-2xl bg-zinc-950 p-3">
              <p className="text-[10px] uppercase tracking-wider text-zinc-500">Пул ликвидности</p>
              <p className="mt-1 truncate font-mono-num text-xs font-bold text-white">
                {formatCompactNum(c.reserve_ton, 2)} TON
              </p>
              <p className="truncate font-mono-num text-[10px] text-zinc-400">
                Объём: {formatCompactNum(c.volume_24h_ton, 1)} TON
              </p>
            </div>
            <div className="min-w-0 rounded-2xl bg-zinc-950 p-3">
              <p className="text-[10px] uppercase tracking-wider text-zinc-500">Ваш баланс</p>
              <p className="mt-1 truncate font-mono-num text-xs font-bold text-white">
                {formatCompactNum(c.my_balance, 2)} ${c.ticker}
              </p>
              <p className="truncate font-mono-num text-[10px] text-zinc-400">
                ≈ {formatCompactNum(c.my_balance * c.price_ton, 3)} TON
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

        {/* Token-based Buy / Sell Terminal */}
        <section className="space-y-3 rounded-3xl border border-white/10 bg-zinc-900/90 p-4 sm:p-5">
          <div className="grid grid-cols-2 gap-2 rounded-2xl bg-zinc-950 p-1">
            <button
              type="button"
              onClick={() => {
                setTradeSide('buy');
                setTradeTokensAmt('1000');
                setErrorMsg(null);
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
                setTradeTokensAmt(c.my_balance > 0 ? String(Math.floor(c.my_balance)) : '0');
                setErrorMsg(null);
              }}
              className={`min-h-[44px] rounded-xl text-xs font-bold ${
                tradeSide === 'sell' ? 'bg-white text-black' : 'text-zinc-400'
              }`}
            >
              Продать
            </button>
          </div>

          <div>
            <div className="mb-1.5 flex items-center justify-between gap-2 text-xs text-zinc-400">
              <span>Количество токенов (${c.ticker})</span>
              <span className="truncate font-mono-num">
                {tradeSide === 'buy'
                  ? `Баланс: ${formatCompactNum(user.balance_tons, 2)} TON`
                  : `У вас: ${formatCompactNum(c.my_balance, 2)} $${c.ticker}`}
              </span>
            </div>

            <input
              type="number"
              step="any"
              min={0}
              value={tradeTokensAmt}
              onChange={(e) => setTradeTokensAmt(e.target.value)}
              placeholder={`Кол-во $${c.ticker}`}
              className="h-12 w-full rounded-2xl border border-white/10 bg-black px-4 font-mono-num text-sm font-semibold text-white outline-none focus:border-white/40"
            />

            {tradeSide === 'buy' ? (
              <div className="mt-2 grid grid-cols-5 gap-1.5">
                {[1000, 10000, 100000, 1000000, 5000000].map((qty) => (
                  <button
                    key={qty}
                    type="button"
                    onClick={() => setTradeTokensAmt(String(qty))}
                    className="min-h-[36px] rounded-xl border border-white/10 bg-zinc-950 font-mono-num text-[11px] font-semibold text-zinc-300 active:scale-95"
                  >
                    {formatCompactNum(qty, 0)}
                  </button>
                ))}
              </div>
            ) : (
              <div className="mt-2 grid grid-cols-4 gap-2">
                {[0.25, 0.5, 0.75, 1].map((pct) => (
                  <button
                    key={pct}
                    type="button"
                    onClick={() =>
                      setTradeTokensAmt(String(Number((c.my_balance * pct).toFixed(2))))
                    }
                    className="min-h-[36px] rounded-xl border border-white/10 bg-zinc-950 font-mono-num text-xs font-semibold text-zinc-300 active:scale-95"
                  >
                    {pct * 100}%
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Live Quote Preview */}
          {tradeQuote && (
            <div className="space-y-1.5 rounded-2xl border border-white/10 bg-zinc-950 p-3 text-xs font-mono-num">
              <div className="flex items-center justify-between gap-2 text-zinc-400">
                <span>Цена за 1 токен</span>
                <span className="text-zinc-200">{formatTokenPrice(c.price_ton)} TON</span>
              </div>
              {tradeSide === 'buy' ? (
                <div className="flex items-center justify-between gap-2">
                  <span className="text-zinc-400">К оплате</span>
                  <span className="font-bold text-white">
                    {tradeQuote.tonCost > 0 ? `${tradeQuote.tonCost.toFixed(4)} TON` : '—'}
                  </span>
                </div>
              ) : (
                <>
                  <div className="flex items-center justify-between gap-2 text-zinc-400">
                    <span>Комиссия рынка (15%)</span>
                    <span className="text-amber-400">-{tradeQuote.feeTon.toFixed(4)} TON</span>
                  </div>
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-zinc-400">Вы получите</span>
                    <span className="font-bold text-emerald-400">
                      +{tradeQuote.netTon.toFixed(4)} TON
                    </span>
                  </div>
                </>
              )}
              {!tradeQuote.valid && (
                <p className="pt-1 text-[11px] font-sans text-rose-400">{tradeQuote.reason}</p>
              )}
            </div>
          )}

          <button
            type="button"
            disabled={tradeBusy || !tradeQuote?.valid}
            onClick={handleOpenTradeConfirm}
            className="h-12 w-full rounded-2xl bg-white text-sm font-bold text-black transition-transform active:scale-[0.98] disabled:opacity-40"
          >
            {tradeSide === 'buy'
              ? `Купить ${formatCompactNum(Number(tradeTokensAmt || 0), 0)} $${c.ticker}`
              : `Продать ${formatCompactNum(Number(tradeTokensAmt || 0), 0)} $${c.ticker}`}
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
                  className="flex items-center justify-between gap-2 rounded-2xl bg-zinc-950 px-3 py-2 text-xs font-mono-num"
                >
                  <span
                    className={
                      t.side === 'buy'
                        ? 'shrink-0 font-semibold text-emerald-400'
                        : 'shrink-0 font-semibold text-rose-400'
                    }
                  >
                    {t.side === 'buy' ? 'BUY' : 'SELL'}
                  </span>
                  <span className="truncate text-zinc-200">{formatTon(t.ton_amount, 3)} TON</span>
                  <span className="truncate text-zinc-400">
                    {formatCompactNum(t.token_amount, 1)} ${c.ticker}
                  </span>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Trade Confirmation Modal */}
        {confirmOpen && tradeQuote && (
          <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/80 backdrop-blur-sm sm:items-center sm:p-4">
            <div className="w-full max-w-md rounded-t-3xl border border-white/15 bg-zinc-900 p-5 sm:rounded-3xl">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <ShieldAlert className="h-5 w-5 text-white" />
                  <h3 className="text-base font-bold text-white">
                    {tradeSide === 'buy' ? 'Подтверждение покупки' : 'Подтверждение продажи'}
                  </h3>
                </div>
                <button
                  type="button"
                  onClick={() => setConfirmOpen(false)}
                  className="flex h-9 w-9 items-center justify-center rounded-full bg-zinc-800 text-zinc-300"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              <div className="mt-4 space-y-2.5 rounded-2xl border border-white/10 bg-zinc-950 p-4 text-xs">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-zinc-400">Монета</span>
                  <span className="font-bold text-white">
                    {c.name} (${c.ticker})
                  </span>
                </div>
                <div className="flex items-center justify-between gap-2">
                  <span className="text-zinc-400">Количество</span>
                  <span className="font-mono-num font-bold text-white">
                    {formatCompactNum(Number(tradeTokensAmt || 0), 2)} ${c.ticker}
                  </span>
                </div>
                <div className="flex items-center justify-between gap-2">
                  <span className="text-zinc-400">Курс (1 токен)</span>
                  <span className="font-mono-num text-zinc-200">
                    {formatTokenPrice(c.price_ton)} TON
                  </span>
                </div>
                {tradeSide === 'buy' ? (
                  <div className="flex items-center justify-between gap-2 border-t border-white/10 pt-2.5">
                    <span className="font-semibold text-zinc-300">Итого списание</span>
                    <span className="font-mono-num text-sm font-bold text-white">
                      {tradeQuote.tonCost.toFixed(4)} TON
                    </span>
                  </div>
                ) : (
                  <>
                    <div className="flex items-center justify-between gap-2 border-t border-white/10 pt-2.5">
                      <span className="text-zinc-400">Сумма до комиссии</span>
                      <span className="font-mono-num text-zinc-200">
                        {tradeQuote.grossTon.toFixed(4)} TON
                      </span>
                    </div>
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-zinc-400">Комиссия рынка (15%)</span>
                      <span className="font-mono-num text-amber-400">
                        -{tradeQuote.feeTon.toFixed(4)} TON
                      </span>
                    </div>
                    <div className="flex items-center justify-between gap-2 border-t border-white/10 pt-2.5">
                      <span className="font-semibold text-zinc-300">К получению</span>
                      <span className="font-mono-num text-sm font-bold text-emerald-400">
                        +{tradeQuote.netTon.toFixed(4)} TON
                      </span>
                    </div>
                  </>
                )}
              </div>

              <div className="mt-5 grid grid-cols-2 gap-2.5">
                <button
                  type="button"
                  disabled={tradeBusy}
                  onClick={() => setConfirmOpen(false)}
                  className="h-12 rounded-2xl border border-white/15 bg-zinc-950 text-xs font-bold text-zinc-300"
                >
                  Отмена
                </button>
                <button
                  type="button"
                  disabled={tradeBusy}
                  onClick={handleConfirmTrade}
                  className="flex h-12 items-center justify-center gap-1.5 rounded-2xl bg-white text-xs font-bold text-black active:scale-[0.98] disabled:opacity-40"
                >
                  <CheckCircle2 className="h-4 w-4" />
                  <span>{tradeBusy ? 'Исполняем...' : 'Подтвердить'}</span>
                </button>
              </div>
            </div>
          </div>
        )}
        {/* Transfer Memecoin Modal */}
        {transferOpen && (
          <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/80 backdrop-blur-sm sm:items-center sm:p-4">
            <div className="w-full max-w-md rounded-t-3xl border border-white/15 bg-zinc-900 p-5 sm:rounded-3xl">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Send className="h-4 w-4 text-white" />
                  <h3 className="text-base font-bold text-white">Передать монету ${c.ticker}</h3>
                </div>
                <button
                  type="button"
                  onClick={() => setTransferOpen(false)}
                  className="flex h-9 w-9 items-center justify-center rounded-full bg-zinc-800 text-zinc-300"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              <div className="mt-4 space-y-3">
                <div className="flex items-center justify-between rounded-2xl border border-white/10 bg-zinc-950 px-3.5 py-2.5 text-xs">
                  <span className="text-zinc-400">Доступно у вас</span>
                  <span className="font-mono-num font-bold text-white">
                    {formatCompactNum(c.my_balance, 2)} ${c.ticker}
                  </span>
                </div>

                <div>
                  <label className="mb-1 block text-xs text-zinc-400">
                    Получатель (@username или Telegram ID)
                  </label>
                  <input
                    type="text"
                    value={transferRecipient}
                    onChange={(e) => setTransferRecipient(e.target.value)}
                    placeholder="@username или 123456789"
                    className="h-12 w-full rounded-2xl border border-white/10 bg-black px-3.5 text-sm text-white outline-none focus:border-white/40"
                  />
                </div>

                <div>
                  <label className="mb-1 block text-xs text-zinc-400">
                    Количество токенов (${c.ticker})
                  </label>
                  <input
                    type="number"
                    step="any"
                    min={0}
                    value={transferAmount}
                    onChange={(e) => setTransferAmount(e.target.value)}
                    placeholder={`Кол-во $${c.ticker}`}
                    className="h-12 w-full rounded-2xl border border-white/10 bg-black px-3.5 font-mono-num text-sm font-semibold text-white outline-none focus:border-white/40"
                  />
                  {c.my_balance > 0 && (
                    <div className="mt-2 grid grid-cols-4 gap-2">
                      {[0.25, 0.5, 0.75, 1].map((pct) => (
                        <button
                          key={pct}
                          type="button"
                          onClick={() =>
                            setTransferAmount(String(Number((c.my_balance * pct).toFixed(2))))
                          }
                          className="min-h-[34px] rounded-xl border border-white/10 bg-zinc-950 font-mono-num text-xs font-semibold text-zinc-300 active:scale-95"
                        >
                          {pct * 100}%
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {errorMsg && (
                <p className="mt-3 text-center text-xs text-rose-400">{errorMsg}</p>
              )}

              <div className="mt-5 grid grid-cols-2 gap-2.5">
                <button
                  type="button"
                  disabled={transferBusy}
                  onClick={() => setTransferOpen(false)}
                  className="h-12 rounded-2xl border border-white/15 bg-zinc-950 text-xs font-bold text-zinc-300"
                >
                  Отмена
                </button>
                <button
                  type="button"
                  disabled={
                    transferBusy ||
                    !transferRecipient.trim() ||
                    Number(transferAmount || 0) <= 0 ||
                    Number(transferAmount || 0) > c.my_balance + 1e-6
                  }
                  onClick={handleTransferCoin}
                  className="flex h-12 items-center justify-center gap-1.5 rounded-2xl bg-white text-xs font-bold text-black active:scale-[0.98] disabled:opacity-40"
                >
                  <Send className="h-3.5 w-3.5" />
                  <span>{transferBusy ? 'Переводим...' : 'Перевести'}</span>
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  // 2. Dedicated Swapper Page ("Обменник")
  if (subView === 'swapper') {
    const isStarsIn = swapDir === 'stars_to_ton';
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <button
            type="button"
            onClick={() => {
              setSubView('hub');
              setErrorMsg(null);
              setNoticeMsg(null);
            }}
            className="flex min-h-[42px] items-center gap-1.5 rounded-2xl border border-white/10 bg-zinc-900 px-3.5 text-xs font-semibold text-white"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>Назад к бирже</span>
          </button>
          <span className="rounded-2xl border border-white/10 bg-zinc-900 px-3 py-2 font-mono-num text-xs text-zinc-300">
            1 TON = {formatStars(catalog.ton_star_rate)} ⭐
          </span>
        </div>

        <section className="rounded-3xl border border-white/10 bg-zinc-900/90 p-5">
          <h2 className="text-lg font-bold tracking-tight text-white">Обменник</h2>
          <p className="mt-0.5 text-xs text-zinc-400">
            Мгновенная конвертация Stars ⭐ ↔ TON без проскальзывания
          </p>

          <div className="relative mt-4 space-y-2.5">
            {/* Pay Box */}
            <div className="rounded-3xl border border-white/10 bg-zinc-950 p-4">
              <div className="flex items-center justify-between text-xs text-zinc-400">
                <span>Вы отдаёте</span>
                <button
                  type="button"
                  onClick={() =>
                    setSwapAmt(
                      isStarsIn
                        ? String(user.balance_stars)
                        : String(Number(user.balance_tons.toFixed(4)))
                    )
                  }
                  className="font-mono-num text-zinc-300 underline decoration-zinc-600 underline-offset-2"
                >
                  Доступно:{' '}
                  {isStarsIn
                    ? `${formatCompactNum(user.balance_stars, 1)} ⭐`
                    : `${formatTon(user.balance_tons, 2)} TON`}
                </button>
              </div>
              <div className="mt-3 flex items-center justify-between gap-3">
                <input
                  type="number"
                  min={0}
                  step="any"
                  value={swapAmt}
                  onChange={(e) => setSwapAmt(e.target.value)}
                  className="w-full min-w-0 bg-transparent font-mono-num text-2xl font-bold text-white outline-none"
                />
                <span className="shrink-0 rounded-2xl border border-white/15 bg-zinc-900 px-3.5 py-2 text-xs font-bold text-white">
                  {isStarsIn ? '⭐ Stars' : 'TON'}
                </span>
              </div>
              <div className="mt-3 flex gap-1.5">
                {(isStarsIn ? [1000, 10000, 100000, 1000000] : [1, 10, 100, 1000]).map((v) => (
                  <button
                    key={v}
                    type="button"
                    onClick={() => setSwapAmt(String(v))}
                    className="min-h-[32px] flex-1 rounded-xl border border-white/10 bg-zinc-900 font-mono-num text-[11px] font-semibold text-zinc-300"
                  >
                    {formatCompactNum(v, 0)}
                  </button>
                ))}
              </div>
            </div>

            {/* Center Flip Button */}
            <div className="flex justify-center -my-1 relative z-10">
              <button
                type="button"
                onClick={handleFlipSwap}
                aria-label="Поменять направление"
                className="flex h-11 w-11 items-center justify-center rounded-full border-2 border-zinc-900 bg-white text-black shadow-lg transition-transform active:rotate-180"
              >
                <ArrowUpDown className="h-4 w-4" />
              </button>
            </div>

            {/* Receive Box */}
            <div className="rounded-3xl border border-white/10 bg-zinc-950 p-4">
              <div className="flex items-center justify-between text-xs text-zinc-400">
                <span>Вы получаете</span>
                <span className="font-mono-num">
                  Баланс:{' '}
                  {isStarsIn
                    ? `${formatTon(user.balance_tons, 2)} TON`
                    : `${formatCompactNum(user.balance_stars, 1)} ⭐`}
                </span>
              </div>
              <div className="mt-3 flex items-center justify-between gap-3">
                <span className="truncate font-mono-num text-2xl font-bold text-white">
                  {isStarsIn
                    ? formatTon(swapReceiveAmount, 4)
                    : formatStars(swapReceiveAmount)}
                </span>
                <span className="shrink-0 rounded-2xl border border-white/15 bg-zinc-900 px-3.5 py-2 text-xs font-bold text-white">
                  {isStarsIn ? 'TON' : '⭐ Stars'}
                </span>
              </div>
            </div>
          </div>

          {noticeMsg && (
            <div className="mt-4 rounded-2xl border border-white/20 bg-zinc-950 p-3 text-center text-xs font-medium text-white">
              {noticeMsg}
            </div>
          )}
          {errorMsg && (
            <div className="mt-4 rounded-2xl border border-rose-500/30 bg-rose-950/30 p-3 text-center text-xs text-rose-300">
              {errorMsg}
            </div>
          )}

          <button
            type="button"
            disabled={swapBusy || swapNumeric <= 0}
            onClick={handleSwap}
            className="mt-4 h-12 w-full rounded-2xl bg-white text-sm font-bold text-black transition-transform active:scale-[0.98] disabled:opacity-40"
          >
            {swapBusy
              ? 'Выполняем обмен...'
              : isStarsIn
              ? `Обменять на ${formatTon(swapReceiveAmount, 4)} TON`
              : `Обменять на ${formatStars(swapReceiveAmount)} ⭐`}
          </button>
        </section>
      </div>
    );
  }

  // 3. Exchange Hub View
  return (
    <div className="space-y-4">
      <section className="rounded-3xl border border-white/10 bg-zinc-900/90 p-4 sm:p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="min-w-0">
            <h2 className="text-lg font-bold tracking-tight text-white">Криптобиржа</h2>
            <p className="text-xs text-zinc-400">
              Курс: 1 TON = {formatStars(catalog.ton_star_rate)} ⭐
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => {
                setErrorMsg(null);
                setNoticeMsg(null);
                setSubView('swapper');
              }}
              className="flex min-h-[42px] items-center gap-1.5 rounded-2xl border border-white/15 bg-zinc-950 px-3.5 text-xs font-bold text-white transition-transform active:scale-95"
            >
              <ArrowRightLeft className="h-4 w-4" />
              <span>Обменник</span>
            </button>
            <button
              type="button"
              onClick={() => {
                setErrorMsg(null);
                setCreateOpen(true);
              }}
              className="flex min-h-[42px] items-center gap-1.5 rounded-2xl bg-white px-3.5 text-xs font-bold text-black transition-transform active:scale-95"
            >
              <Plus className="h-4 w-4" />
              <span>Создать</span>
            </button>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-2.5">
          <div className="min-w-0 rounded-2xl border border-white/10 bg-zinc-950 p-3">
            <p className="text-[10px] uppercase tracking-wider text-zinc-500">Баланс TON</p>
            <p className="mt-1 truncate font-mono-num text-sm font-bold text-white">
              {formatTon(user.balance_tons, 2)} TON
            </p>
          </div>
          <div className="min-w-0 rounded-2xl border border-white/10 bg-zinc-950 p-3">
            <p className="text-[10px] uppercase tracking-wider text-zinc-500">Баланс Stars</p>
            <p className="mt-1 truncate font-mono-num text-sm font-bold text-white">
              {formatCompactNum(user.balance_stars, 1)} ⭐
            </p>
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

      {/* Coins List */}
      <section className="rounded-3xl border border-white/10 bg-zinc-900/80 p-4">
        <div className="mb-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Coins className="h-4 w-4 text-zinc-300" />
            <h3 className="text-sm font-semibold text-white">Мемкоины рынка</h3>
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
                className="flex w-full items-center justify-between gap-3 rounded-2xl border border-white/10 bg-zinc-950 p-3.5 text-left transition-colors hover:border-white/25 active:scale-[0.99]"
              >
                <div className="flex min-w-0 flex-1 items-center gap-3">
                  <img
                    src={resolveAssetUrl(c.image_url)}
                    alt={c.name}
                    className="h-11 w-11 shrink-0 rounded-2xl border border-white/10 bg-black object-cover"
                  />
                  <div className="min-w-0">
                    <p className="truncate text-sm font-bold text-white">{c.name}</p>
                    <p className="mt-0.5 truncate font-mono-num text-[11px] text-zinc-400">
                      ${c.ticker} · MCap {formatCompactNum(c.market_cap_ton, 1)} TON
                    </p>
                  </div>
                </div>
                <div className="shrink-0 text-right font-mono-num">
                  <p className="text-xs font-bold text-white">
                    {formatTokenPrice(c.price_ton)} TON
                  </p>
                  <p className="text-[10px] text-zinc-500">
                    1 ток. ≈ {formatStarEquivalent(c.price_stars)} ⭐
                  </p>
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
                <span
                  className={
                    user.level > catalog.memecoin_min_level
                      ? 'font-bold text-white'
                      : 'text-rose-400'
                  }
                >
                  Ваш: {user.level}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-zinc-400">Стоимость (пул 20k TON)</span>
                <span
                  className={
                    user.balance_tons >= catalog.memecoin_create_ton_cost
                      ? 'font-bold text-white'
                      : 'text-rose-400'
                  }
                >
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
              {createBusy
                ? 'Выпуск монеты...'
                : `Выпустить за ${formatTon(catalog.memecoin_create_ton_cost, 0)} TON`}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
