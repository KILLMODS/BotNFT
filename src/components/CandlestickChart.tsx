import { useMemo, useRef, useState, type PointerEvent, type WheelEvent } from 'react';
import { RotateCcw, ZoomIn, ZoomOut } from 'lucide-react';
import type { CandleData } from '../types';

interface CandlestickChartProps {
  candles: CandleData[];
}

export function CandlestickChart({ candles }: CandlestickChartProps) {
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);
  const [visibleCount, setVisibleCount] = useState<number>(36);
  const [panRightOffset, setPanRightOffset] = useState<number>(0); // how many candles back from end
  const [panYOffsetRatio, setPanYOffsetRatio] = useState<number>(0); // vertical price pan ratio

  const dragRef = useRef<{
    active: boolean;
    startX: number;
    startY: number;
    startRight: number;
    startYRatio: number;
    moved: boolean;
  }>({
    active: false,
    startX: 0,
    startY: 0,
    startRight: 0,
    startYRatio: 0,
    moved: false,
  });

  const maxRightOffset = Math.max(0, candles.length - Math.min(candles.length, 6));
  const clampedRightOffset = Math.max(0, Math.min(panRightOffset, maxRightOffset));

  const displayCandles = useMemo(() => {
    if (candles.length === 0) return [];
    const end = Math.max(1, candles.length - Math.round(clampedRightOffset));
    const start = Math.max(0, end - visibleCount);
    return candles.slice(start, end);
  }, [candles, visibleCount, clampedRightOffset]);

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
    const pad = baseRange * 0.16;
    const rawMin = Math.max(0, minP - pad);
    const rawMax = maxP + pad;
    const span = Math.max(1e-9, rawMax - rawMin);
    const shift = panYOffsetRatio * span;
    const shiftedMin = Math.max(0, rawMin + shift);
    return {
      minPrice: shiftedMin,
      maxPrice: Math.max(shiftedMin + span, rawMax + shift),
      maxVol: Math.max(1, maxV),
    };
  }, [displayCandles, panYOffsetRatio]);

  const width = 680;
  const height = 340;
  const padLeft = 10;
  const padRight = 76;
  const padTop = 18;
  const chartBottom = 266;
  const volBottom = 316;
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
  const bodyW = Math.max(4, Math.min(18, stepW * 0.64));

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

  const isModified =
    clampedRightOffset > 0.5 || Math.abs(panYOffsetRatio) > 0.02 || visibleCount !== 36;

  const handleReset = () => {
    setPanRightOffset(0);
    setPanYOffsetRatio(0);
    setVisibleCount(36);
  };

  const handlePointerDown = (e: PointerEvent<SVGSVGElement>) => {
    e.currentTarget.setPointerCapture(e.pointerId);
    dragRef.current = {
      active: true,
      startX: e.clientX,
      startY: e.clientY,
      startRight: clampedRightOffset,
      startYRatio: panYOffsetRatio,
      moved: false,
    };
  };

  const handlePointerMove = (e: PointerEvent<SVGSVGElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    if (dragRef.current.active) {
      const dx = e.clientX - dragRef.current.startX;
      const dy = e.clientY - dragRef.current.startY;
      if (Math.abs(dx) > 3 || Math.abs(dy) > 3) {
        dragRef.current.moved = true;
      }
      const pxPerCandle = Math.max(6, (rect.width * (plotW / width)) / slots);
      const nextRight = Math.max(
        0,
        Math.min(maxRightOffset, dragRef.current.startRight + dx / pxPerCandle)
      );
      const plotPxH = Math.max(80, rect.height * (plotH / height));
      const nextY = Math.max(-1.5, Math.min(1.5, dragRef.current.startYRatio + dy / plotPxH));
      setPanRightOffset(nextRight);
      setPanYOffsetRatio(nextY);
      return;
    }

    if (displayCandles.length > 0 && rect.width > 0) {
      const svgX = ((e.clientX - rect.left) / rect.width) * width;
      const rel = Math.floor((svgX - padLeft) / stepW);
      if (rel >= 0 && rel < displayCandles.length) {
        setHoverIdx(rel);
      } else {
        setHoverIdx(null);
      }
    }
  };

  const handlePointerUp = (e: PointerEvent<SVGSVGElement>) => {
    if (dragRef.current.active) {
      try {
        e.currentTarget.releasePointerCapture(e.pointerId);
      } catch {
        // Ignore if capture already released
      }
      if (!dragRef.current.moved) {
        const rect = e.currentTarget.getBoundingClientRect();
        const svgX = ((e.clientX - rect.left) / rect.width) * width;
        const rel = Math.floor((svgX - padLeft) / stepW);
        if (rel >= 0 && rel < displayCandles.length) {
          setHoverIdx(rel);
        }
      }
      dragRef.current.active = false;
    }
  };

  const handleWheel = (e: WheelEvent<SVGSVGElement>) => {
    if (Math.abs(e.deltaY) > Math.abs(e.deltaX)) {
      const step = e.deltaY > 0 ? 4 : -4;
      setVisibleCount((v) => Math.max(10, Math.min(120, v + step)));
    } else if (Math.abs(e.deltaX) > 0) {
      setPanRightOffset((r) => Math.max(0, Math.min(maxRightOffset, r - e.deltaX / 24)));
    }
  };

  return (
    <div className="rounded-3xl border border-white/10 bg-zinc-950 p-3.5">
      <div className="mb-2.5 flex flex-wrap items-center justify-between gap-2 px-1">
        {activeCandle ? (
          <div className="flex min-w-0 flex-wrap items-center gap-x-2.5 gap-y-1 text-[11px] font-mono-num text-zinc-400">
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

        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={() => setVisibleCount((v) => Math.max(10, v - 6))}
            title="Приблизить"
            className="flex h-8 w-8 items-center justify-center rounded-xl border border-white/10 bg-zinc-900 text-zinc-200 active:scale-95"
          >
            <ZoomIn className="h-3.5 w-3.5" />
          </button>
          <button
            type="button"
            onClick={() => setVisibleCount((v) => Math.min(120, v + 6))}
            title="Отдалить"
            className="flex h-8 w-8 items-center justify-center rounded-xl border border-white/10 bg-zinc-900 text-zinc-200 active:scale-95"
          >
            <ZoomOut className="h-3.5 w-3.5" />
          </button>
          {isModified && (
            <button
              type="button"
              onClick={handleReset}
              className="flex h-8 items-center gap-1 rounded-xl border border-white/15 bg-white px-2.5 text-[11px] font-bold text-black active:scale-95"
            >
              <RotateCcw className="h-3 w-3" />
              <span>Сброс</span>
            </button>
          )}
        </div>
      </div>

      <div className="relative w-full overflow-hidden rounded-2xl border border-white/5 bg-black/80">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="h-72 w-full cursor-grab select-none touch-none active:cursor-grabbing sm:h-80"
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerCancel={handlePointerUp}
          onWheel={handleWheel}
          onMouseLeave={() => {
            if (!dragRef.current.active) setHoverIdx(null);
          }}
        >
          <defs>
            <clipPath id="candle-plot-clip">
              <rect x={padLeft} y={padTop} width={plotW} height={volBottom - padTop} />
            </clipPath>
          </defs>

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

          {/* Clipped Plot Contents */}
          <g clipPath="url(#candle-plot-clip)">
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
                    fillOpacity={0.28}
                  />
                </g>
              );
            })}

            {/* Last Price Dotted Line */}
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
                  stroke={isUp ? 'rgba(52,211,153,0.5)' : 'rgba(251,113,133,0.5)'}
                  strokeDasharray="4 3"
                />
              );
            })()}
          </g>

          {/* Last Price Tag on Axis */}
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

          {/* Bottom Time Labels */}
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
      <p className="mt-2 text-center text-[10px] text-zinc-500">
        Тяните график пальцем или мышью в любую сторону для перемещения
      </p>
    </div>
  );
}
