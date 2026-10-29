export default function AnalyticsLoading() {
  return (
    <main className="page inventory-page" id="main" aria-busy="true">
      <div className="inventory-command">
        <div style={{ width: "min(620px, 100%)" }}>
          <div className="skeleton" style={{ width: 150, height: 12 }} />
          <div className="skeleton" style={{ width: 300, height: 28, marginBlock: 12 }} />
          <div className="skeleton" style={{ width: "100%", height: 14 }} />
        </div>
      </div>
      <div className="analytics-grid" aria-hidden="true">
        {Array.from({ length: 2 }).map((_, index) => (
          <div className="skeleton" key={index} style={{ height: 220 }} />
        ))}
      </div>
      <div className="skeleton" style={{ height: 160, marginBlockStart: 16 }} />
      <div className="skeleton" style={{ height: 320, marginBlockStart: 16 }} />
    </main>
  );
}