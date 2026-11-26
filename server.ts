import 'dotenv/config';
import express from 'express';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { WebSocketServer, WebSocket } from 'ws';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const IMAGES_DIR = path.resolve(__dirname, 'Lol-main', 'images');
const PORT = Number(process.env.PORT || 3000);

const TON_STAR_RATE = 1000;
const MEMECOIN_MIN_LEVEL = 30;
const MEMECOIN_CREATE_TON_COST = 20000;
const UPGRADER_CHANCE_FACTOR = 0.78;
const ROCKET_UPGRADE_MULT_PENALTY = 1.28;

interface ModelDef {
  name: string;
  filename: string;
  chance_pct: number;
  price_mult: number;
  image_url: string;
}

interface BackdropDef {
  key: string;
  name: string;
  palette: string;
  center_hex: string;
  edge_hex: string;
  price_mult: number;
  rarity_label: string;
}

interface GiftCatalogItem {
  key: string;
  title: string;
  name: string;
  base_stars: number;
  upgrade_cost: number;
  image_url: string;
}

interface CollectionItem {
  id: number;
  gift_key: string;
  name: string;
  base_stars: number;
  display_stars: number;
  is_upgraded: boolean;
  model_name: string | null;
  backdrop_key: string | null;
  backdrop_name: string | null;
  backdrop_center_hex: string | null;
  backdrop_edge_hex: string | null;
  upgrade_num: number;
  is_listed: number;
  is_favorite: boolean;
  image_url: string;
  base_image_url: string;
  buff_backdrop_pct: number;
  buff_model_pct: number;
  buff_value_pct: number;
}

interface UserState {
  user_id: number;
  id_num: number;
  username: string;
  first_name: string;
  avatar_url: string;
  balance_stars: number;
  balance_tons: number;
  xp: number;
  max_inventory: number;
  collection: CollectionItem[];
}

