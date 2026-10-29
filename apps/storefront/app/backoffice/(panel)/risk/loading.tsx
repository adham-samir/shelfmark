export default function RiskLoading() {
  return (
    <main className="page inventory-page" id="main" aria-busy="true">
      <div className="inventory-command">
        <div style={{ width: "min(620px, 100%)" }}>
          <div className="skeleton" style={{ width: 150, height: 12 }} />
          <div className="skeleton" style={{ width: 300, height: 28, marginBlock: 12 }} />
          <div className="skeleton" style={{ width: "100%", height: 14 }} />
        </div>
      </div>
      <div className="inventory-ledger" aria-hidden="true">
        {Array.from({ length: 4 }).map((_, index) => (
          <div key={index}>
            <span className="skeleton" style={{ width: 80, height: 28 }} />
          </div>
        ))}
      </div>
      <div className="inventory-sheet" aria-hidden="true">
        <div className="skeleton" style={{ height: 420 }} />
      </div>
    </main>
  );
}