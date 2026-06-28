interface AddNoteButtonProps {
  onClick: () => void;
}

// Secondary memo affordance.
const AddNoteButton = ({ onClick }: AddNoteButtonProps) => (
  <button
    type="button"
    onClick={onClick}
    aria-label="Add a memo"
    title="Add a memo"
    className="font-sans flex h-[130px] w-[130px] items-center justify-center rounded-[10px] border-[2.5px] border-dashed border-[rgba(229,225,214,.62)] bg-transparent px-3 text-center text-[18px] font-semibold uppercase leading-none text-[var(--paper)] transition duration-150 hover:border-[var(--yellow)] hover:text-[var(--yellow)] focus-visible:border-[var(--yellow)] focus-visible:text-[var(--yellow)] focus-visible:outline-none"
  >
    Add memo
  </button>
);

export default AddNoteButton;
