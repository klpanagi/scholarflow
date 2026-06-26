import { Sidebar } from './Sidebar'
import { Sheet, SheetContent, SheetTitle } from '@/components/ui/sheet'

interface MobileSidebarProps {
  open: boolean
  onClose: () => void
}

export function MobileSidebar({ open, onClose }: MobileSidebarProps) {
  return (
    <Sheet open={open} onOpenChange={onClose}>
      <SheetContent
        side="left"
        className="w-[15.25rem] p-0 [&>button:last-child]:hidden"
      >
        <SheetTitle className="sr-only">Navigation menu</SheetTitle>
        <Sidebar />
      </SheetContent>
    </Sheet>
  )
}
