/**
 * 男娘幻城 — 游戏 API 层
 */
import { apiRequest } from './api-commons'

// ─────────────────────────────────────────────
// 类型定义
// ─────────────────────────────────────────────

export interface GameZone {
  id: number
  name: 'ruins' | 'ruins_deep' | 'ruins_outer' | 'salon' | 'black_market' | 'checkpoint' | 'abandoned_camp' | 'armory' | 'sewer' | 'control_room' | 'interrogation_room'
  display_name: string
  description: string
  player_count: number
}

export interface MimicProfile {
  username: string
  avatar: string | null
  depilation_charge: number
  suppression_value: number
  purity_score: number
  femboy_score: number
  smoothness_score: number
  control_resistance: number
  base_detectability: number
  current_faction: 'mimic' | 'patrol'
  is_disguised: boolean
  total_successful_runs: number
  total_failed_runs: number
  total_crystals_collected: number
  permanent_tells: string[]
}

export interface PatrolProfile {
  username: string
  avatar: string | null
  authority_value: number
  reputation_score: number
  inspection_tokens: number
  current_faction: 'mimic' | 'patrol'
  total_arrests: number
  false_accusations: number
  total_correct_identifications: number
  detection_tools: Record<string, boolean>
}

export interface TellEvent {
  id: string
  player_username: string
  tell_type: string
  tell_text: string
  action_type: string
  created_at: string
}

export interface ZoneChatMessage {
  id: string
  sender: { id: number; username: string; avatar: string | null } | null
  content: string
  is_system: boolean
  created_at: string
  tells: TellEvent[]
}

export interface CheckpointParticipant {
  id: number
  user: { id: number; username: string; avatar: string | null }
  role: 'smuggler' | 'patrol'
  outcome: 'pending' | 'passed' | 'arrested' | 'fled' | 'bribed_through'
  entered_at: string
  queue_position: number | null
}

export interface CheckpointSession {
  id: string
  status: 'active' | 'closed'
  npc_count: number
  opened_at: string
  participants: CheckpointParticipant[]
  npc_queue: Array<{
    id: string
    name: string
    description: string
    tells: string[]
  }>
}

export interface InterrogationRequest {
  id: string
  interrogator: { id: number; username: string; avatar: string | null }
  target: { id: number; username: string; avatar: string | null }
  status: 'pending' | 'answered' | 'expired'
  question: string
  response_text: string
  response_time_seconds: number | null
  triggered_pause_tell: boolean
  created_at: string
  deadline: string
}

export interface GrayMarketTransaction {
  id: string
  transaction_type: 'bribe' | 'extortion' | 'trade'
  initiator: { id: number; username: string; avatar: string | null }
  recipient: { id: number; username: string; avatar: string | null }
  status: string
  offer_from_initiator: Record<string, unknown>
  offer_from_recipient: Record<string, unknown>
  escrowed_crystals: number
  encrypted_channel_id: string | null
  negotiation_log: unknown[]
  created_at: string
  expires_at: string
}

export interface GameControlTransfer {
  id: string
  grantor: { id: number; username: string; avatar: string | null }
  grantee: { id: number; username: string; avatar: string | null }
  lock_task_title: string
  source: 'arrest' | 'bribe_deal' | 'extortion_deal'
  can_add_time: boolean
  can_freeze: boolean
  can_assign_tasks: boolean
  duration_hours: number
  expires_at: string
  is_active: boolean
}

export interface DetentionRecord {
  id: string
  prisoner: { id: number; username: string; avatar: string | null }
  captor: { id: number; username: string; avatar: string | null }
  status: string
  seized_crystals: number
  duration_hours: number
  arrested_at: string
  release_at: string
  charm_attempts_used: number
  last_charm_at: string | null
  control_transfer: GameControlTransfer | null
  time_remaining_seconds: number
}

export interface EncryptedMessage {
  id: string
  sender: { id: number; username: string; avatar: string | null } | null
  content: string
  is_system: boolean
  created_at: string
}

export interface CrystalDeposit {
  id: string
  zone_name: string
  quantity: number
  max_quantity: number
  respawn_rate_per_hour: number
}

export interface PlayerCrystals {
  raw_crystals: number
  purified_crystals: number
  updated_at: string
}

