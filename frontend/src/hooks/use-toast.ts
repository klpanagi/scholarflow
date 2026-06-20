import { toast as sonnerToast } from "sonner"

type ToastOptions = {
  title?: string
  description?: string
  variant?: "default" | "destructive"
}

function toast(opts: ToastOptions) {
  const { title, description, variant } = opts
  if (variant === "destructive") {
    sonnerToast.error(title ?? "Error", {
      description,
    })
  } else {
    sonnerToast(title ?? "", {
      description,
    })
  }
}

function useToast() {
  return {
    toast,
    toasts: [] as never[],
    dismiss: () => {},
  }
}

export { useToast, toast }
