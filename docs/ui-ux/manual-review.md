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
survive translation. The product reads in plain Modern Standard Arabic — no
dialect, no marketing superlatives. The assistant surface is the deliberate
exception and is listed separately in 2b.

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
| `assistant.emptyHint` | اختار سؤال من دول أو اكتب سؤالك براحتك. | Pick one of these, or just type your question. (assistant surface — Egyptian colloquial, see 2b) |
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

### 2b. Assistant and voice surface (added or rewritten since the UI overhaul)

The assistant was rebuilt after the overhaul — it gained a name, a warmer
voice, conversation memory, an order picker, and a live transcript path — and
the voice surface gained its rejected-recording state. None of these have been
read by a native speaker yet. **Egyptian colloquial is intentional here**; the
rest of the product stays Modern Standard Arabic. Placeholders in braces are
substituted at render time and must survive translation.

#### Assistant

| Key | Arabic (as shipped) | English (reference) |
|---|---|---|
| `assistant.assistant` | نور | Nour |
| `assistant.disclaimer` | بجاوب من بيانات المتجر، وبيانات طلبات باقي العملاء محمية. ولو حاجة مش متوفرة هقولك بصراحة. | I answer from store data, and other customers' orders stay private. If something isn't available, I'll say so. |
| `assistant.failed` | حصلت مشكلة بسيطة | Something went wrong |
| `assistant.failedHint` | جرّب تاني بعد لحظات، ولو المشكلة كمّلت كلّم الدعم. | Give it another try in a moment; if it keeps happening, contact support. |
| `assistant.intro` | أهلاً! أنا نور، مساعدة المتجر. اسألني عن أي منتج، أو التوصيل والاسترجاع، أو اطلب حالة طلب من طلباتك. | Hi! I'm Nour, your shop assistant. Ask me about any product, delivery and returns, or the status of your orders. |
| `assistant.orderAskCancel` | أقدر ألغيه؟ | Can I cancel it? |
| `assistant.orderAskItems` | إيه اللي في الطلب ده؟ | What's in this order? |
| `assistant.orderAskStatus` | وصل فين؟ | Where is it? |
| `assistant.orderAttach` | اسأل عن الطلب | Ask about this order |
| `assistant.orderAttached` | بتسأل عن طلب {id} | Asking about {id} |
| `assistant.orderDetach` | إزالة الطلب | Remove order |
| `assistant.orderEmpty` | لسه مفيش طلبات في حسابك. | You don't have any orders yet. |
| `assistant.orderPanel` | اسأل عن طلب معيّن | Ask about an order |
| `assistant.orderViewAll` | كل الطلبات | All orders |
| `assistant.placeholder` | اكتب سؤالك… مثلاً: عايز سماعات في حدود ٢٠٠٠ جنيه | Type your question… e.g. headphones under EGP 2,000 |
| `assistant.providerMissing` | المساعد مش متاح دلوقتي | The assistant is unavailable right now |
| `assistant.providerMissingHint` | مش قادر أرد دلوقتي، جرّب تاني بعد شويّة. | I can't reply at the moment — please try again in a little while. |
| `assistant.send` | إرسال | Send |
| `assistant.sending` | ثانية واحدة… | Sending… |
| `assistant.sourceFaq` | سؤال شائع | Common question |
| `assistant.sourceProduct` | منتج | Product |
| `assistant.sourceShipment` | طلبك | Your order |
| `assistant.sources` | معلومات ذات صلة | Related info |
| `assistant.suggestionOne` | إيه سياسة الاسترجاع؟ | What's your return policy? |
| `assistant.suggestionThree` | إيه الطلبات اللي عندي؟ | What orders do I have? |
| `assistant.suggestionTwo` | عايز موبايل كاميرته حلوة | I want a phone with a good camera |
| `assistant.suggestions` | تقدر تسألني مثلاً | You can ask me things like |
| `assistant.title` | نور | Nour |
| `assistant.you` | أنت | You |

#### Voice search

| Key | Arabic (as shipped) | English (reference) |
|---|---|---|
| `voice.denied` | تم رفض إذن الميكروفون | Microphone permission denied |
| `voice.deniedHint` | اسمح بالوصول من إعدادات المتصفح، أو استخدم البحث النصي. | Allow access in the browser settings, or use text search. |
| `voice.empty` | لم يُسمع أي كلام | No speech detected |
| `voice.emptyHint` | أعد التسجيل بصوت أوضح أو اكتب البحث. | Record again more clearly or type the search. |
| `voice.failed` | تعذر إكمال البحث الصوتي | The voice search could not be completed |
| `voice.intro` | اضغط للتسجيل ثم اسمع/راجع النص قبل البحث. يبقى البحث النصي متاحًا دائمًا. | Press to record, then review the transcript before searching. Text search stays available. |
| `voice.noResults` | لم تُعثر نتائج للنص المُستخرج | No results for the transcript |
| `voice.processing` | جارٍ التحويل… | Transcribing… |
| `voice.providerMissing` | التحويل الصوتي مش متاح دلوقتي | Transcription isn't available right now |
| `voice.providerMissingHint` | مش قادر أسمع التسجيل دلوقتي، جرّب تاني بعد شويّة. | I can't transcribe that at the moment — please try again in a little while. |
| `voice.recording` | جارٍ التسجيل… | Recording… |
| `voice.rejected` | تعذر استخدام هذا التسجيل | That recording could not be used |
| `voice.rejectedHint` | جرّب التسجيل مرة أخرى، أو استخدم البحث النصي. | Try recording again, or use text search. |
| `voice.rerecord` | إعادة التسجيل | Record again |
| `voice.searchTranscript` | ابحث بهذا النص | Search this transcript |
| `voice.seconds` | {seconds} ثانية | {seconds} seconds |
| `voice.start` | بدء التسجيل | Start recording |
| `voice.stop` | إيقاف التسجيل | Stop recording |
| `voice.textFallback` | اكتب البحث بدلًا من الصوت | Type the search instead |
| `voice.title` | البحث بالصوت | Search by voice |
| `voice.transcript` | النص المُستخرج (قابل للتعديل) | Transcript (editable) |
| `voice.unsupported` | المتصفح لا يدعم تسجيل الصوت | This browser cannot record audio |
| `voice.unsupportedHint` | استخدم البحث النصي أو متصفحًا يدعم MediaRecorder. | Use text search or a browser that supports MediaRecorder. |

#### New attribute labels

| Key | Arabic (as shipped) | English (reference) |
|---|---|---|
| `attr.camera` | الكاميرا | Camera |
| `attr.os` | نظام التشغيل | Operating system |
| `attr.gpu` | كرت الرسومات | Graphics |
| `attr.weight` | الوزن | Weight |
| `attr.refresh_rate` | معدل تحديث الشاشة | Refresh rate |
| `attr.microphone` | الميكروفون | Microphone |
| `attr.drivers` | مكبرات الصوت | Drivers |

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
| Arabic review (43 strings + the assistant and voice surface) | | | |

Until both rows have a name and a date, the interface is verified by automation
only, and `docs/test-report.md` continues to list manual accessibility as a
declared gap.