export interface GameMarketRate {
  item_slug: string
  item_display_name: string
  current_price_crystals: number
  base_price_crystals: number
  demand_pressure: number
  last_recalculated_at: string
}

export interface GameItem {
  id: number
  slug: string
  name: string
  tier: 1 | 2 | 3 | 4
  slot: string
  description: string
  icon: string
  stat_modifiers: Record<string, number>
  is_lock_device: boolean
  is_removal_device: boolean
  is_disguise_item: boolean
  permanent_tell: string
  permanent_detectability_bonus: number
  craft_recipe: Record<string, unknown>
  price_crystals: number
  available_in_zones: string[]
}

export interface PlayerGameInventory {
  id: number
  item: GameItem
  quantity: number
  obtained_at: string
}

export interface ActiveDisguise {
  outer_layer_item: GameItem | null
  inner_items: GameItem[]
  behavioral_mode: 'passive' | 'confident' | 'evasive'
  computed_detectability: number
  computed_disguise_quality: number
  computed_active_tells: string[]
  last_computed_at: string
}

export interface GameProfile {
  mimic_profile: MimicProfile | null
  patrol_profile: PatrolProfile | null
  crystals: PlayerCrystals | null
  active_disguise: ActiveDisguise | null
  current_zone: GameZone | null
  active_detention: DetentionRecord | null
  active_control_transfers: GameControlTransfer[]
  has_active_lock: boolean
}

// ─────────────────────────────────────────────
// API 函数
// ─────────────────────────────────────────────

// 档案
export const getGameProfile = () =>
  apiRequest<GameProfile>('/game/profile/')

export const chooseFaction = (faction: 'mimic' | 'patrol') =>
  apiRequest<{ success: boolean; faction: string }>('/game/profile/faction/', {
    method: 'POST',
    body: JSON.stringify({ faction }),
  })

export const salonRest = () =>
  apiRequest<{ success: boolean; suppression_before: number; suppression_after: number }>('/game/profile/rest/', {
    method: 'POST',
  })

// 区域
export const getZones = () =>
  apiRequest<GameZone[]>('/game/zones/')

export const travelToZone = (zone: string) =>
  apiRequest<{ success: boolean; zone: GameZone }>('/game/zones/travel/', {
    method: 'POST',
    body: JSON.stringify({ zone }),
  })

export const getZonePlayers = (zoneName: string) =>
  apiRequest<unknown[]>(`/game/zones/${zoneName}/players/`)

export const getZoneChat = (zoneName: string) =>
  apiRequest<ZoneChatMessage[]>(`/game/zones/${zoneName}/chat/`)

export const speakInZone = (zoneName: string, content: string) =>
  apiRequest<{ success: boolean; message: ZoneChatMessage; tells: TellEvent[] }>(
    `/game/zones/${zoneName}/speak/`,
    { method: 'POST', body: JSON.stringify({ content }) }
  )

// 安检口
export const getCheckpointSession = () =>
  apiRequest<CheckpointSession>('/game/checkpoint/session/')

export const inspectPlayer = (targetId: number, sessionId: string) =>
  apiRequest<{ tells: Array<{ type: string; text: string }>; suspicion_score: number; can_pat_down: boolean }>(
    '/game/checkpoint/inspect/',
    { method: 'POST', body: JSON.stringify({ target_id: targetId, session_id: sessionId }) }
  )

export const interrogatePlayer = (targetId: number, sessionId: string, question: string) =>
  apiRequest<InterrogationRequest>('/game/checkpoint/interrogate/', {
    method: 'POST',
    body: JSON.stringify({ target_id: targetId, session_id: sessionId, question }),
  })

export const respondToInterrogation = (interrogationId: string, response: string) =>
  apiRequest<{ success: boolean; response_time: number; tells: TellEvent[] }>(
    `/game/checkpoint/interrogate/${interrogationId}/respond/`,
    { method: 'POST', body: JSON.stringify({ response }) }
  )

export const patDownPlayer = (targetId: number, sessionId: string) =>
  apiRequest<{
    success: boolean
    arrested: boolean
    detention?: DetentionRecord
    false_accusation?: boolean
    inspection_tokens_remaining?: number
    authority_gained?: number
    reputation_gained?: number
    reputation_lost?: number
  }>(
    '/game/checkpoint/pat_down/',
    { method: 'POST', body: JSON.stringify({ target_id: targetId, session_id: sessionId }) }
  )

