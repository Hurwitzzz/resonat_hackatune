import Plus from "./icons/Plus";

interface ControlsProps {
  onAdd: () => void;
}

const Controls = ({ onAdd }: ControlsProps) => {
  return (
    <div className="fixed left-4 top-1/2 z-[10000] -translate-y-1/2 rounded-full bg-[#35363e] p-2 shadow-lg">
      <button
        type="button"
        onClick={onAdd}
        aria-label="Add a note"
        title="Add a note"
        className="flex h-10 w-10 items-center justify-center rounded-full bg-[#212228] text-white/90 transition-transform duration-300 hover:scale-110 hover:text-white"
      >
        <Plus size={22} />
      </button>
    </div>
  );
};

export default Controls;
