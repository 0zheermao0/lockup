/**
 * 男娘幻城 — Pinia Store
 */
import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import * as api from '../lib/api-game'
import type {
  GameProfile, GameZone, ZoneChatMessage, CheckpointSession,
  DetentionRecord, GameControlTransfer, GrayMarketTransaction,
  EncryptedMessage, CrystalDeposit, GameMarketRate,
  PlayerGameInventory, TellEvent,
} from '../lib/api-game'

export const usePhantomCityStore = defineStore('phantomCity', () => {
  // ── 档案 ──
  const profile = ref<GameProfile | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  // ── 区域 ──
  const zones = ref<GameZone[]>([])
  const currentZone = computed(() => profile.value?.current_zone ?? null)
  const chatMessages = ref<ZoneChatMessage[]>([])

  // ── 安检口 ──
  const checkpointSession = ref<CheckpointSession | null>(null)
  const suspicionData = ref<Record<string, number>>({})
  const inspectionTokens = ref(10)

  // ── 收押 ──
  const myDetention = ref<DetentionRecord | null>(null)

  // ── 控制权 ──
  const controlTransfers = ref<GameControlTransfer[]>([])

  // ── 加密频道 ──
  const activeChannelId = ref<string | null>(null)
  const channelMessages = ref<EncryptedMessage[]>([])
  const activeTransaction = ref<GrayMarketTransaction | null>(null)

  // ── 市场 ──
  const marketRates = ref<GameMarketRate[]>([])
  const ruinsDeposits = ref<CrystalDeposit[]>([])
  const ruinsDeepDeposits = ref<CrystalDeposit[]>([])
  const ruinsOuterDeposits = ref<CrystalDeposit[]>([])
  const inventory = ref<PlayerGameInventory[]>([])

  // ── 计算属性 ──
  const mimicProfile = computed(() => profile.value?.mimic_profile ?? null)
  const patrolProfile = computed(() => profile.value?.patrol_profile ?? null)
  const crystals = computed(() => profile.value?.crystals ?? null)
  const activeDisguise = computed(() => profile.value?.active_disguise ?? null)
  const isDetained = computed(() => !!profile.value?.active_detention)
  const currentFaction = computed(() => {
    if (profile.value === null) return null
    return profile.value.has_active_lock ? 'mimic' : 'patrol'
  })

  // ── 动作 ──

  async function loadProfile() {
    isLoading.value = true
    error.value = null
    try {
      profile.value = await api.getGameProfile()
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '加载档案失败'
    } finally {
      isLoading.value = false
    }
  }

  async function loadZones() {
    zones.value = await api.getZones()
  }

  async function travelTo(zoneName: string) {
    const result = await api.travelToZone(zoneName)
    if (result.success) {
      await loadProfile()
      await loadChatMessages(zoneName)
    }
    return result
  }

  async function loadChatMessages(zoneName: string) {
    chatMessages.value = await api.getZoneChat(zoneName)
  }

  async function speak(content: string) {
    if (!currentZone.value) return null
    const result = await api.speakInZone(currentZone.value.name, content)
    if (result.success) {
      chatMessages.value.push(result.message)
    }
    return result
  }

  async function loadCheckpointSession() {
    checkpointSession.value = await api.getCheckpointSession()
  }

  async function loadSuspicion() {
    const data = await api.getSuspicionData()
    suspicionData.value = data.suspicion_evidence
    inspectionTokens.value = data.inspection_tokens
  }

  async function loadDetention() {
    const data = await api.getMyDetention()
    myDetention.value = data.detained ? (data.detention ?? null) : null
  }

  async function loadControlTransfers() {
    controlTransfers.value = await api.getControlTransfers()
  }

  async function loadMarketRates() {
    marketRates.value = await api.getMarketRates()
  }

  async function loadDeposits() {
    ruinsDeposits.value = await api.getRuinsDeposits()
  }

  async function loadDeepDeposits() {
    ruinsDeepDeposits.value = await api.getRuinsDeepDeposits()
  }

  async function loadOuterDeposits() {
    ruinsOuterDeposits.value = await api.getRuinsOuterDeposits()
  }

  async function loadInventory() {
    inventory.value = await api.getInventory()
  }

  async function openEncryptedChannel(channelId: string, transaction: GrayMarketTransaction) {
    activeChannelId.value = channelId
    activeTransaction.value = transaction
    await refreshChannelMessages()
  }

  async function refreshChannelMessages() {
    if (!activeChannelId.value) return
    const data = await api.getChannelMessages(activeChannelId.value)
    channelMessages.value = data.messages
  }

  async function sendChannelMessage(content: string) {
    if (!activeChannelId.value) return
    const msg = await api.sendChannelMessage(activeChannelId.value, content)
    channelMessages.value.push(msg)
    return msg
  }

  function closeChannel() {
    activeChannelId.value = null
    channelMessages.value = []
    activeTransaction.value = null
  }

  async function salonRest() {
    const result = await api.salonRest()
    if (result.success) {
      await loadProfile()
    }
    return result
  }

  return {
    // state
    profile, isLoading, error,
    zones, chatMessages,
    checkpointSession, suspicionData, inspectionTokens,
    myDetention, controlTransfers,
    activeChannelId, channelMessages, activeTransaction,
    marketRates, ruinsDeposits, ruinsDeepDeposits, ruinsOuterDeposits, inventory,
    // computed
    mimicProfile, patrolProfile, crystals, activeDisguise,
    currentZone, isDetained, currentFaction,
    // actions
    loadProfile, loadZones, travelTo, loadChatMessages, speak,
    loadCheckpointSession, loadSuspicion,
    loadDetention, loadControlTransfers,
    loadMarketRates, loadDeposits, loadDeepDeposits, loadOuterDeposits, loadInventory,
    openEncryptedChannel, refreshChannelMessages, sendChannelMessage, closeChannel,
    salonRest,
  }
})