export const getSuspicionData = () =>
  apiRequest<{ suspicion_evidence: Record<string, number>; inspection_tokens: number }>(
    '/game/checkpoint/suspicion/'
  )

// 打点
export const proposeBribe = (recipientId: number, offer: Record<string, unknown>, sessionId?: string) =>
  apiRequest<{ success: boolean; transaction: GrayMarketTransaction; channel: { id: string } }>(
    '/game/bribe/propose/',
    { method: 'POST', body: JSON.stringify({ recipient_id: recipientId, offer, session_id: sessionId }) }
  )

export const counterBribe = (transactionId: string, offer: Record<string, unknown>) =>
  apiRequest<{ success: boolean; transaction: GrayMarketTransaction }>(
    `/game/bribe/${transactionId}/counter/`,
    { method: 'POST', body: JSON.stringify({ offer }) }
  )

export const acceptBribe = (transactionId: string) =>
  apiRequest<{ success: boolean }>(`/game/bribe/${transactionId}/accept/`, { method: 'POST' })

// 威胁
export const demandExtortion = (targetId: number, demand: Record<string, unknown>, sessionId?: string) =>
  apiRequest<{ success: boolean; transaction: GrayMarketTransaction; channel: { id: string } }>(
    '/game/extort/demand/',
    { method: 'POST', body: JSON.stringify({ target_id: targetId, demand, session_id: sessionId }) }
  )

export const payExtortion = (transactionId: string) =>
  apiRequest<{ success: boolean }>(`/game/extort/${transactionId}/pay/`, { method: 'POST' })

export const refuseExtortion = (transactionId: string) =>
  apiRequest<{ success: boolean }>(`/game/extort/${transactionId}/refuse/`, { method: 'POST' })

// 交易
export const proposeTrade = (recipientId: number, offerA: Record<string, unknown>) =>
  apiRequest<{ success: boolean; transaction: GrayMarketTransaction }>(
    '/game/trade/propose/',
    { method: 'POST', body: JSON.stringify({ recipient_id: recipientId, offer_a: offerA }) }
  )

export const acceptTrade = (transactionId: string, offerB: Record<string, unknown>) =>
  apiRequest<{ success: boolean }>(`/game/trade/${transactionId}/accept/`, {
    method: 'POST',
    body: JSON.stringify({ offer_b: offerB }),
  })

// 加密频道
export const getChannelMessages = (channelId: string, since?: string) => {
  const url = `/game/channel/${channelId}/messages/${since ? `?since=${since}` : ''}`
  return apiRequest<{ channel_id: string; is_active: boolean; messages: EncryptedMessage[] }>(url)
}

export const sendChannelMessage = (channelId: string, content: string) =>
  apiRequest<EncryptedMessage>(`/game/channel/${channelId}/send/`, {
    method: 'POST',
    body: JSON.stringify({ content }),
  })

// 收押
export const getMyDetention = () =>
  apiRequest<{ detained: boolean; detention?: DetentionRecord }>('/game/detention/my/')

export const charmWarden = (detentionId: string) =>
  apiRequest<{
    success: boolean
    authority_drained?: number
    captor_authority_remaining?: number
    conversion_triggered?: boolean
  }>(`/game/detention/${detentionId}/charm_warden/`, { method: 'POST' })

// 控制权
export const getControlTransfers = () =>
  apiRequest<GameControlTransfer[]>('/game/control-transfers/')

export const addTimeToLock = (transferId: string, minutes: number) =>
  apiRequest<{ success: boolean; new_end_time: string }>(
    `/game/control-transfers/${transferId}/add_time/`,
    { method: 'POST', body: JSON.stringify({ minutes }) }
  )

export const freezeLock = (transferId: string) =>
  apiRequest<{ success: boolean }>(`/game/control-transfers/${transferId}/freeze/`, { method: 'POST' })

// 市场与收集
export const getMarketRates = () =>
  apiRequest<GameMarketRate[]>('/game/market/rates/')

export const buyItem = (itemSlug: string, quantity = 1) =>
  apiRequest<{ success: boolean; item: GameItem; quantity: number; cost: number; crystals_remaining: number }>(
    '/game/market/buy/',
    { method: 'POST', body: JSON.stringify({ item_slug: itemSlug, quantity }) }
  )

