/** 浏览器语音合成降级：服务端发音不可用时用它朗读英文单词。 */
export function isSpeechSupported(): boolean {
  return typeof window !== 'undefined' && 'speechSynthesis' in window
}

export function speak(text: string): boolean {
  if (!isSpeechSupported() || !text) {
    return false
  }
  try {
    const utterance = new SpeechSynthesisUtterance(text)
    utterance.lang = 'en-US'
    // 与服务端 TTS 的 -15% 保持一致，避免降级朗读时语速突变
    utterance.rate = 0.85
    window.speechSynthesis.cancel()
    window.speechSynthesis.speak(utterance)
    return true
  } catch {
    return false
  }
}

export function useSpeech() {
  return { isSpeechSupported, speak }
}