interface Candle {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface Trade {
  id: number;
  user_id: number;
  side: 'buy' | 'sell';
  ton_amount: number;
  token_amount: number;
  price_ton: number;
  created_ts: number;
}

interface Memecoin {
  id: number;
  creator_id: number;
  name: string;
  ticker: string;
  image_url: string;
  reserve_ton: number;
  reserve_token: number;
  total_supply: number;
  price_ton: number;
  market_cap_ton: number;
  volume_24h_ton: number;
  holders_count: number;
  created_ts: number;
  candles: Candle[];
  trades: Trade[];
  holdings: Map<number, number>;
}

const UPGRADABLE_GIFTS: GiftCatalogItem[] = [
  { key: 'pepe_heart', title: 'Plush Pepe', name: 'Plush Pepe (Пепе с сердцем)', base_stars: 480000, upgrade_cost: 300000, image_url: '/api/assets/gift/pepe_heart' },
  { key: 'heart_lock_key', title: 'Heart Locket', name: 'Heart Locket (Сердце-замок)', base_stars: 22000, upgrade_cost: 200000, image_url: '/api/assets/gift/heart_lock_key' },
  { key: 'cap_tg', title: "Durov's Cap", name: "Durov's Cap (Кепка Дурова)", base_stars: 38000, upgrade_cost: 150000, image_url: '/api/assets/gift/cap_tg' },
  { key: 'trophy_cup', title: 'Algorithm Cup', name: 'Algorithm Cup (Кубок Чемпиона)', base_stars: 85000, upgrade_cost: 200000, image_url: '/api/assets/gift/trophy_cup' },
  { key: 'bonded_ring', title: 'Bonded Ring', name: 'Bonded Ring (Кольцо)', base_stars: 40000, upgrade_cost: 150000, image_url: '/api/assets/gift/bonded_ring' },
];

const BACKDROPS: BackdropDef[] = [
  { key: 'black', name: 'Black', palette: 'Глубокий чёрный', center_hex: '#363738', edge_hex: '#0E0F0F', price_mult: 10.5, rarity_label: 'Ультра-редкий' },
  { key: 'onyx_black', name: 'Onyx Black', palette: 'Ониксовый чёрный', center_hex: '#4D5254', edge_hex: '#313638', price_mult: 9.5, rarity_label: 'Ультра-редкий' },
  { key: 'steel_grey', name: 'Steel Grey', palette: 'Холодный серый', center_hex: '#97A2AC', edge_hex: '#63727C', price_mult: 8.4, rarity_label: 'Ультра-редкий' },
  { key: 'platinum', name: 'Platinum', palette: 'Платиновый серый', center_hex: '#B2AEA7', edge_hex: '#88847E', price_mult: 7.2, rarity_label: 'Ультра-редкий' },
  { key: 'ivory_white', name: 'Ivory White', palette: 'Слоновая кость', center_hex: '#BAB6B1', edge_hex: '#A19D97', price_mult: 6.8, rarity_label: 'Ультра-редкий' },
  { key: 'pure_gold', name: 'Pure Gold', palette: 'Чистое золото', center_hex: '#CCAB41', edge_hex: '#987B32', price_mult: 8.2, rarity_label: 'Ультра-редкий' },
  { key: 'midnight_blue', name: 'Midnight Blue', palette: 'Полуночный синий', center_hex: '#5C6985', edge_hex: '#354057', price_mult: 5.8, rarity_label: 'Редкий' },
  { key: 'silver_blue', name: 'Silver Blue', palette: 'Серебристо-синий', center_hex: '#80A4B8', edge_hex: '#607C91', price_mult: 4.3, rarity_label: 'Редкий' },
  { key: 'burgundy', name: 'Burgundy', palette: 'Благородный бордо', center_hex: '#A35E66', edge_hex: '#6D414A', price_mult: 5.2, rarity_label: 'Редкий' },
  { key: 'rainbow', name: 'Rainbow', palette: 'Переливающийся радужный', center_hex: '#FF4D8D', edge_hex: '#6366F1', price_mult: 100.0, rarity_label: 'Мифический' },
];

const MODEL_DIR_MAP: Record<string, string> = {
  pepe_heart: 'plushpepe_models',
  heart_lock_key: 'heart_locket_models',
  cap_tg: 'durov_cap_models',
  trophy_cup: 'cup_models',
  bonded_ring: 'bonded_ring_models',
};

function loadModelsForGift(giftKey: string): ModelDef[] {
  const dirName = MODEL_DIR_MAP[giftKey];
  if (!dirName) return [];
  const fullDir = path.resolve(IMAGES_DIR, dirName);
  if (!fs.existsSync(fullDir)) return [];
  const files = fs.readdirSync(fullDir).filter((f) => /\.(webp|png|jpe?g)$/i.test(f)).sort();
  return files.slice(0, 65).map((filename, idx) => {
    const cleanName = filename.replace(/\.(webp|png|jpe?g)$/i, '');
    const mult = Number((1.08 + ((idx % 7) * 0.04)).toFixed(2));
    return {
      name: cleanName,
      filename,
      chance_pct: Number(Math.max(0.8, 3.0 - (idx % 5) * 0.45).toFixed(2)),
      price_mult: mult,
      image_url: `/api/assets/model/${encodeURIComponent(giftKey)}/${encodeURIComponent(filename)}`,
    };
  });
}

const MODELS_BY_GIFT: Record<string, ModelDef[]> = {
  pepe_heart: loadModelsForGift('pepe_heart'),
  heart_lock_key: loadModelsForGift('heart_lock_key'),
  cap_tg: loadModelsForGift('cap_tg'),
  trophy_cup: loadModelsForGift('trophy_cup'),
  bonded_ring: loadModelsForGift('bonded_ring'),
};

function calculateXpLevelInfo(totalXp: number) {
  let level = 0;
  let cur = Math.max(0, totalXp);
  let req = 1000;
  while (cur >= req) {
    cur -= req;
    level += 1;
    req = Math.floor(req + 1500 + level * 500);
  }
  const ratio = req > 0 ? Math.min(1, Math.max(0, cur / req)) : 1;
  return { level, xp_current: cur, xp_required: req, xp_ratio: Number(ratio.toFixed(4)) };
}

function calcUpgradedStars(giftKey: string, model: ModelDef, backdrop: BackdropDef): number {
  const g = UPGRADABLE_GIFTS.find((x) => x.key === giftKey) || UPGRADABLE_GIFTS[0];
  const base = giftKey === 'pepe_heart' ? g.base_stars : g.base_stars + g.upgrade_cost;
  const raw = base * backdrop.price_mult * model.price_mult * 1.5;
  return Math.max(150000, Math.round(raw / 5000) * 5000);
}

let nextCollectionId = 100;
let nextUpgradeNum = 42;
let nextCoinId = 2;
let nextTradeId = 10;

const usersMap = new Map<number, UserState>();

function getOrCreatePreviewUser(uid: number, firstName = 'Collector', username = 'collector'): UserState {
  const existing = usersMap.get(uid);
  if (existing) return existing;
  const initial: UserState = {
    user_id: uid,
    id_num: 1,
    username,
    first_name: firstName,
    avatar_url: `/api/assets/avatar/${uid}`,
    balance_stars: 32500000,
    balance_tons: 24500,
    xp: 2150000,
    max_inventory: 35,
    collection: [
      {
        id: nextCollectionId++,
        gift_key: 'pepe_heart',
        name: 'Plush Pepe (Пепе с сердцем)',
        base_stars: 480000,
        display_stars: 480000,
        is_upgraded: false,
        model_name: null,
        backdrop_key: null,
        backdrop_name: null,
        backdrop_center_hex: null,
        backdrop_edge_hex: null,
        upgrade_num: 0,
        is_listed: 0,
        is_favorite: true,
        image_url: '/api/assets/gift/pepe_heart',
        base_image_url: '/api/assets/gift/pepe_heart',
        buff_backdrop_pct: 0,
        buff_model_pct: 0,
        buff_value_pct: 0,
      },
      {
        id: nextCollectionId++,
        gift_key: 'bonded_ring',
        name: 'Bonded Ring (Кольцо)',
        base_stars: 40000,
        display_stars: 40000,
        is_upgraded: false,
        model_name: null,
        backdrop_key: null,
        backdrop_name: null,
        backdrop_center_hex: null,
        backdrop_edge_hex: null,
        upgrade_num: 0,
        is_listed: 0,
        is_favorite: false,
        image_url: '/api/assets/gift/bonded_ring',
        base_image_url: '/api/assets/gift/bonded_ring',
        buff_backdrop_pct: 0,
        buff_model_pct: 0,
        buff_value_pct: 0,
      },
      {
        id: nextCollectionId++,
        gift_key: 'cap_tg',
        name: "Durov's Cap (Кепка Дурова)",
        base_stars: 38000,
        display_stars: 38000,
        is_upgraded: false,
        model_name: null,
        backdrop_key: null,
        backdrop_name: null,
        backdrop_center_hex: null,
        backdrop_edge_hex: null,
        upgrade_num: 0,
        is_listed: 0,
        is_favorite: false,
        image_url: '/api/assets/gift/cap_tg',
        base_image_url: '/api/assets/gift/cap_tg',
        buff_backdrop_pct: 0,
        buff_model_pct: 0,
        buff_value_pct: 0,
      },
      {
        id: nextCollectionId++,
        gift_key: 'heart_lock_key',
        name: 'Heart Locket (Сердце-замок)',
        base_stars: 22000,
        display_stars: 22000,
        is_upgraded: false,
        model_name: null,
        backdrop_key: null,
        backdrop_name: null,
        backdrop_center_hex: null,
        backdrop_edge_hex: null,
        upgrade_num: 0,
        is_listed: 0,
        is_favorite: false,
        image_url: '/api/assets/gift/heart_lock_key',
        base_image_url: '/api/assets/gift/heart_lock_key',
        buff_backdrop_pct: 0,
        buff_model_pct: 0,
        buff_value_pct: 0,
      },
      {
        id: nextCollectionId++,
        gift_key: 'trophy_cup',
        name: 'Algorithm Cup (Кубок Чемпиона)',
        base_stars: 85000,
        display_stars: 85000,
        is_upgraded: false,
        model_name: null,
        backdrop_key: null,
        backdrop_name: null,
        backdrop_center_hex: null,
        backdrop_edge_hex: null,
        upgrade_num: 0,
        is_listed: 0,
        is_favorite: false,
        image_url: '/api/assets/gift/trophy_cup',
        base_image_url: '/api/assets/gift/trophy_cup',
        buff_backdrop_pct: 0,
        buff_model_pct: 0,
        buff_value_pct: 0,
      },
    ],
  };
  usersMap.set(uid, initial);
  return initial;
}

function makeSeedCoin(): Memecoin {
  const nowSec = Math.floor(Date.now() / 1000);
  const bucket = nowSec - (nowSec % 60);
  const candles: Candle[] = [];
  let p = 0.00025;
  const deltas = [0.00002, -0.00001, 0.00003, 0.00001, -0.00002, 0.00004, -0.000015, 0.000035, 0.000025, -0.00001];
  for (let i = 0; i < deltas.length; i++) {
    const open = p;
    const close = Number(Math.max(0.00015, open + deltas[i]).toFixed(8));
    const high = Number((Math.max(open, close) * 1.04).toFixed(8));
    const low = Number((Math.min(open, close) * 0.96).toFixed(8));
    candles.push({
      time: bucket - (deltas.length - i) * 60,
      open,
      high,
      low,
      close,
      volume: Number((18 + i * 7.5).toFixed(2)),
    });
    p = close;
  }
  const resTon = 340.0;
  const resTok = resTon / p;
  return {
    id: 1,
    creator_id: 684535319,
    name: 'Pepe Gold',
    ticker: 'PEPEG',
    image_url: '/api/assets/gift/pepe_heart',
    reserve_ton: resTon,
    reserve_token: resTok,
    total_supply: 1000000,
    price_ton: p,
    market_cap_ton: Number((p * 1000000).toFixed(4)),
    volume_24h_ton: 425.5,
    holders_count: 14,
    created_ts: nowSec - 3600,
    candles,
    trades: [
      { id: 1, user_id: 684535319, side: 'buy', ton_amount: 45, token_amount: 128500, price_ton: p, created_ts: nowSec - 180 },
      { id: 2, user_id: 7459502130, side: 'buy', ton_amount: 22.5, token_amount: 64200, price_ton: Number((p * 0.96).toFixed(8)), created_ts: nowSec - 420 },
    ],
    holdings: new Map([[684535319, 128500]]),
  };
}

const memecoins = new Map<number, Memecoin>([[1, makeSeedCoin()]]);

function serializeUser(u: UserState) {
  const lv = calculateXpLevelInfo(u.xp);
  return {
    user_id: u.user_id,
    id_num: u.id_num,
    username: u.username,
    first_name: u.first_name,
    avatar_url: u.avatar_url,
    balance_stars: u.balance_stars,
    balance_tons: Number(u.balance_tons.toFixed(6)),
    xp: u.xp,
    level: lv.level,
    xp_current: lv.xp_current,
    xp_required: lv.xp_required,
    xp_ratio: lv.xp_ratio,
    max_inventory: u.max_inventory,
  };
}

function serializeCoinSummary(c: Memecoin, uid: number) {
  const firstOpen = c.candles[0]?.open || c.price_ton;
  const changePct = firstOpen > 0 ? Number((((c.price_ton - firstOpen) / firstOpen) * 100).toFixed(2)) : 0;
  return {
    id: c.id,
    creator_id: c.creator_id,
    name: c.name,
    ticker: c.ticker,
    image_url: c.image_url,
    reserve_ton: Number(c.reserve_ton.toFixed(6)),
    reserve_token: Number(c.reserve_token.toFixed(4)),
    total_supply: c.total_supply,
    price_ton: Number(c.price_ton.toFixed(8)),
    price_stars: Number((c.price_ton * TON_STAR_RATE).toFixed(4)),
    market_cap_ton: Number(c.market_cap_ton.toFixed(4)),
    volume_24h_ton: Number(c.volume_24h_ton.toFixed(4)),
    holders_count: c.holders_count,
    created_ts: c.created_ts,
    change_pct: changePct,
    my_balance: Number((c.holdings.get(uid) || 0).toFixed(4)),
  };
}

// Rocket Engine
interface RocketBet {
  user_id: number;
  name: string;
  avatar_url: string;
  stake_type: 'stars' | 'nft';
  stake_stars: number;
  collection_item_id?: number;
  item_name?: string;
  item_image_url?: string;
  target_gift_key?: string;
  target_gift_title?: string;
  target_model_name?: string;
  target_backdrop_key?: string;
  target_stars?: number;
  target_mult?: number;
  auto_cashout?: number | null;
  status: 'active' | 'won' | 'lost';
  cashout_mult: number | null;
  payout_stars: number;
}

const rocket = {
  phase: 'betting' as 'betting' | 'flying' | 'crashed',
  round_id: 1,
  countdown_sec: 9.0,
  multiplier: 1.0,
  crash_point: 2.15,
  started_ms: Date.now(),
  bets: new Map<number, RocketBet>(),
  history: [
    { round_id: 100, crash_point: 2.34 },
    { round_id: 99, crash_point: 1.18 },
    { round_id: 98, crash_point: 4.82 },
    { round_id: 97, crash_point: 1.0 },
    { round_id: 96, crash_point: 1.76 },
  ] as Array<{ round_id: number; crash_point: number }>,
};

function rollCrashPoint(): number {
  const r = Math.random();
  if (r < 0.08) return 1.0;
  return Number(Math.min(100, Math.max(1.01, 0.92 / Math.max(1e-6, 1 - r))).toFixed(2));
}

function getRocketPublicState() {
  return {
    phase: rocket.phase,
    round_id: rocket.round_id,
    countdown_sec: Number(Math.max(0, rocket.countdown_sec).toFixed(1)),
    multiplier: Number(rocket.multiplier.toFixed(2)),
    crash_point: rocket.phase === 'crashed' ? rocket.crash_point : null,
    bets: Array.from(rocket.bets.values()),
    history: rocket.history.slice(0, 16),
  };
}

const wsClients = new Set<WebSocket>();
function broadcastWS(type: string, data: unknown) {
  if (wsClients.size === 0) return;
  const msg = JSON.stringify({ type, data });
  for (const ws of wsClients) {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(msg);
    }
  }
}

