# Manual review before sign-off

Two things the automated gates cannot decide: whether the Arabic reads like
Arabic to a native speaker, and whether the interface works for someone using a
screen reader. Both are recorded here so the outstanding work has an owner and a
definition of done rather than a vague "review later".

The automated evidence — axe-core on 46 pages in two engines, the 136-page
capture, the token-contrast gate, and the rendering budget — is in
[`../test-report.md`](../test-report.md).

## 1. Assistive-technology walkthrough

Nothing below has been run. The axe gate proves the markup exposes the right
roles, names, and states; it does not prove the experience is usable.

### Setup

- One desktop screen reader: NVDA with Firefox on Windows, or VoiceOver with
  Safari on macOS. Do not test with Chromium plus a screen reader alone.
- One mobile screen reader: VoiceOver on iOS, or TalkBack on Android.
- The local stack from `docs/user-manual.md`, seeded with the demo accounts.
- Arabic as the default locale, then repeat the first three checks in English.

### Checks

| # | Check | Passes when |
|---|---|---|
| 1 | Land on `/` and read the first screen | The language and direction are announced as Arabic RTL; the brand, search, and cart are reachable in a sensible order; the skip link is the first stop and moves focus to `<main>`. |
| 2 | Tab through the header | Every control announces its name, role, and state; the cart count is announced once, not twice; the locale switch says which language is active. |
| 3 | Tab through the catalog filter rail | Each facet announces as a group with its name; a collapsed facet says collapsed and expands with Enter or Space; the active filter count is announced when it changes. |
| 4 | Select two products, then open the compare dock | The dock appears at one selection and is announced; the drawer traps focus, Escape closes it and returns focus to the control that opened it; the selection count updates audibly. |
| 5 | Reach `/compare` with one product selected | The page renders a single column without an empty second column, and the heading says how many products are being compared. |
| 6 | Add to cart, then change quantity | The live region announces the new quantity and the new line total; the remove control's name contains the product name. |
| 7 | Complete checkout to the review step | Each field's error is announced when it appears and is tied to the field; the summary is announced as a list, not a run-on sentence. |
| 8 | In the back office, move through the rail | The active page is announced as current; the grouped headings are announced as headings; focus on the dark rail stays visible (the ring switches to the lighter step). |
| 9 | On `/backoffice/risk`, read a review row | The localised reason sentence is read first and the machine identifier is read as a separate reference; the allow/decline control announces the order it applies to. |
| 10 | On `/backoffice/inventory`, adjust stock | The status column and the adjust control are reachable without horizontal scrolling at 1024 px; the confirmation is announced. |
| 11 | Turn on "reduce motion" and reload `/` | No entrance animation plays, the compare dock still appears, and nothing is invisible because its animation was suppressed. |
| 12 | Zoom to 200% at 1280 px wide | No content is clipped, no horizontal scrollbar appears on the page body, and tables remain usable (their own scroll region is acceptable). |
| 13 | Repeat 1–5 in English | The same order and the same announcements, with `dir="ltr"` and no mirrored icons that should not mirror (play, chevron, media). |

Record the outcome as a row per check with the screen reader, browser, and
version, plus a link to any recording. A failure becomes an issue against
`apps/storefront`, not a note in this file.

## 2. New Arabic strings for native review

These 43 strings were added during the UI overhaul and have not been read by a
native speaker. Placeholders in braces are substituted at render time and must
survive translation. Egyptian consumer-electronics register is intended: plain
Modern Standard Arabic, no dialect, no marketing superlatives.

