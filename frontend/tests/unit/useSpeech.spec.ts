import { afterEach, describe, expect, it } from 'vitest'
import { isSpeechSupported, speak } from '@/composables/useSpeech'

function installSpeechSynthesis() {
  const spoken: string[] = []
  // jsdom 未提供 SpeechSynthesisUtterance，这里补一个最小替身
  Object.defineProperty(window, 'SpeechSynthesisUtterance', {
    configurable: true,
    writable: true,
    value: class {
      text: string
      lang = ''
      constructor(text: string) {
        this.text = text
      }
    },
  })
  Object.defineProperty(window, 'speechSynthesis', {
    configurable: true,
    value: {
      cancel: () => undefined,
      speak: (utterance: SpeechSynthesisUtterance) => spoken.push(utterance.text),
    },
  })
  return spoken
}

afterEach(() => {
  // @ts-expect-error 清理测试替身
  delete window.speechSynthesis
  // @ts-expect-error 清理测试替身
  delete window.SpeechSynthesisUtterance
})

describe('useSpeech 降级朗读', () => {
  it('浏览器不支持语音合成时返回 false（不抛错）', () => {
    expect(isSpeechSupported()).toBe(false)
    expect(speak('ability')).toBe(false)
  })

  it('支持时以 en-US 朗读并返回 true', () => {
    const spoken = installSpeechSynthesis()

    expect(isSpeechSupported()).toBe(true)
    expect(speak('ability')).toBe(true)
    expect(spoken).toEqual(['ability'])
  })

  it('空文本不朗读', () => {
    installSpeechSynthesis()
    expect(speak('')).toBe(false)
  })
})
