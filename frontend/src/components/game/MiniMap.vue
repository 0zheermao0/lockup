<template>
  <div class="mini-map-wrap neo-brutal-card">
    <h2 class="mini-map-title">🗺 区域地图</h2>
    <div class="mini-map" ref="mapRef">
      <svg class="mini-map-svg" aria-hidden="true">
        <line
          v-for="(line, i) in svgLines"
          :key="i"
          :x1="line.x1" :y1="line.y1"
          :x2="line.x2" :y2="line.y2"
          :class="'mini-line mini-line-' + line.state"
        />
      </svg>

      <!-- 黑市 col2 row1 -->
      <div
        class="mini-node node-black-market"
        :class="nodeClass('black_market')"
        :ref="(el) => setNodeRef('black_market', el)"
        @click="handleNodeClick('black_market')"
      >
        <div class="mini-node-inner black-market-zone">
          <span class="mini-icon">💹</span>
          <span class="mini-name">黑市</span>
          <span class="mini-count">{{ getZonePlayerCount('black_market') }}人</span>
          <span v-if="store.currentZone?.name === 'black_market'" class="mini-here">📍</span>
        </div>
      </div>

      <!-- 闺房 col2 row2 -->
      <div
        class="mini-node node-salon"
        :class="nodeClass('salon')"
        :ref="(el) => setNodeRef('salon', el)"
        @click="handleNodeClick('salon')"
      >
        <div class="mini-node-inner salon-zone">
          <span class="mini-icon">🥂</span>
          <span class="mini-name">闺房</span>
          <span class="mini-count">{{ getZonePlayerCount('salon') }}人</span>
          <span v-if="store.currentZone?.name === 'salon'" class="mini-here">📍</span>
        </div>
      </div>

      <!-- 储物柜 col1 row3 -->
      <div
        class="mini-node node-armory"
        :class="nodeClass('armory')"
        :ref="(el) => setNodeRef('armory', el)"
        @click="handleNodeClick('armory')"
      >
        <div class="mini-node-inner armory-zone">
          <span class="mini-icon">🗄️</span>
          <span class="mini-name">储物柜</span>
          <span class="mini-count">{{ getZonePlayerCount('armory') }}人</span>
          <span v-if="store.currentZone?.name === 'armory'" class="mini-here">📍</span>
        </div>
      </div>

      <!-- 安检口 col2 row3 -->
      <div
        class="mini-node node-checkpoint"
        :class="nodeClass('checkpoint')"
        :ref="(el) => setNodeRef('checkpoint', el)"
        @click="handleNodeClick('checkpoint')"
      >
        <div class="mini-node-inner checkpoint-zone">
          <span class="mini-icon">🚧</span>
          <span class="mini-name">防线</span>
          <span class="mini-count">{{ getZonePlayerCount('checkpoint') }}人</span>
          <span v-if="store.currentZone?.name === 'checkpoint'" class="mini-here">📍</span>
        </div>
      </div>

      <!-- 下水道 col3 row3 -->
      <div
        class="mini-node node-sewer"
        :class="nodeClass('sewer')"
        :ref="(el) => setNodeRef('sewer', el)"
        @click="handleNodeClick('sewer')"
      >
        <div class="mini-node-inner sewer-zone">
          <span class="mini-icon">☠️</span>
          <span class="mini-name">管道</span>
          <span class="mini-count">{{ getZonePlayerCount('sewer') }}人</span>
          <span v-if="store.currentZone?.name === 'sewer'" class="mini-here">📍</span>
        </div>
      </div>

      <!-- 更衣室 col2 row4 -->
      <div
        class="mini-node node-abandoned"
        :class="nodeClass('abandoned_camp')"
        :ref="(el) => setNodeRef('abandoned_camp', el)"
        @click="handleNodeClick('abandoned_camp')"
      >
        <div class="mini-node-inner camp-zone">
          <span class="mini-icon">⛺</span>
          <span class="mini-name">营地</span>
          <span class="mini-count">{{ getZonePlayerCount('abandoned_camp') }}人</span>
          <span v-if="store.currentZone?.name === 'abandoned_camp'" class="mini-here">📍</span>
        </div>
      </div>

      <!-- 外围备皮间 col3 row4 -->
      <div
        class="mini-node node-ruins-outer"
        :class="nodeClass('ruins_outer')"
        :ref="(el) => setNodeRef('ruins_outer', el)"
        @click="handleNodeClick('ruins_outer')"
      >
        <div class="mini-node-inner ruins-outer-zone">
          <span class="mini-icon">☢️</span>
          <span class="mini-name">外围备皮间</span>
          <span class="mini-count">{{ getZonePlayerCount('ruins_outer') }}人</span>
          <span v-if="store.currentZone?.name === 'ruins_outer'" class="mini-here">📍</span>
        </div>
      </div>

      <!-- 备皮间 col2 row5 -->
      <div
        class="mini-node node-ruins"
        :class="nodeClass('ruins')"
        :ref="(el) => setNodeRef('ruins', el)"
        @click="handleNodeClick('ruins')"
      >
        <div class="mini-node-inner ruins-zone">
          <span class="mini-icon">🔴</span>
          <span class="mini-name">备皮间</span>
          <span class="mini-count">{{ getZonePlayerCount('ruins') }}人</span>
          <span v-if="store.currentZone?.name === 'ruins'" class="mini-here">📍</span>
        </div>
      </div>

      <!-- 深处备皮间 col2 row6 -->
      <div
        class="mini-node node-ruins-deep"
        :class="nodeClass('ruins_deep')"
        :ref="(el) => setNodeRef('ruins_deep', el)"
        @click="handleNodeClick('ruins_deep')"
      >
        <div class="mini-node-inner ruins-deep-zone">
          <span class="mini-icon">🔥</span>
          <span class="mini-name">深处备皮间</span>
          <span class="mini-count">{{ getZonePlayerCount('ruins_deep') }}人</span>
          <span v-if="store.currentZone?.name === 'ruins_deep'" class="mini-here">📍</span>
        </div>
      </div>

    </div><!-- .mini-map -->
    <p v-if="travelError" class="mini-error">{{ travelError }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { usePhantomCityStore } from '../../stores/phantomCity'

const store = usePhantomCityStore()
const router = useRouter()

const traveling = ref(false)
const travelError = ref<string | null>(null)
const mapRef = ref<HTMLElement | null>(null)
const nodeRefs = ref<Record<string, HTMLElement | null>>({})

const ZONE_ADJACENCY: Record<string, string[]> = {
  black_market:       ['salon'],
  salon:              ['black_market', 'checkpoint', 'armory', 'sewer'],
  armory:             ['salon', 'abandoned_camp'],
  checkpoint:         ['salon', 'abandoned_camp'],
  sewer:              ['salon', 'ruins_outer'],
  abandoned_camp:     ['armory', 'checkpoint', 'ruins', 'ruins_outer'],
  ruins_outer:        ['sewer', 'abandoned_camp', 'ruins'],
  ruins:              ['abandoned_camp', 'ruins_outer', 'ruins_deep'],
  ruins_deep:         ['ruins'],
  interrogation_room: [],
  control_room:       [],
}

const ZONE_ROUTES: Record<string, string> = {
  black_market:   '/phantom-city/black-market',
  salon:          '/phantom-city/salon',
  armory:         '/phantom-city/armory',
  checkpoint:     '/phantom-city/checkpoint',
  sewer:          '/phantom-city/sewer',
  abandoned_camp: '/phantom-city/abandoned-camp',
  ruins_outer:    '/phantom-city/ruins-outer',
  ruins:          '/phantom-city/ruins',
  ruins_deep:     '/phantom-city/ruins-deep',
}

const CONNECTIONS: [string, string][] = [
  ['black_market', 'salon'],
  ['salon', 'armory'],
  ['salon', 'checkpoint'],
  ['salon', 'sewer'],
  ['armory', 'abandoned_camp'],
  ['checkpoint', 'abandoned_camp'],
  ['sewer', 'ruins_outer'],
  ['abandoned_camp', 'ruins_outer'],
  ['abandoned_camp', 'ruins'],
  ['ruins_outer', 'ruins'],
  ['ruins', 'ruins_deep'],
]

interface SvgLine {
  x1: number; y1: number; x2: number; y2: number; state: string
}
const svgLines = ref<SvgLine[]>([])

function setNodeRef(zoneName: string, el: unknown) {
  nodeRefs.value[zoneName] = el instanceof HTMLElement ? el : null
}

function recalcLines() {
  const container = mapRef.value
  if (!container) return
  const containerRect = container.getBoundingClientRect()
  const lines: SvgLine[] = []
  const current = store.currentZone?.name

  for (const [a, b] of CONNECTIONS) {
    const elA = nodeRefs.value[a]
    const elB = nodeRefs.value[b]
    if (!elA || !elB) continue
    const ra = elA.getBoundingClientRect()
    const rb = elB.getBoundingClientRect()
    const x1 = ra.left + ra.width / 2 - containerRect.left
    const y1 = ra.top + ra.height / 2 - containerRect.top
    const x2 = rb.left + rb.width / 2 - containerRect.left
    const y2 = rb.top + rb.height / 2 - containerRect.top

    let state = 'normal'
    if (current === a || current === b) {
      state = 'current'
    } else if (
      current && ZONE_ADJACENCY[current]?.includes(a) && ZONE_ADJACENCY[current]?.includes(b)
    ) {
      state = 'adjacent'
    }
    lines.push({ x1, y1, x2, y2, state })
  }
  svgLines.value = lines
}

function isAdjacent(zoneName: string): boolean {
  const current = store.currentZone?.name
  if (!current) return false
  return ZONE_ADJACENCY[current]?.includes(zoneName) ?? false
}

function nodeClass(zoneName: string) {
  const current = store.currentZone?.name
  return {
    'zone-current': current === zoneName,
    'zone-adjacent': isAdjacent(zoneName),
    'zone-blocked': current !== zoneName && !isAdjacent(zoneName),
  }
}

function getZonePlayerCount(zoneName: string): number {
  const zone = store.zones.find(z => z.name === zoneName)
  return zone?.player_count ?? 0
}

function handleNodeClick(zoneName: string) {
  if (store.currentZone?.name === zoneName) return
  if (!isAdjacent(zoneName)) return
  travelTo(zoneName)
}

async function travelTo(zoneName: string) {
  traveling.value = true
  travelError.value = null
  try {
    await store.travelTo(zoneName)
    await store.loadZones()
    const route = ZONE_ROUTES[zoneName]
    if (route) router.push(route)
  } catch (e: unknown) {
    travelError.value = e instanceof Error ? e.message : '移动失败'
  } finally {
    traveling.value = false
  }
}

let resizeObserver: ResizeObserver | null = null

watch(() => store.currentZone, async () => {
  await nextTick()
  recalcLines()
})

onMounted(async () => {
  await nextTick()
  recalcLines()
  if (mapRef.value) {
    resizeObserver = new ResizeObserver(() => recalcLines())
    resizeObserver.observe(mapRef.value)
  }
})

onUnmounted(() => {
  resizeObserver?.disconnect()
})
</script>

<style scoped>
.mini-map-wrap {
  background: #fff;
  padding: 0 0 10px;
  border: 2px solid #000;
  box-shadow: 4px 4px 0 #000;
}

.mini-map-title {
  font-size: 13px;
  font-weight: 900;
  margin: 0 0 8px;
  padding: 10px 12px 0;
  font-family: 'Courier New', Courier, monospace;
}

.mini-map {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  grid-template-rows: repeat(6, auto);
  gap: 5px 4px;
  position: relative;
  padding: 0 8px;
}

.mini-map-svg {
  position: absolute;
  top: 0; left: 0;
  width: 100%; height: 100%;
  pointer-events: none;
  z-index: 0;
  overflow: visible;
}

.mini-line {
  stroke-linecap: round;
}
.mini-line-current  { stroke: #d97706; stroke-width: 2; }
.mini-line-adjacent { stroke: #16a34a; stroke-width: 1.5; }
.mini-line-normal   { stroke: #d1d5db; stroke-width: 1.5; }

/* Grid positions */
.node-black-market { grid-column: 2; grid-row: 1; }
.node-salon        { grid-column: 2; grid-row: 2; }
.node-armory       { grid-column: 1; grid-row: 3; }
.node-checkpoint   { grid-column: 2; grid-row: 3; }
.node-sewer        { grid-column: 3; grid-row: 3; }
.node-abandoned    { grid-column: 2; grid-row: 4; }
.node-ruins-outer  { grid-column: 3; grid-row: 4; }
.node-ruins        { grid-column: 2; grid-row: 5; }
.node-ruins-deep   { grid-column: 2; grid-row: 6; }

.mini-node {
  position: relative;
  z-index: 1;
  transition: opacity 0.2s;
}

/* 当前节点 */
.mini-node.zone-current {
  cursor: default;
}

/* 邻接节点：可点击 */
.mini-node.zone-adjacent {
  cursor: pointer;
}
.mini-node.zone-adjacent:hover .mini-node-inner {
  transform: translate(-1px, -1px);
  box-shadow: 3px 3px 0 #000;
}

/* 不可达节点：灰化不可点 */
.mini-node.zone-blocked {
  opacity: 0.35;
  cursor: not-allowed;
  pointer-events: none;
}

.mini-node-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 5px 3px;
  border: 1.5px solid #000;
  box-shadow: 2px 2px 0 #000;
  min-height: 56px;
  text-align: center;
  font-family: 'Courier New', Courier, monospace;
  transition: transform 0.1s, box-shadow 0.1s;
}

.mini-node.zone-current .mini-node-inner {
  border-width: 2px;
  box-shadow: 3px 3px 0 #000;
}

/* Zone color themes */
.black-market-zone { background: #1a1a2e; color: #f0c040; }
.salon-zone        { background: #f0fdf4; color: #000; }
.armory-zone       { background: #1f1f1f; color: #ccc; }
.checkpoint-zone   { background: #fef2f2; color: #000; }
.sewer-zone        { background: #0a1a0a; color: #44ff44; }
.camp-zone         { background: #fef9c3; color: #000; }
.ruins-outer-zone  { background: #fff7ed; color: #000; }
.ruins-zone        { background: #fef2f2; color: #000; }
.ruins-deep-zone   { background: #1a0505; color: #ff8080; }

.mini-icon  { font-size: 13px; line-height: 1; }
.mini-name  { font-size: 9px; font-weight: 900; line-height: 1.2; }
.mini-count { font-size: 8px; opacity: 0.7; }

.mini-here {
  font-size: 10px;
  color: #059669;
  margin-top: 1px;
}

.mini-error {
  color: #dc2626;
  font-size: 11px;
  font-weight: 700;
  padding: 0 12px;
  margin: 6px 0 0;
  font-family: 'Courier New', Courier, monospace;
}
</style>