| Key | Arabic (as shipped) | English (reference) |
|---|---|---|
| `filters.priceAny` | بلا حد | No limit |
| `filters.searchWithin` | ابحث في {group} | Search {group} |
| `filters.searchNone` | لا خيارات مطابقة | No matching options |
| `compare.selectedCount` | {count} من {limit} محدد للمقارنة | {count} of {limit} selected to compare |
| `compare.compare` | قارن | Compare |
| `compare.hide` | إخفاء | Hide |
| `unit.hours` | {value} ساعة | {value} h |
| `unit.inches` | {value} بوصة | {value} in |
| `value.notApplicable` | لا ينطبق | Not applicable |
| `cart.summary` | ملخص الطلب | Order summary |
| `shipment.statusPending` | قيد التجهيز | Pending |
| `shipment.statusReady` | جاهزة للشحن | Ready to ship |
| `shipment.statusInTransit` | في الطريق | In transit |
| `shipment.statusDelivered` | مسلَّمة | Delivered |
| `shipment.statusException` | استثناء | Exception |
| `assistant.emptyHint` | اختر سؤالًا جاهزًا أو اكتب سؤالك بالعربية أو الإنجليزية. | Pick a ready question or write your own in Arabic or English. |
| `inventory.supplierAck` | أقرّها محاكي المورد الاصطناعي. | Acknowledged by the synthetic supplier simulator. |
| `pricing.detail.missing` | لا توجد ملاحظة تسعير مسجلة. | No pricing observation is recorded. |
| `pricing.detail.future` | وقت رصد الملاحظة في المستقبل. | The observation timestamp is in the future. |
| `pricing.detail.stale` | الملاحظة أقدم من حد الحداثة البالغ ٢٤ ساعة. | The observation is older than the 24-hour freshness limit. |
| `pricing.detail.floorExceeds` | حد التكلفة المسجلة يتجاوز أقصى زيادة مسموح بها. | The recorded cost floor exceeds the maximum permitted increase. |
| `pricing.detail.floorRaised` | رفع حد التكلفة المسجلة السعر المقترح. | The recorded cost floor raised the proposed price. |
| `pricing.detail.floorCap` | تعذّر تحقيق حد التكلفة وسقف التغيير معًا. | The cost floor and the change cap cannot both be satisfied. |
| `pricing.detail.equal` | السعر المحتسب يساوي السعر الحالي. | The calculated price equals the current price. |
| `pricing.detail.already` | أنتجت هذه الملاحظة تغيير سعر بالفعل. | This observation has already produced a price change. |
| `pricing.detail.conflict` | غيّر كاتب آخر السعر أولًا؛ فتركه التشغيل دون تغيير. | Another writer changed the price first; the run left it untouched. |
| `risk.reason.amountAboveNorm` | المبلغ يعادل ثلاثة أضعاف معتاد العميل أو أكثر | Amount is three times the customer's norm or more |
| `risk.reason.orderVelocity` | ثلاثة طلبات أو أكثر خلال ٢٤ ساعة | Three or more orders within 24 hours |
| `risk.reason.priorFailures` | محاولتا دفع فاشلتان أو أكثر سابقًا | Two or more prior failed payment attempts |
| `risk.reason.newAddress` | عنوان شحن جديد لعميل لديه طلبات سابقة | New shipping address for a returning customer |
| `risk.reason.tokenReuse` | إعادة استخدام رمز الدفع | Payment token reused |
| `risk.reason.unusualHour` | طلب في ساعة غير معتادة (قبل السادسة صباحًا) | Order placed at an unusual hour (before 06:00) |
| `risk.reason.firstOrder` | أول طلب للعميل | Customer's first order |
| `risk.reason.modelUnavailable` | تقييم المخاطر غير متاح | Risk assessment unavailable |
| `risk.reason.scoreAbove` | درجة النموذج بلغت حد المراجعة أو تجاوزته | Model score at or above the review threshold |
| `risk.reason.scoreBelow` | درجة النموذج دون حد المراجعة | Model score below the review threshold |
| `admin.groupOverview` | نظرة عامة | Overview |
| `admin.groupOperations` | العمليات | Operations |
| `admin.groupIntelligence` | التحليلات الذكية | Intelligence |
| `common.footerNav` | روابط التذييل | Footer links |
| `common.listSep` | ، | , |
| `common.breadcrumb` | مسار التنقل | Breadcrumb |
| `product.specsOther` | تفاصيل أخرى | Other details |

### What to look for

1. **Register.** Does each sentence sound like a shop or an operations tool, not
   a literal translation of the English?
2. **Numbers.** `٢٤` and `٢٠٧٩٨٦`-style amounts are rendered with Latin digits
   elsewhere in the product. Flag any place where Arabic-Indic and Latin digits
   appear in the same sentence without a reason.
3. **Placeholders.** `{count}`, `{limit}`, `{value}`, `{group}` must stay intact
   and stay in a position that reads naturally after substitution.
4. **Bidi.** The risk identifiers, order IDs, and prices are isolated with
   Unicode marks. Check that a reason sentence followed by its identifier does
   not reorder on screen.
5. **Brevity.** The back-office table columns are narrow; a string that grows by
   more than about 20% may wrap the row. `risk.reason.unusualHour` and
   `pricing.detail.conflict` are the longest.

## Sign-off

| Item | Owner | Date | Outcome |
|---|---|---|---|
| Screen-reader walkthrough (13 checks) | | | |
| Arabic review (43 strings) | | | |

Until both rows have a name and a date, the interface is verified by automation
only, and `docs/test-report.md` continues to list manual accessibility as a
declared gap.
