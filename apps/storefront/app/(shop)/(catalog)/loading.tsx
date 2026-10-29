import { SkeletonGrid } from "@/components/states";

export default function Loading() {
  return (
    <main className="workbench" aria-busy="true" aria-live="polite">
      <aside className="rail" aria-hidden="true">
        <div className="skeleton" style={{ height: 220, marginBlockEnd: 12 }} />
        <div className="skeleton" style={{ height: 260 }} />
      </aside>
      <section className="field-column">
        <div className="skeleton" style={{ height: 22, width: "40%", marginBlock: "10px 16px" }} />
        <SkeletonGrid count={8} />
      </section>
    </main>
  );
}
