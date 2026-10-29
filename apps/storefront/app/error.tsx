"use client";

export default function Error({ reset }: { error: Error; reset: () => void }) {
  return (
    <main className="page page-narrow" id="main">
      <div className="state" data-tone="error" role="alert">
        <h2>Something went wrong · حدث خطأ غير متوقع</h2>
        <p>
          The page could not be rendered. No substitute data was shown. · تعذر عرض الصفحة، ولم
          تُعرض بيانات بديلة.
        </p>
        <div className="actions">
          <button type="button" className="btn" onClick={reset}>
            Retry · إعادة المحاولة
          </button>
        </div>
      </div>
    </main>
  );
}
