interface ChatHeaderProps {
  onOpenSettings: () => void;
  onClearHistory: () => void;
}

export function ChatHeader({ onOpenSettings, onClearHistory }: ChatHeaderProps) {
  return (
    <header className="mb-2 flex items-center justify-between sm:mb-4">
      <div className="flex items-center">
        <h1 className="text-base font-semibold sm:text-lg">Alyn 🌴</h1>
      </div>
      <div className="flex items-center gap-1.5 sm:gap-2">
        <button
          className="rounded-md border border-gray-200 px-2 py-1.5 text-xs hover:bg-gray-50 sm:px-3 sm:py-2 sm:text-sm"
          onClick={onOpenSettings}
        >
          Settings
        </button>
        <button
          className="rounded-md border border-gray-200 px-2 py-1.5 text-xs hover:bg-gray-50 sm:px-3 sm:py-2 sm:text-sm"
          onClick={onClearHistory}
        >
          Clear
        </button>
      </div>
    </header>
  );
}
