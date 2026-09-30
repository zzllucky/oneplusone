import { describe, expect, it } from 'vitest'
import { parsePhrases, splitPhraseEntry } from '@/utils/phrase'

describe('parsePhrases', () => {
  it('按 ； 拆成多条并分离英文与中文', () => {
    const entries = parsePhrases('talk about 谈论；think about 思考')
    expect(entries).toHaveLength(2)
    expect(entries[0]).toMatchObject({ english: 'talk about', chinese: '谈论' })
    expect(entries[1]).toMatchObject({ english: 'think about', chinese: '思考' })
  })

  it('单条短语无中文时 chinese 为空', () => {
    expect(splitPhraseEntry('be able to do')).toMatchObject({
      english: 'be able to do',
      chinese: '',
    })
  })

  it('空值返回空数组', () => {
    expect(parsePhrases(null)).toEqual([])
    expect(parsePhrases('')).toEqual([])
    expect(parsePhrases('   ')).toEqual([])
  })

  it('忽略空片段并保留原始文本', () => {
    const entries = parsePhrases('go across 穿过；；')
    expect(entries).toHaveLength(1)
    expect(entries[0].raw).toBe('go across 穿过')
  })
})
