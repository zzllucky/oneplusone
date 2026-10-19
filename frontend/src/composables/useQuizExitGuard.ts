/**
 * useQuizExitGuard — 答题进行中离开守卫（三页共用，自包含、零依赖）
 *
 * 职责：判定是否处于答题中，若是则拦截离开并暂存目标路由；
 * 把最终决定（继续 / 离开）交回调用方，由调用方决定弹窗与跳转。
 *
 * 用法（在答题页 setup 中）：
 *   const { pending, confirmLeave, cancelLeave } = useQuizExitGuard({
 *     isActive: () => questions.value.length > 0 && !report.value,
 *   })
 *
 *   <ConfirmDialog
 *     :open="pending !== null"
 *     title="离开测验？"
 *     message="离开后本轮测验不会保留，确定离开吗？"
 *     confirm-text="离开"
 *     cancel-text="继续答题"
 *     @confirm="confirmLeave"
 *     @cancel="cancelLeave"
 *   />
 *
 * 行为契约见 specs/005-quiz-mis-tap-guard/contracts/ui-guard.md §2
 */
import { ref, type Ref } from 'vue'
import { onBeforeRouteLeave, useRouter } from 'vue-router'

export interface UseQuizExitGuardOptions {
  /** 是否处于"答题进行中"，由调用方根据页面状态计算 */
  isActive: () => boolean
}

export interface UseQuizExitGuardResult {
  /** 待定目标路由 fullPath；为 null 时无需弹窗 */
  pending: Readonly<Ref<string | null>>
  /** 确认离开：跳到 pending 并清空；no-op if pending is null */
  confirmLeave: () => Promise<void>
  /** 继续答题：清空 pending，停留在当前页 */
  cancelLeave: () => void
}

export function useQuizExitGuard(options: UseQuizExitGuardOptions): UseQuizExitGuardResult {
  const router = useRouter()
  const pending = ref<string | null>(null)

  onBeforeRouteLeave((to) => {
    if (!options.isActive()) return true
    // confirmLeave 主动 push 时会重走此守卫：以 pending 是否等于目标识别为"已确认放行"
    if (pending.value === to.fullPath) {
      pending.value = null
      return true
    }
    if (pending.value === null) {
      pending.value = to.fullPath
    }
    return false
  })

  function cancelLeave(): void {
    pending.value = null
  }

  async function confirmLeave(): Promise<void> {
    const target = pending.value
    if (target === null) return
    // 不预先清空 pending：守卫以 pending === to.fullPath 识别为确认放行
    await router.push(target)
  }

  return { pending, confirmLeave, cancelLeave }
}
