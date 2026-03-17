"""
Skill: compare_modal_react
Description: Multi-listing side-by-side comparison modal pattern for React/Tailwind.

Key patterns:
1. winnerIndex(values, direction) — finds best value index for highlighting
2. CompareRow — renders a labeled row with one cell per listing, highlights winner
3. Dynamic grid columns via inline style (Tailwind can't do runtime grid-cols-N)
4. Floating compare bar with max-3 enforcement
5. Jest mock pattern for the modal

Usage:
- Copy CompareModal.jsx pattern, adjust fields to your data model
- Pass `listings` (2-3 objects) and `onClose` callback
- In parent: `compareListings` state array, `isComparing(l)` / `toggleCompare(l)` functions
- Show floating bar when compareListings.length >= 2 and !showCompare

--- WINNER INDEX ---

def winnerIndex(values, direction='max'):
    valid = [(v, i) for i, v in enumerate(values) if v is not None]
    if len(valid) < 2:
        return -1
    return max(valid, key=lambda x: x[0] if direction == 'max' else -x[0])[1]

--- DYNAMIC GRID (JSX) ---

<div style={{ gridTemplateColumns: `140px repeat(${n}, 1fr)` }}>

--- FLOATING COMPARE BAR ---

{compareListings.length >= 2 && !showCompare && (
  <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 flex items-center gap-3 px-5 py-3 bg-card border border-blue-500/40 rounded-full shadow-xl">
    <span>{compareListings.length} listings selected</span>
    <Button onClick={() => setShowCompare(true)}>Compare</Button>
    <button onClick={() => setCompareListings([])}><X /></button>
  </div>
)}

--- JEST MOCK ---

jest.mock('@/components/shared/CompareModal', () => () => null);

--- MAX 3 ENFORCEMENT ---

const toggleCompare = (l) => {
  setCompareListings(prev => {
    if (prev.some(c => key(c) === key(l))) return prev.filter(c => key(c) !== key(l));
    if (prev.length >= 3) return prev; // max 3 — silently ignore
    return [...prev, l];
  });
};
"""
