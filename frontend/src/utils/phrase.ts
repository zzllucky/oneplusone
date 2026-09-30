/** 常用短语解析：按 `；` 拆条，并分离英文短语与中文注释（发音只朗读英文部分）。 */

export interface PhraseEntry {
  /** 英文短语（可朗读部分） */
  english: string
  /** 中文注释（仅展示，不朗读） */
  chinese: string
  /** 原始整条文本 */
  raw: string
}

const NON_ASCII = /[^\x00-\x7F]/

export function splitPhraseEntry(line: string): PhraseEntry {
  const raw = line.trim()
  const separatorIndex = raw.search(NON_ASCII)
  if (separatorIndex < 0) {
    return { english: raw, chinese: '', raw }
  }
  return {
    english: raw.slice(0, separatorIndex).trim(),
    chinese: raw.slice(separatorIndex).trim(),
    raw,
  }
}

export function parsePhrases(phrase: string | null | undefined): PhraseEntry[] {
  if (!phrase) return []
  return phrase
    .split('；')
    .map((item) => item.trim())
    .filter(Boolean)
    .map(splitPhraseEntry)
}
