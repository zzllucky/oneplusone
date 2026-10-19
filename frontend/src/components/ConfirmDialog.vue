<script setup lang="ts">
/**
 * ConfirmDialog — 通用确认弹窗（自包含、零依赖）
 *
 * 职责：展示一段提示与两个按钮，把用户选择回传给调用方。
 * 不做任何业务判断、不读取 store、不发起网络请求。
 *
 * 用法：
 *   <ConfirmDialog
 *     :open="show"
 *     title="离开测验？"
 *     message="离开后本轮测验不会保留，确定离开吗？"
 *     cancel-text="继续答题"
 *     confirm-text="离开"
 *     @confirm="onConfirm"
 *     @cancel="onCancel"
 *   />
 *
 * 行为契约见 specs/005-quiz-mis-tap-guard/contracts/ui-guard.md §1
 */
defineProps<{
  open: boolean
  title: string
  message: string
  confirmText: string
  cancelText: string
}>()
const emit = defineEmits<{ (e: 'confirm'): void; (e: 'cancel'): void }>()
</script>

<template>
  <div
    v-if="open"
    role="dialog"
    aria-modal="true"
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
  >
    <div class="card w-full max-w-sm flex flex-col gap-3">
      <h3 class="text-lg font-bold text-gray-900">{{ title }}</h3>
      <p class="text-sm text-gray-700">{{ message }}</p>
      <div class="flex flex-wrap gap-2 pt-1">
        <button
          class="btn-primary min-h-[44px] flex-1"
          type="button"
          @click="emit('cancel')"
        >
          {{ cancelText }}
        </button>
        <button
          class="btn-ghost min-h-[44px] flex-1"
          type="button"
          @click="emit('confirm')"
        >
          {{ confirmText }}
        </button>
      </div>
    </div>
  </div>
</template>
