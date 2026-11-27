import { useMemo, useState, type PointerEvent } from 'react';
import type { CandleData } from '../types';

interface CandlestickChartProps {
  candles: CandleData[];
}

export function CandlestickChart({ candles }: CandlestickChartProps) {
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);

  const displayCandles = useMemo(() => {
    if (candles.length === 0) return [];
    return candles.slice(-34);
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
    const baseRange = Math.max(maxP - minP, maxP * 0.06, 0.00001);
    const pad = baseRange * 0.14;
    return {
      minPrice: Math.max(0, minP - pad),
      maxPrice: maxP + pad,
      maxVol: Math.max(1, maxV),
    };
  }, [displayCandles]);

  const width = 680;
  const height = 310;
  const padLeft = 10;
  const padRight = 76;
  const padTop = 16;
  const chartBottom = 242;
  const volBottom = 290;
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

  const slots = Math.max(displayCandles.length, 10);
  const stepW = plotW / slots;
  const bodyW = Math.max(4, Math.min(18, stepW * 0.62));

  const formatTime = (ts: number) => {
    const d = new Date(ts * 1000);
    return d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
  };

  const formatP = (p: number) => {
    if (p < 0.0001) return p.toFixed(7);
    if (p < 0.01) return p.toFixed(6);
    if (p < 1) return p.toFixed(4);
    return p.toFixed(2);
  };

  const priceLevels = [0, 0.25, 0.5, 0.75, 1].map((t) => minPrice + (maxPrice - minPrice) * t);

  const handlePointerInspect = (e: PointerEvent<SVGSVGElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    if (displayCandles.length === 0 || rect.width <= 0) return;
    const svgX = ((e.clientX - rect.left) / rect.width) * width;
    const rel = Math.floor((svgX - padLeft) / stepW);
    if (rel >= 0 && rel < displayCandles.length) {
      setHoverIdx(rel);
    } else {
      setHoverIdx(null);
    }
  };

  return (
    <div className="glass-card rounded-[26px] p-3.5">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2 px-1">
        {activeCandle ? (
          <div className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1 font-mono-num text-[11px] text-zinc-400">
            <span>O <strong className="text-zinc-200">{formatP(activeCandle.open)}</strong></span>
            <span>H <strong className="text-zinc-200">{formatP(activeCandle.high)}</strong></span>
            <span>L <strong className="text-zinc-200">{formatP(activeCandle.low)}</strong></span>
            <span>
              C{' '}
              <strong className={activeCandle.close >= activeCandle.open ? 'text-emerald-400' : 'text-rose-400'}>
                {formatP(activeCandle.close)}
              </strong>
            </span>
            <span className="text-zinc-500">
              {formatTime(activeCandle.time)} · {activeCandle.volume.toFixed(1)} TON
            </span>
          </div>
        ) : (
          <span className="text-xs text-zinc-500">Нет данных</span>
        )}
      </div>

      <div className="glass-inset relative w-full overflow-hidden rounded-2xl">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="h-64 w-full select-none sm:h-72"
          onPointerMove={handlePointerInspect}
          onPointerDown={handlePointerInspect}
          onMouseLeave={() => setHoverIdx(null)}
        >
          <defs>
            <clipPath id="candle-plot-clip">
              <rect x={padLeft} y={padTop} width={plotW} height={volBottom - padTop} />
            </clipPath>
          </defs>

          {priceLevels.map((lvl, i) => {
            const y = yForPrice(lvl);
            return (
              <g key={i}>
                <line
                  x1={padLeft}
                  y1={y}
                  x2={width - padRight}
                  y2={y}
                  stroke="rgba(255,255,255,0.055)"
                  strokeDasharray="3 4"
                />
                <text
                  x={width - padRight + 6}
                  y={y + 3.5}
                  fill="#71717a"
                  fontSize="10"
                  fontFamily="JetBrains Mono, monospace"
                >
                  {formatP(lvl)}
                </text>
              </g>
            );
          })}

          <g clipPath="url(#candle-plot-clip)">
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
                <g key={c.time}>
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
                  <line x1={cx} y1={yHigh} x2={cx} y2={yLow} stroke={color} strokeWidth="1.6" />
                  <rect
                    x={cx - bodyW / 2}
                    y={bodyTop}
                    width={bodyW}
                    height={bodyH}
                    rx={1.5}
                    fill={color}
                  />
                  <rect
                    x={cx - bodyW / 2}
                    y={volBottom - volH}
                    width={bodyW}
                    height={volH}
                    rx={1}
                    fill={color}
                    fillOpacity={0.26}
                  />
                </g>
              );
            })}

            {displayCandles.length > 0 && (() => {
              const last = displayCandles[displayCandles.length - 1];
              const y = yForPrice(last.close);
              const isUp = last.close >= last.open;
              return (
                <line
                  x1={padLeft}
                  y1={y}
                  x2={width - padRight}
                  y2={y}
                  stroke={isUp ? 'rgba(52,211,153,0.45)' : 'rgba(251,113,133,0.45)'}
                  strokeDasharray="4 3"
                />
              );
            })()}
          </g>

          {displayCandles.length > 0 && (() => {
            const last = displayCandles[displayCandles.length - 1];
            const y = Math.max(padTop + 10, Math.min(chartBottom - 10, yForPrice(last.close)));
            const isUp = last.close >= last.open;
            return (
              <g>
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
                  fontSize="9.5"
                  fontWeight="700"
                  fontFamily="JetBrains Mono, monospace"
                >
                  {formatP(last.close)}
                </text>
              </g>
            );
          })()}

          {displayCandles.length > 1 && [0, Math.floor(displayCandles.length / 2), displayCandles.length - 1].map((idx) => {
            const c = displayCandles[idx];
            if (!c) return null;
            const cx = padLeft + idx * stepW + stepW / 2;
            return (
              <text
                key={`t-${idx}`}
                x={cx}
                y={height - 6}
                textAnchor={idx === 0 ? 'start' : idx === displayCandles.length - 1 ? 'end' : 'middle'}
                fill="#52525b"
                fontSize="10"
                fontFamily="JetBrains Mono, monospace"
              >
                {formatTime(c.time)}
              </text>
            );
          })}
        </svg>
      </div>
    </div>
  );
}