function settleRocketBet(bet: RocketBet, mult: number) {
  const u = getOrCreatePreviewUser(bet.user_id);
  if (bet.stake_type === 'stars') {
    const payout = Math.round(bet.stake_stars * mult);
    u.balance_stars += payout;
    u.xp += 350;
    bet.status = 'won';
    bet.cashout_mult = Number(mult.toFixed(2));
    bet.payout_stars = payout;
    return { won: true, payout_stars: payout, upgraded: false };
  }
  const item = u.collection.find((x) => x.id === bet.collection_item_id);
  if (item) {
    item.is_listed = 0;
    if (mult >= (bet.target_mult || 999)) {
      const targetKey = bet.target_gift_key || 'pepe_heart';
      const targetGift = UPGRADABLE_GIFTS.find((g) => g.key === targetKey) || UPGRADABLE_GIFTS[0];
      const mdef = (MODELS_BY_GIFT[targetKey] || []).find((m) => m.name === bet.target_model_name) || MODELS_BY_GIFT[targetKey]?.[0];
      const bdef = BACKDROPS.find((b) => b.key === bet.target_backdrop_key) || BACKDROPS[0];
      item.gift_key = targetKey;
      item.name = targetGift.name;
      item.base_stars = targetGift.base_stars;
      item.is_upgraded = true;
      item.model_name = mdef?.name || 'Classic';
      item.backdrop_key = bdef.key;
      item.backdrop_name = bdef.name;
      item.backdrop_center_hex = bdef.center_hex;
      item.backdrop_edge_hex = bdef.edge_hex;
      item.display_stars = bet.target_stars || item.display_stars;
      item.upgrade_num = nextUpgradeNum++;
      item.image_url = mdef?.image_url || targetGift.image_url;
      item.base_image_url = targetGift.image_url;
      u.xp += 3500;
      bet.status = 'won';
      bet.cashout_mult = Number(mult.toFixed(2));
      bet.payout_stars = item.display_stars;
      return { won: true, payout_stars: item.display_stars, upgraded: true };
    }
    bet.status = 'won';
    bet.cashout_mult = Number(mult.toFixed(2));
    bet.payout_stars = item.display_stars;
    return { won: true, payout_stars: item.display_stars, upgraded: false };
  }
  return { won: false, payout_stars: 0, upgraded: false };
}

