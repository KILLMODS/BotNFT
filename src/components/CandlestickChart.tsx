import { useMemo, useState } from 'react';
import type { CandleData } from '../types';

interface CandlestickChartProps {
  candles: CandleData[];
}

export function CandlestickChart({ candles }: CandlestickChartProps) {
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);

  const displayCandles = useMemo(() => {
    if (candles.length === 0) return [];
    return candles.slice(-48);
  }, [candles]);

  const { minPrice, maxPrice, maxVol } = useMemo(() => {
    if (displayCandles.length === 0) {
      return { minPrice: 0, maxPrice: 1, maxVol: 1 };
    }
    let minP = Infinity;
    let maxP = -Infinity;
    let maxV = 0;
    for (const c of displayCandles) {
      if (c.low < minP) minP = c.low;
      if (c.high > maxP) maxP = c.high;
      if (c.volume > maxV) maxV = c.volume;
    }
    const pad = Math.max((maxP - minP) * 0.14, maxP * 0.03, 0.00001);
    return {
      minPrice: Math.max(0, minP - pad),
      maxPrice: maxP + pad,
      maxVol: Math.max(1, maxV),
    };
  }, [displayCandles]);

  const width = 640;
  const height = 270;
  const padLeft = 10;
  const padRight = 72;
  const padTop = 18;
  const chartBottom = 212;
  const volBottom = 252;
  const plotW = width - padLeft - padRight;
  const plotH = chartBottom - padTop;

  const yForPrice = (p: number) => {
    const span = Math.max(1e-9, maxPrice - minPrice);
    return chartBottom - ((p - minPrice) / span) * plotH;
  };

  const activeCandle =
    hoverIdx !== null && displayCandles[hoverIdx]
      ? displayCandles[hoverIdx]
      : displayCandles[displayCandles.length - 1] || null;

  const stepW = displayCandles.length > 0 ? plotW / Math.max(displayCandles.length, 14) : 20;
  const bodyW = Math.max(4, Math.min(14, stepW * 0.62));

  const formatTime = (ts: number) => {
    const d = new Date(ts * 1000);
    return d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
  };

  const formatP = (p: number) => {
    if (p < 0.001) return p.toFixed(6);
    if (p < 1) return p.toFixed(4);
    return p.toFixed(2);
  };

  const priceLevels = [0, 0.25, 0.5, 0.75, 1].map((t) => minPrice + (maxPrice - minPrice) * t);

  return (
    <div className="rounded-3xl border border-white/10 bg-zinc-950 p-3.5">
      {activeCandle && (
        <div className="mb-2.5 flex flex-wrap items-center justify-between gap-2 px-1 text-[11px] font-mono-num text-zinc-400">
          <div className="flex flex-wrap items-center gap-2.5">
            <span>O <strong className="text-zinc-200">{formatP(activeCandle.open)}</strong></span>
            <span>H <strong className="text-zinc-200">{formatP(activeCandle.high)}</strong></span>
            <span>L <strong className="text-zinc-200">{formatP(activeCandle.low)}</strong></span>
            <span>C <strong className={activeCandle.close >= activeCandle.open ? 'text-emerald-400' : 'text-rose-400'}>{formatP(activeCandle.close)}</strong></span>
          </div>
          <span>Vol <strong className="text-zinc-200">{activeCandle.volume.toFixed(2)} TON</strong> · {formatTime(activeCandle.time)}</span>
        </div>
      )}

      <div className="relative w-full overflow-hidden rounded-2xl bg-black/70">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="h-56 w-full select-none touch-pan-y sm:h-64"
          onMouseLeave={() => setHoverIdx(null)}
        >
          {/* Horizontal Price Grid */}
          {priceLevels.map((lvl, i) => {
            const y = yForPrice(lvl);
            return (
              <g key={i}>
                <line
                  x1={padLeft}
                  y1={y}
                  x2={width - padRight}
                  y2={y}
                  stroke="rgba(255,255,255,0.06)"
                  strokeDasharray="3 4"
                />
                <text
                  x={width - padRight + 8}
                  y={y + 4}
                  fill="#71717a"
                  fontSize="10"
                  fontFamily="JetBrains Mono, monospace"
                >
                  {formatP(lvl)}
                </text>
              </g>
            );
          })}

          {/* Last Price Line */}
          {displayCandles.length > 0 && (() => {
            const last = displayCandles[displayCandles.length - 1];
            const y = yForPrice(last.close);
            const isUp = last.close >= last.open;
            return (
              <g>
                <line
                  x1={padLeft}
                  y1={y}
                  x2={width - padRight}
                  y2={y}
                  stroke={isUp ? 'rgba(52,211,153,0.45)' : 'rgba(251,113,133,0.45)'}
                  strokeDasharray="4 3"
                />
                <rect
                  x={width - padRight + 2}
                  y={y - 9}
                  width={padRight - 4}
                  height={18}
                  rx={6}
                  fill={isUp ? '#10b981' : '#f43f5e'}
                />
                <text
                  x={width - padRight + 6}
                  y={y + 3.5}
                  fill="#000000"
                  fontSize="10"
                  fontWeight="700"
                  fontFamily="JetBrains Mono, monospace"
                >
                  {formatP(last.close)}
                </text>
              </g>
            );
          })()}

          {/* Candlesticks & Volume */}
          {displayCandles.map((c, idx) => {
            const cx = padLeft + idx * stepW + stepW / 2;
            const yHigh = yForPrice(c.high);
            const yLow = yForPrice(c.low);
            const yOpen = yForPrice(c.open);
            const yClose = yForPrice(c.close);
            const isUp = c.close >= c.open;
            const color = isUp ? '#22c55e' : '#ef4444';
            const bodyTop = Math.min(yOpen, yClose);
            const bodyH = Math.max(2.5, Math.abs(yClose - yOpen));
            const volH = Math.max(2, (c.volume / maxVol) * (volBottom - chartBottom - 6));
            const isHovered = hoverIdx === idx;

            return (
              <g
                key={c.time}
                onMouseEnter={() => setHoverIdx(idx)}
                onTouchStart={() => setHoverIdx(idx)}
                className="cursor-crosshair"
              >
                {isHovered && (
                  <line
                    x1={cx}
                    y1={padTop}
                    x2={cx}
                    y2={volBottom}
                    stroke="rgba(255,255,255,0.22)"
                    strokeWidth="1"
                  />
                )}
                {/* Invisible wider hit target */}
                <rect
                  x={cx - stepW / 2}
                  y={padTop}
                  width={stepW}
                  height={volBottom - padTop}
                  fill="transparent"
                />
                {/* Wick */}
                <line x1={cx} y1={yHigh} x2={cx} y2={yLow} stroke={color} strokeWidth="1.5" />
                {/* Candle Body */}
                <rect
                  x={cx - bodyW / 2}
                  y={bodyTop}
                  width={bodyW}
                  height={bodyH}
                  rx={1.5}
                  fill={color}
                />
                {/* Volume Bar */}
                <rect
                  x={cx - bodyW / 2}
                  y={volBottom - volH}
                  width={bodyW}
                  height={volH}
                  rx={1}
                  fill={color}
                  fillOpacity={0.28}
                />
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
}
