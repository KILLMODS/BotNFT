import { Star, Diamond, Sparkles, Layers } from 'lucide-react';
import { formatStars, formatTon, resolveAssetUrl } from '../api';
import type { CollectionItem, UserProfile } from '../types';

interface ProfileViewProps {
  user: UserProfile;
  collection: CollectionItem[];
  onGoUpgrader: () => void;
  onGoExchange: () => void;
}

export function ProfileView({ user, collection, onGoUpgrader, onGoExchange }: ProfileViewProps) {
  const totalInvStars = collection.reduce((sum, item) => sum + (item.display_stars || 0), 0);

  return (
    <div className="space-y-3.5">
      {/* Identity Glass Card */}
      <section className="glass-surface rounded-[28px] p-5">
        <div className="flex items-center gap-4">
          <img
            src={resolveAssetUrl(user.avatar_url)}
            alt={user.first_name}
            className="h-16 w-16 shrink-0 rounded-full border border-white/20 bg-zinc-900 object-cover shadow-lg"
          />
          <div className="min-w-0 flex-1">
            <h2 className="truncate text-lg font-bold tracking-tight text-white">
              {user.first_name}
            </h2>
            <p className="mt-0.5 truncate text-xs text-zinc-400">
              {user.username ? `@${user.username} · ` : ''}
              <span className="font-mono-num text-zinc-300">ID {user.user_id}</span>
            </p>
            <div className="mt-3">
              <div className="mb-1.5 flex items-center justify-between text-[11px] font-medium text-zinc-400">
                <span>Уровень {user.level}</span>
                <span className="font-mono-num text-zinc-300">
                  {formatStars(user.xp_current)} / {formatStars(user.xp_required)} XP
                </span>
              </div>
              <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/12">
                <div
                  className="h-full rounded-full bg-white transition-all duration-300"
                  style={{ width: `${Math.max(4, Math.round(user.xp_ratio * 100))}%` }}
                />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Balances Glass Grid */}
      <section className="grid grid-cols-2 gap-3">
        <div className="glass-card rounded-[26px] p-4">
          <div className="flex items-center justify-between text-xs font-medium text-zinc-400">
            <span>Баланс Stars</span>
            <Star className="h-4 w-4 text-zinc-300" strokeWidth={1.75} />
          </div>
          <p className="mt-2 font-mono-num text-xl font-bold tracking-tight text-white">
            {formatStars(user.balance_stars)}
          </p>
          <p className="mt-1 text-[11px] text-zinc-500">Игровая валюта</p>
        </div>

        <button
          type="button"
          onClick={onGoExchange}
          className="glass-card rounded-[26px] p-4 text-left transition-all hover:border-white/25 active:scale-[0.985]"
        >
          <div className="flex items-center justify-between text-xs font-medium text-zinc-400">
            <span>Баланс TON</span>
            <Diamond className="h-4 w-4 text-zinc-300" strokeWidth={1.75} />
          </div>
          <p className="mt-2 font-mono-num text-xl font-bold tracking-tight text-white">
            {formatTon(user.balance_tons, 2)} TON
          </p>
          <p className="mt-1 text-[11px] text-zinc-400">Открыть криптобиржу →</p>
        </button>
      </section>

      {/* Inventory Glass Section */}
      <section className="glass-surface rounded-[28px] p-4">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2.5">
            <div className="glass-chip flex h-9 w-9 items-center justify-center rounded-2xl text-zinc-200">
              <Layers className="h-4 w-4" strokeWidth={1.8} />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-white">Инвентарь NFT</h3>
              <p className="font-mono-num text-xs text-zinc-400">
                {collection.length} / {user.max_inventory} · {formatStars(totalInvStars)} ⭐
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onGoUpgrader}
            className="min-h-[38px] rounded-2xl bg-white px-4 text-xs font-semibold text-black shadow-sm transition-transform active:scale-95"
          >
            Апгрейд
          </button>
        </div>

        {collection.length === 0 ? (
          <div className="glass-inset mt-4 rounded-2xl border-dashed p-6 text-center text-sm text-zinc-500">
            Коллекция пока пуста. Выбивайте подарки в боте или играйте в Ракетку и Мины.
          </div>
        ) : (
          <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            {collection.map((item) => {
              const bgStyle =
                item.is_upgraded && item.backdrop_center_hex && item.backdrop_edge_hex
                  ? {
                      background: `radial-gradient(circle at center, ${item.backdrop_center_hex}, ${item.backdrop_edge_hex})`,
                    }
                  : undefined;

              return (
                <div
                  key={item.id}
                  className="glass-card flex flex-col justify-between overflow-hidden rounded-[22px] p-2.5"
                >
                  <div
                    className="relative flex aspect-square items-center justify-center overflow-hidden rounded-[16px] bg-zinc-900/80"
                    style={bgStyle}
                  >
                    <img
                      src={resolveAssetUrl(item.image_url)}
                      alt={item.name}
                      loading="lazy"
                      className="h-20 w-20 object-contain drop-shadow-lg"
                    />
                    {item.is_upgraded && (
                      <span className="absolute top-2 left-2 rounded-lg border border-white/10 bg-black/65 px-1.5 py-0.5 font-mono-num text-[10px] font-semibold text-white backdrop-blur-md">
                        #{item.upgrade_num}
                      </span>
                    )}
                    {item.is_listed !== 0 && (
                      <span className="absolute right-2 bottom-2 rounded-lg border border-white/10 bg-black/75 px-1.5 py-0.5 text-[10px] font-medium text-zinc-200 backdrop-blur-md">
                        Занят
                      </span>
                    )}
                  </div>

                  <div className="mt-2 px-0.5">
                    <p className="truncate text-xs font-semibold text-white">
                      {item.model_name || item.name}
                    </p>
                    <div className="mt-1 flex items-center justify-between text-[11px] font-mono-num font-semibold text-zinc-300">
                      <span>{formatStars(item.display_stars)} ⭐</span>
                      {item.is_upgraded && <Sparkles className="h-3 w-3 text-zinc-400" />}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