async function runRocketLoop() {
  while (true) {
    rocket.phase = 'betting';
    rocket.round_id += 1;
    rocket.countdown_sec = 9.0;
    rocket.multiplier = 1.0;
    rocket.crash_point = rollCrashPoint();
    rocket.bets.clear();

    for (let s = 0; s < 90; s++) {
      broadcastWS('rocket_state', getRocketPublicState());
      await new Promise((r) => setTimeout(r, 100));
      rocket.countdown_sec = Math.max(0, 9.0 - (s + 1) * 0.1);
    }

    rocket.phase = 'flying';
    rocket.started_ms = Date.now();
    rocket.multiplier = 1.0;
    broadcastWS('rocket_state', getRocketPublicState());

    while (true) {
      await new Promise((r) => setTimeout(r, 100));
      const elapsed = Math.max(0, (Date.now() - rocket.started_ms) / 1000);
      const nextMult = Number(Math.exp(0.075 * elapsed).toFixed(2));
      if (nextMult >= rocket.crash_point) {
        rocket.multiplier = rocket.crash_point;
        rocket.phase = 'crashed';
        for (const bet of rocket.bets.values()) {
          if (bet.status === 'active') {
            bet.status = 'lost';
            if (bet.stake_type === 'nft' && bet.collection_item_id) {
              const u = getOrCreatePreviewUser(bet.user_id);
              u.collection = u.collection.filter((it) => it.id !== bet.collection_item_id);
            }
          }
        }
        rocket.history.unshift({ round_id: rocket.round_id, crash_point: rocket.crash_point });
        rocket.history = rocket.history.slice(0, 20);
        broadcastWS('rocket_state', getRocketPublicState());
        break;
      } else {
        rocket.multiplier = nextMult;
        let stateChanged = false;
        for (const bet of rocket.bets.values()) {
          if (bet.status === 'active' && bet.auto_cashout && nextMult >= bet.auto_cashout) {
            settleRocketBet(bet, bet.auto_cashout);
            stateChanged = true;
          }
        }
        broadcastWS(stateChanged ? 'rocket_state' : 'rocket_tick', getRocketPublicState());
      }
    }

    await new Promise((r) => setTimeout(r, 3800));
  }
}

