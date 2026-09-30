/** 发音播放链路：共享播放器 + 解码器预热 + 预取。

浏览器在**首次真正出声**时才初始化音频解码器与输出设备，开头容易被吞掉，
表现为前几个单词"又小又短"。这里在用户第一次手势时用一段听不见的静音把
链路跑通，之后真实播放即为完整满音量播放。
*/

import { fetchAudio } from '@/api/client'

let player: HTMLAudioElement | null = null
let warmedUp = false

/** 所有发音按钮共用的播放器：避免多次点击时多实例并发或被回收截断。 */
export function getPlayer(): HTMLAudioElement {
  if (!player) {
    player = new Audio()
    player.preload = 'auto'
  }
  return player
}

/** 构造 0.2s 静音 WAV（8kHz / 8bit 单声道），仅用于预热播放。 */
function createSilentWavUrl(): string {
  const sampleRate = 8000
  const dataLength = Math.floor(sampleRate * 0.2)
  const buffer = new ArrayBuffer(44 + dataLength)
  const view = new DataView(buffer)

  const writeText = (offset: number, text: string) => {
    for (let i = 0; i < text.length; i += 1) {
      view.setUint8(offset + i, text.charCodeAt(i))
    }
  }

  writeText(0, 'RIFF')
  view.setUint32(4, 36 + dataLength, true)
  writeText(8, 'WAVE')
  writeText(12, 'fmt ')
  view.setUint32(16, 16, true)
  view.setUint16(20, 1, true) // PCM
  view.setUint16(22, 1, true) // 单声道
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate, true)
  view.setUint16(32, 1, true)
  view.setUint16(34, 8, true)
  writeText(36, 'data')
  view.setUint32(40, dataLength, true)
  for (let i = 0; i < dataLength; i += 1) {
    view.setUint8(44 + i, 128) // 8bit 静音电平
  }

  return URL.createObjectURL(new Blob([buffer], { type: 'audio/wav' }))
}

/** 预热：静音播放一小段音频，完成解码与输出设备初始化（幂等）。 */
export async function warmUpAudio(): Promise<void> {
  if (warmedUp) return
  warmedUp = true

  const url = createSilentWavUrl()
  const audio = new Audio(url)
  audio.muted = true
  audio.preload = 'auto'
  try {
    await audio.play()
    await new Promise<void>((resolve) => {
      audio.addEventListener('ended', () => resolve(), { once: true })
      window.setTimeout(resolve, 600)
    })
  } catch {
    // 预热失败不阻断后续正式播放
  } finally {
    audio.pause()
    audio.removeAttribute('src')
    URL.revokeObjectURL(url)
  }
}

/** 首次任意手势即预热：pointerdown 早于 click，先于发音请求完成。 */
export function registerAudioWarmup(): void {
  const handler = () => {
    void warmUpAudio()
  }
  const options: AddEventListenerOptions = { once: true, capture: true }
  document.addEventListener('pointerdown', handler, options)
  document.addEventListener('touchstart', handler, options)
  document.addEventListener('keydown', handler, options)
}

/** 预取发音：让服务端提前合成并缓存，点击时不再等待合成。 */
export async function prefetchPronunciation(text: string): Promise<void> {
  const value = text.trim()
  if (!value) return
  try {
    await fetchAudio(`/api/pronounce/${encodeURIComponent(value)}`)
  } catch {
    // 预取失败不影响点击时重新请求
  }
}