export const getRuinsDeposits = () =>
  apiRequest<CrystalDeposit[]>('/game/ruins/deposits/')

export const getRuinsDeepDeposits = () =>
  apiRequest<CrystalDeposit[]>('/game/ruins-deep/deposits/')

export const getRuinsOuterDeposits = () =>
  apiRequest<CrystalDeposit[]>('/game/ruins-outer/deposits/')

export const harvestCrystals = (depositId: string) =>
  apiRequest<{ success: boolean; harvested: number; remaining: number }>(
    '/game/ruins/harvest/',
    { method: 'POST', body: JSON.stringify({ deposit_id: depositId }) }
  )

// 安检口溜走
export const checkpointFlee = (sessionId: string) =>
  apiRequest<{ success: boolean; suppression_added: number; purity_lost: number }>(
    '/game/checkpoint/flee/',
    { method: 'POST', body: JSON.stringify({ session_id: sessionId }) }
  )

// 储物柜遭遇战
export interface ArmoryEncounter {
  triggered: boolean
  other_player: { id: number; username: string } | null
  role: 'demand' | 'target' | null
}

export const checkArmoryEncounter = () =>
  apiRequest<ArmoryEncounter>('/game/armory/encounter/check/', { method: 'POST' })

export const armoryTollDemand = (targetId: number, crystals: number) =>
  apiRequest<{ success: boolean; transaction_id: string; channel_id: string }>(
    '/game/armory/toll/demand/',
    { method: 'POST', body: JSON.stringify({ target_id: targetId, crystals }) }
  )

export const armoryTollPay = (transactionId: string) =>
  apiRequest<{ success: boolean; crystals_paid: number }>(
    `/game/armory/toll/${transactionId}/pay/`,
    { method: 'POST' }
  )

export const armoryTollResist = (transactionId: string) =>
  apiRequest<{ success: boolean; escaped: boolean; suppression_change?: number; crystals_seized?: number }>(
    `/game/armory/toll/${transactionId}/resist/`,
    { method: 'POST' }
  )

export const armoryFlee = () =>
  apiRequest<{ success: boolean; suppression_added: number }>(
    '/game/armory/flee/',
    { method: 'POST' }
  )

// 下水道遭遇
export interface SewerEncounter {
  triggered: boolean
  type?: 'mimic_mimic' | 'patrol_mimic'
  resolved?: boolean
  role?: 'demand' | 'target'
  other_player?: { id: number; username: string }
  tells?: string[]
}

export const checkSewerEncounter = () =>
  apiRequest<SewerEncounter>('/game/sewer/encounter/check/', { method: 'POST' })

export const sewerDemand = (targetId: number, amount: number) =>
  apiRequest<{ success: boolean; crystals_seized: number; tells: string[] }>(
    '/game/sewer/encounter/demand/',
    { method: 'POST', body: JSON.stringify({ target_id: targetId, amount }) }
  )

// 黑市洗白
export const bmLaunder = (amount: number) =>
  apiRequest<{ success: boolean; raw_consumed: number; purified_gained: number }>(
    '/game/black-market/launder/',
    { method: 'POST', body: JSON.stringify({ amount }) }
  )

// 更衣室互助
export const campShareFood = (recipientId: number) =>
  apiRequest<{ success: boolean; item_used: string; recipient_suppression: number }>(
    '/game/camp/share-food/',
    { method: 'POST', body: JSON.stringify({ recipient_id: recipientId }) }
  )

export const campStartWatch = () =>
  apiRequest<{ success: boolean; watch_until: string }>(
    '/game/camp/watch/start/',
    { method: 'POST' }
  )

export const campActiveWatches = () =>
  apiRequest<Array<{ id: number; username: string }>>('/game/camp/watch/active/')

// 背包
export const getInventory = () =>
  apiRequest<PlayerGameInventory[]>('/game/inventory/')

export const equipItem = (itemId: number, slot: 'outer' | 'inner') =>
  apiRequest<{ success: boolean; disguise: ActiveDisguise }>('/game/inventory/equip/', {
    method: 'POST',
    body: JSON.stringify({ item_id: itemId, slot }),
  })

export const unequipItem = (itemId: number, slot: 'outer' | 'inner') =>
  apiRequest<{ success: boolean }>('/game/inventory/unequip/', {
    method: 'POST',
    body: JSON.stringify({ item_id: itemId, slot }),
  })