function resolveRequestUser(req: express.Request): UserState {
  const rawInit = String(req.header('X-Telegram-Init-Data') || '');
  if (rawInit) {
    try {
      const params = new URLSearchParams(rawInit);
      const userJson = params.get('user');
      if (userJson) {
        const parsed = JSON.parse(userJson);
        if (parsed?.id) {
          return getOrCreatePreviewUser(Number(parsed.id), parsed.first_name || 'Player', parsed.username || '');
        }
      }
    } catch {
      // Fallback to preview user below
    }
  }
  const devId = Number(req.header('X-Dev-User-Id') || 777001);
  return getOrCreatePreviewUser(Number.isFinite(devId) && devId > 0 ? devId : 777001, 'Demo Collector', 'new_nft_user');
}

function safeGiftAssetPath(key: string): string | null {
  const cleanKey = key === 'ring_silver' ? 'bonded_ring' : key.replace(/[^a-zA-Z0-9_ -]/g, '');
  const overrides: Record<string, string[]> = {
    trophy_cup: ['Algorithm Cup.webp', 'trophy_cup.webp'],
    bonded_ring: ['ring_silver.webp', 'bonded_ring.webp'],
    signet_ring: ['ring_signet_tg.webp', 'signet_ring.webp'],
    scared_cat: ['Scared Cat.webp', 'scared_cat.webp'],
  };
  const candidates = [
    ...(overrides[cleanKey] || []),
    `${cleanKey}.webp`,
    `${cleanKey}.png`,
    `${cleanKey}.jpg`,
  ];
  for (const name of candidates) {
    const resolved = path.resolve(IMAGES_DIR, name);
    if (resolved.startsWith(IMAGES_DIR) && fs.existsSync(resolved)) {
      return resolved;
    }
  }
  return null;
}

