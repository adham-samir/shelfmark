import Link from "next/link";

export default function NotFound() {
  return (
    <main className="page page-narrow" id="main">
      <div className="state" data-tone="warn">
        <h2 lang="ar" dir="rtl">الصفحة أو المنتج غير موجود</h2>
        <p lang="ar" dir="rtl">
          قد يكون العنصر مسودة أو مؤرشفًا، أو أن الرابط غير صحيح.
        </p>
        <p lang="en" dir="ltr">The page or product does not exist. It may be a draft, archived, or the link is wrong.</p>
        <div className="actions">
          <Link className="btn" href="/">
            <span lang="ar" dir="rtl">العودة إلى الكتالوج</span>
          </Link>
        </div>
      </div>
    </main>
  );
}
