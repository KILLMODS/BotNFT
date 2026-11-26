export interface UserProfile {
  user_id: number;
  id_num: number;
  username: string;
  first_name: string;
  avatar_url: string;
  balance_stars: number;
  balance_tons: number;
  xp: number;
  level: number;
  xp_current: number;
  xp_required: number;
  xp_ratio: number;
  max_inventory: number;
}

export interface CollectionItem {
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

export interface GiftCatalogItem {
  key: string;
  title: string;
  name: string;
  base_stars: number;
  upgrade_cost: number;
  image_url: string;
}

export interface ModelDef {
  name: string;
  filename: string;
  chance_pct: number;
  price_mult: number;
  color_family?: string;
  image_url: string;
}

export interface BackdropDef {
  key: string;
  name: string;
  palette: string;
  center_hex: string;
  edge_hex: string;
  price_mult: number;
  rarity_label: string;
  color_family?: string;
}

export interface BaseGiftDef {
  key: string;
  name: string;
  stars: number;
  image_url: string;
}

export interface CatalogData {
  upgradable_gifts: GiftCatalogItem[];
  base_gifts?: BaseGiftDef[];
  models_by_gift: Record<string, ModelDef[]>;
  backdrops: BackdropDef[];
  ton_star_rate: number;
  memecoin_min_level: number;
  memecoin_create_ton_cost: number;
  upgrader_chance_factor: number;
  mono_price_mult?: number;
  rocket_upgrade_mult_penalty: number;
}

export interface RocketBet {
  user_id: number;
  name: string;
  avatar_url: string;
  stake_type: 'stars' | 'nft';
  stake_stars: number;
  item_name?: string;
  item_image_url?: string;
  source_is_upgraded?: boolean;
  target_gift_title?: string;
  target_mult?: number;
  auto_cashout?: number | null;
  status: 'active' | 'won' | 'lost';
  cashout_mult?: number | null;
  payout_stars?: number;
}

export interface RocketState {
  phase: 'betting' | 'flying' | 'crashed';
  round_id: number;
  countdown_sec: number;
  multiplier: number;
  crash_point: number | null;
  bets: RocketBet[];
  history: Array<{ round_id: number; crash_point: number }>;
}

export interface MemecoinSummary {
  id: number;
  creator_id: number;
  name: string;
  ticker: string;
  image_url: string;
  reserve_ton: number;
  reserve_token: number;
  total_supply: number;
  price_ton: number;
  price_stars: number;
  market_cap_ton: number;
  volume_24h_ton: number;
  holders_count: number;
  created_ts: number;
  change_pct: number;
  my_balance: number;
}

export interface CandleData {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface TradeData {
  id: number;
  user_id: number;
  side: 'buy' | 'sell';
  ton_amount: number;
  token_amount: number;
  price_ton: number;
  created_ts: number;
}

export type AppTab = 'home' | 'games' | 'upgrader' | 'profile' | 'exchange';