async function startServer() {
  const app = express();
  app.use(express.json({ limit: '2mb' }));

  app.get('/api/health', (_req, res) => {
    res.json({ ok: true, service: 'new-nft-miniapp-preview', port: PORT });
  });

  app.get('/api/me', (req, res) => {
    const u = resolveRequestUser(req);
    res.json({
      ok: true,
      user: serializeUser(u),
      collection: u.collection,
      catalog: {
        upgradable_gifts: UPGRADABLE_GIFTS,
        models_by_gift: MODELS_BY_GIFT,
        backdrops: BACKDROPS,
        ton_star_rate: TON_STAR_RATE,
        memecoin_min_level: MEMECOIN_MIN_LEVEL,
        memecoin_create_ton_cost: MEMECOIN_CREATE_TON_COST,
        upgrader_chance_factor: UPGRADER_CHANCE_FACTOR,
        rocket_upgrade_mult_penalty: ROCKET_UPGRADE_MULT_PENALTY,
      },
    });
  });

  app.post('/api/upgrade', (req, res) => {
    const u = resolveRequestUser(req);
    const sourceId = Number(req.body?.source_item_id || 0);
    const targetKey = String(req.body?.target_gift_key || 'pepe_heart');
    const targetModelName = req.body?.target_model_name ? String(req.body.target_model_name) : undefined;
    const targetBackdropKey = req.body?.target_backdrop_key ? String(req.body.target_backdrop_key) : undefined;

    const itemIdx = u.collection.findIndex((x) => x.id === sourceId);
    if (itemIdx === -1) return res.status(400).json({ ok: false, error: 'Предмет не найден в коллекции.' });
    const src = u.collection[itemIdx];
    if (src.is_listed !== 0) return res.status(400).json({ ok: false, error: 'Предмет сейчас занят.' });

    const targetGift = UPGRADABLE_GIFTS.find((g) => g.key === targetKey);
    if (!targetGift) return res.status(400).json({ ok: false, error: 'Недоступная цель для апгрейда.' });

    const mlist = MODELS_BY_GIFT[targetKey] || [];
    const modelDef = mlist.find((m) => m.name === targetModelName) || mlist[0] || { name: 'Classic', filename: '', chance_pct: 2, price_mult: 1.1, image_url: targetGift.image_url };
    const backdropDef = BACKDROPS.find((b) => b.key === targetBackdropKey) || BACKDROPS[BACKDROPS.length - 1];
    const targetStars = calcUpgradedStars(targetKey, modelDef, backdropDef);
    const chancePct = Number(Math.max(1, Math.min(72, (src.display_stars / Math.max(1, targetStars)) * 100 * UPGRADER_CHANCE_FACTOR)).toFixed(2));
    const roll = Number((Math.random() * 100).toFixed(2));
    const won = roll < chancePct;

    u.collection.splice(itemIdx, 1);
    let newItem: CollectionItem | null = null;
    if (won) {
      newItem = {
        id: nextCollectionId++,
        gift_key: targetKey,
        name: targetGift.name,
        base_stars: targetGift.base_stars,
        display_stars: targetStars,
        is_upgraded: true,
        model_name: modelDef.name,
        backdrop_key: backdropDef.key,
        backdrop_name: backdropDef.name,
        backdrop_center_hex: backdropDef.center_hex,
        backdrop_edge_hex: backdropDef.edge_hex,
        upgrade_num: nextUpgradeNum++,
        is_listed: 0,
        is_favorite: false,
        image_url: modelDef.image_url,
        base_image_url: targetGift.image_url,
        buff_backdrop_pct: 0,
        buff_model_pct: 0,
        buff_value_pct: 0,
      };
      u.collection.unshift(newItem);
      u.xp += 3500;
    } else {
      u.xp += 500;
    }

    res.json({
      ok: true,
      won,
      chance_pct: chancePct,
      roll,
      source_stars: src.display_stars,
      target_stars: targetStars,
      new_item: newItem,
      user: serializeUser(u),
      collection: u.collection,
    });
  });

  app.post('/api/exchange/swap', (req, res) => {
    const u = resolveRequestUser(req);
    const direction = String(req.body?.direction || 'stars_to_ton');
    const amount = Number(req.body?.amount || 0);
    if (!(amount > 0)) return res.status(400).json({ ok: false, error: 'Укажите сумму больше нуля.' });

    if (direction === 'stars_to_ton') {
      const starsIn = Math.round(amount);
      if (starsIn < 100) return res.status(400).json({ ok: false, error: 'Минимум для обмена — 100 ⭐.' });
      if (u.balance_stars < starsIn) return res.status(400).json({ ok: false, error: 'Недостаточно Stars на балансе.' });
      const tonsOut = Number((starsIn / TON_STAR_RATE).toFixed(6));
      u.balance_stars -= starsIn;
      u.balance_tons = Number((u.balance_tons + tonsOut).toFixed(6));
      return res.json({ ok: true, balance_stars: u.balance_stars, balance_tons: u.balance_tons, swapped_tons: tonsOut, swapped_stars: -starsIn });
    }

    if (direction === 'ton_to_stars') {
      const tonsIn = Number(amount.toFixed(6));
      if (tonsIn < 0.1) return res.status(400).json({ ok: false, error: 'Минимум для обмена — 0.1 TON.' });
      if (u.balance_tons + 1e-9 < tonsIn) return res.status(400).json({ ok: false, error: 'Недостаточно TON на балансе.' });
      const starsOut = Math.round(tonsIn * TON_STAR_RATE);
      u.balance_tons = Number(Math.max(0, u.balance_tons - tonsIn).toFixed(6));
      u.balance_stars += starsOut;
      return res.json({ ok: true, balance_stars: u.balance_stars, balance_tons: u.balance_tons, swapped_tons: -tonsIn, swapped_stars: starsOut });
    }

    return res.status(400).json({ ok: false, error: 'Неверное направление обмена.' });
  });

  app.get('/api/coins', (req, res) => {
    const u = resolveRequestUser(req);
    const coins = Array.from(memecoins.values())
      .map((c) => serializeCoinSummary(c, u.user_id))
      .sort((a, b) => b.market_cap_ton - a.market_cap_ton);
    res.json({ ok: true, coins });
  });

  app.get('/api/coins/:id', (req, res) => {
    const u = resolveRequestUser(req);
    const c = memecoins.get(Number(req.params.id));
    if (!c) return res.status(404).json({ ok: false, error: 'Монета не найдена.' });
    res.json({
      ok: true,
      coin: serializeCoinSummary(c, u.user_id),
      candles: c.candles.slice(-240),
      trades: c.trades.slice(0, 30),
    });
  });

  app.post('/api/coins/create', (req, res) => {
    const u = resolveRequestUser(req);
    const lv = calculateXpLevelInfo(u.xp).level;
    if (lv <= MEMECOIN_MIN_LEVEL) {
      return res.status(400).json({ ok: false, error: `Для создания мемкоина нужен уровень выше ${MEMECOIN_MIN_LEVEL} (ваш: ${lv}).` });
    }
    if (u.balance_tons + 1e-9 < MEMECOIN_CREATE_TON_COST) {
      return res.status(400).json({ ok: false, error: 'Недостаточно TON! Требуется 20,000 TON (20,000,000 ⭐).' });
    }
    const cleanName = String(req.body?.name || '').trim().replace(/\s+/g, ' ');
    if (cleanName.length < 2 || cleanName.length > 32) {
      return res.status(400).json({ ok: false, error: 'Название мемкоина должно быть от 2 до 32 символов.' });
    }
    let ticker = String(req.body?.ticker || '').trim().replace(/[^A-Za-zА-Яа-я0-9]/g, '').toUpperCase();
    if (!ticker) ticker = cleanName.replace(/[^A-Za-z0-9]/g, '').toUpperCase().slice(0, 6) || 'MEME';
    if (ticker.length < 2 || ticker.length > 8) {
      return res.status(400).json({ ok: false, error: 'Тикер должен быть от 2 до 8 символов.' });
    }
    const imageB64 = String(req.body?.image_b64 || '').trim();
    if (!/^data:image\/(png|jpeg|jpg|webp);base64,/i.test(imageB64) || imageB64.length > 1200000) {
      return res.status(400).json({ ok: false, error: 'Загрузите корректное изображение PNG, JPG или WEBP до 800 КБ.' });
    }

    u.balance_tons = Number((u.balance_tons - MEMECOIN_CREATE_TON_COST).toFixed(6));
    const nowSec = Math.floor(Date.now() / 1000);
    const bucket = nowSec - (nowSec % 60);
    const id = nextCoinId++;
    const coin: Memecoin = {
      id,
      creator_id: u.user_id,
      name: cleanName,
      ticker,
      image_url: imageB64,
      reserve_ton: 250,
      reserve_token: 1000000,
      total_supply: 1000000,
      price_ton: 0.00025,
      market_cap_ton: 250,
      volume_24h_ton: 0,
      holders_count: 1,
      created_ts: nowSec,
      candles: [{ time: bucket, open: 0.00025, high: 0.00025, low: 0.00025, close: 0.00025, volume: 0 }],
      trades: [],
      holdings: new Map(),
    };
    memecoins.set(id, coin);
    res.json({ ok: true, coin: serializeCoinSummary(coin, u.user_id), balance_tons: u.balance_tons });
  });

  app.post('/api/coins/:id/trade', (req, res) => {
    const u = resolveRequestUser(req);
    const coin = memecoins.get(Number(req.params.id));
    if (!coin) return res.status(404).json({ ok: false, error: 'Монета не найдена.' });
    const side = String(req.body?.side || '');
    const amount = Number(req.body?.amount || 0);
    if (!(amount > 0)) return res.status(400).json({ ok: false, error: 'Укажите сумму больше 0.' });

    const kConst = coin.reserve_ton * coin.reserve_token;
    const nowSec = Math.floor(Date.now() / 1000);
    const bucket = nowSec - (nowSec % 60);
    let tonVol = 0;
    let tokDelta = 0;

    if (side === 'buy') {
      const tonIn = Number(amount.toFixed(6));
      if (tonIn < 0.01) return res.status(400).json({ ok: false, error: 'Минимальная покупка — 0.01 TON.' });
      if (u.balance_tons + 1e-9 < tonIn) return res.status(400).json({ ok: false, error: 'Недостаточно TON на балансе.' });
      const effectiveTon = tonIn * 0.99;
      const newResTon = coin.reserve_ton + effectiveTon;
      const newResTok = kConst / newResTon;
      const tokensOut = Math.max(0, coin.reserve_token - newResTok);
      coin.reserve_ton = newResTon;
      coin.reserve_token = newResTok;
      coin.price_ton = newResTon / newResTok;
      coin.market_cap_ton = coin.price_ton * coin.total_supply;
      u.balance_tons = Number(Math.max(0, u.balance_tons - tonIn).toFixed(6));
      coin.holdings.set(u.user_id, (coin.holdings.get(u.user_id) || 0) + tokensOut);
      tonVol = tonIn;
      tokDelta = tokensOut;
    } else if (side === 'sell') {
      const owned = coin.holdings.get(u.user_id) || 0;
      if (owned + 1e-6 < amount) return res.status(400).json({ ok: false, error: 'Недостаточно токенов для продажи.' });
      const tokIn = Math.min(amount, owned);
      const newResTok = coin.reserve_token + tokIn;
      const newResTon = kConst / newResTok;
      const tonOut = Number((Math.max(0, coin.reserve_ton - newResTon) * 0.99).toFixed(6));
      if (tonOut <= 0) return res.status(400).json({ ok: false, error: 'Слишком маленькое количество.' });
      coin.reserve_ton = newResTon;
      coin.reserve_token = newResTok;
      coin.price_ton = newResTon / newResTok;
      coin.market_cap_ton = coin.price_ton * coin.total_supply;
      u.balance_tons = Number((u.balance_tons + tonOut).toFixed(6));
      coin.holdings.set(u.user_id, Math.max(0, owned - tokIn));
      tonVol = tonOut;
      tokDelta = tokIn;
    } else {
      return res.status(400).json({ ok: false, error: 'Неизвестная операция.' });
    }

    coin.volume_24h_ton += tonVol;
    let holders = 0;
    for (const val of coin.holdings.values()) {
      if (val > 0.0001) holders += 1;
    }
    coin.holders_count = Math.max(1, holders);

    const lastCandle = coin.candles[coin.candles.length - 1];
    if (lastCandle && lastCandle.time === bucket) {
      lastCandle.high = Math.max(lastCandle.high, coin.price_ton);
      lastCandle.low = Math.min(lastCandle.low, coin.price_ton);
      lastCandle.close = coin.price_ton;
      lastCandle.volume = Number((lastCandle.volume + tonVol).toFixed(4));
    } else {
      const open = lastCandle ? lastCandle.close : coin.price_ton;
      coin.candles.push({
        time: bucket,
        open,
        high: Math.max(open, coin.price_ton),
        low: Math.min(open, coin.price_ton),
        close: coin.price_ton,
        volume: Number(tonVol.toFixed(4)),
      });
    }

    coin.trades.unshift({
      id: nextTradeId++,
      user_id: u.user_id,
      side: side as 'buy' | 'sell',
      ton_amount: Number(tonVol.toFixed(6)),
      token_amount: Number(tokDelta.toFixed(4)),
      price_ton: Number(coin.price_ton.toFixed(8)),
      created_ts: nowSec,
    });
    coin.trades = coin.trades.slice(0, 40);

    const summary = serializeCoinSummary(coin, u.user_id);
    broadcastWS('coin_update', summary);
    res.json({
      ok: true,
      balance_tons: u.balance_tons,
      coin: summary,
      candles: coin.candles.slice(-240),
      trades: coin.trades.slice(0, 30),
    });
  });

  app.get('/api/rocket/state', (_req, res) => {
    res.json({ ok: true, rocket: getRocketPublicState() });
  });

  app.post('/api/rocket/bet', (req, res) => {
    const u = resolveRequestUser(req);
    if (rocket.phase !== 'betting') {
      return res.status(400).json({ ok: false, error: 'Приём ставок закрыт, дождитесь следующего раунда.' });
    }
    if (rocket.bets.has(u.user_id)) {
      return res.status(400).json({ ok: false, error: 'Вы уже сделали ставку в этом раунде.' });
    }
    const stakeType = String(req.body?.stake_type || 'stars');
    if (stakeType === 'stars') {
      const amt = Math.round(Number(req.body?.stake_stars || 0));
      if (amt < 50) return res.status(400).json({ ok: false, error: 'Минимальная ставка — 50 ⭐.' });
      if (u.balance_stars < amt) return res.status(400).json({ ok: false, error: 'Недостаточно Stars на балансе.' });
      u.balance_stars -= amt;
      const acRaw = Number(req.body?.auto_cashout || 0);
      rocket.bets.set(u.user_id, {
        user_id: u.user_id,
        name: u.first_name,
        avatar_url: u.avatar_url,
        stake_type: 'stars',
        stake_stars: amt,
        auto_cashout: acRaw >= 1.1 ? Number(acRaw.toFixed(2)) : null,
        status: 'active',
        cashout_mult: null,
        payout_stars: 0,
      });
    } else if (stakeType === 'nft') {
      const itemId = Number(req.body?.collection_item_id || 0);
      const item = u.collection.find((x) => x.id === itemId);
      if (!item) return res.status(400).json({ ok: false, error: 'NFT не найден в коллекции.' });
      if (item.is_listed !== 0) return res.status(400).json({ ok: false, error: 'Этот NFT уже занят.' });
      const targetKey = String(req.body?.target_gift_key || 'pepe_heart');
      const targetGift = UPGRADABLE_GIFTS.find((g) => g.key === targetKey);
      if (!targetGift) return res.status(400).json({ ok: false, error: 'Выберите доступную цель апгрейда.' });
      const mlist = MODELS_BY_GIFT[targetKey] || [];
      const mdef = mlist.find((m) => m.name === req.body?.target_model_name) || mlist[0] || { name: 'Classic', filename: '', chance_pct: 2, price_mult: 1.1, image_url: targetGift.image_url };
      const bdef = BACKDROPS.find((b) => b.key === req.body?.target_backdrop_key) || BACKDROPS[BACKDROPS.length - 1];
      const targetStars = calcUpgradedStars(targetKey, mdef, bdef);
      const reqMult = Math.max(1.35, Number(((targetStars / Math.max(1, item.display_stars)) * ROCKET_UPGRADE_MULT_PENALTY).toFixed(2)));
      item.is_listed = 2;
      rocket.bets.set(u.user_id, {
        user_id: u.user_id,
        name: u.first_name,
        avatar_url: u.avatar_url,
        stake_type: 'nft',
        stake_stars: item.display_stars,
        collection_item_id: item.id,
        item_name: item.name,
        item_image_url: item.image_url,
        target_gift_key: targetKey,
        target_gift_title: targetGift.title,
        target_model_name: mdef.name,
        target_backdrop_key: bdef.key,
        target_stars: targetStars,
        target_mult: reqMult,
        auto_cashout: reqMult,
        status: 'active',
        cashout_mult: null,
        payout_stars: 0,
      });
    } else {
      return res.status(400).json({ ok: false, error: 'Неизвестный тип ставки.' });
    }
    broadcastWS('rocket_state', getRocketPublicState());
    res.json({ ok: true, rocket: getRocketPublicState(), user: serializeUser(u), collection: u.collection });
  });

  app.post('/api/rocket/cashout', (req, res) => {
    const u = resolveRequestUser(req);
    if (rocket.phase !== 'flying') return res.status(400).json({ ok: false, error: 'Раунд сейчас не в полёте.' });
    const bet = rocket.bets.get(u.user_id);
    if (!bet || bet.status !== 'active') return res.status(400).json({ ok: false, error: 'Нет активной ставки.' });
    if (bet.stake_type === 'nft' && rocket.multiplier < 1.3) {
      return res.status(400).json({ ok: false, error: 'NFT можно забрать начиная с x1.30.' });
    }
    const result = settleRocketBet(bet, rocket.multiplier);
    broadcastWS('rocket_state', getRocketPublicState());
    res.json({ ok: true, ...result, rocket: getRocketPublicState(), user: serializeUser(u), collection: u.collection });
  });

  app.get('/api/assets/gift/:key', (req, res) => {
    const file = safeGiftAssetPath(String(req.params.key || ''));
    if (!file) return res.status(404).end();
    res.sendFile(file);
  });

  app.get('/api/assets/model/:giftKey/:filename', (req, res) => {
    const dirName = MODEL_DIR_MAP[String(req.params.giftKey || '')];
    const safeName = path.basename(decodeURIComponent(String(req.params.filename || '')));
    if (dirName && safeName) {
      const baseDir = path.resolve(IMAGES_DIR, dirName);
      const target = path.resolve(baseDir, safeName);
      if (target.startsWith(baseDir) && fs.existsSync(target)) {
        return res.sendFile(target);
      }
    }
    const fallback = safeGiftAssetPath(String(req.params.giftKey || ''));
    if (fallback) return res.sendFile(fallback);
    return res.status(404).end();
  });

  app.get('/api/assets/avatar/:uid', (req, res) => {
    const label = String(req.params.uid || '00').slice(-2);
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128"><rect width="128" height="128" rx="64" fill="#1C1C1E"/><text x="64" y="76" font-family="sans-serif" font-size="44" font-weight="700" fill="#F5F5F7" text-anchor="middle">${label}</text></svg>`;
    res.type('image/svg+xml').send(svg);
  });

  const server = http.createServer(app);
  const wss = new WebSocketServer({ server, path: '/ws' });
  wss.on('connection', (ws) => {
    wsClients.add(ws);
    ws.send(JSON.stringify({ type: 'rocket_state', data: getRocketPublicState() }));
    ws.on('message', (raw) => {
      if (raw.toString() === 'ping') ws.send('pong');
    });
    ws.on('close', () => wsClients.delete(ws));
  });

  if (process.env.NODE_ENV === 'production') {
    const distDir = path.resolve(__dirname, 'dist');
    app.use(express.static(distDir));
    app.get('*', (_req, res) => {
      res.sendFile(path.resolve(distDir, 'index.html'));
    });
  } else {
    const { createServer: createViteServer } = await import('vite');
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  }

  runRocketLoop().catch((err) => console.error('Rocket loop error:', err));

  server.listen(PORT, '0.0.0.0', () => {
    console.log(`New NFT Mini App preview server listening on http://0.0.0.0:${PORT}`);
  });
}

startServer();
