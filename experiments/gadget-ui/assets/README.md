# נכסי ממשק (GPT image) — מה יש, מה חסר, ומה הפרומפט

תמונות ריאליסטיות לדף `../index.html`. נוצרו ב-GPT (תמונות) לפי הפרומפטים למטה. **לפני שימוש מסחרי/פרסום** יש לבדוק את תנאי השימוש בתמונות שנוצרו.

## כללים לכל נכס
רקע שקוף (PNG), מבט ישר מלפנים, אור ראשי מלמעלה-שמאל, צל רך רק מתחת לחפץ, בלי טקסט ובלי לוגואים, אותו סגנון חומרים. כל פריט בזוג מצבים (רגיל/לחוץ או כבוי/דולק) — בקשת המצב השני כעריכה של הראשון ("same object, but ...").

כותרת משותפת לפרומפטים:
`Photorealistic product render, front orthographic view, transparent background (PNG), soft studio lighting from the top-left, subtle soft shadow only beneath the object, high detail materials, no text, no logos, no background.`

## מצב הנכסים
| נכס | קובץ | מצב |
|---|---|---|
| כפתור האכלה — רגיל | `feed_up.webp` (מקור: `source/feed_up_original.png`) | ✅ נוצר ומשולב (2026-10-18). מצב לחוץ מדומה ב-CSS |
| כפתור האכלה — לחוץ | `feed_down.webp` | ⏳ חסר (אופציונלי, יחליף את סימולציית ה-CSS) |
| כפתור שמע (כבוי/דולק) | — | ⏳ חסר |
| פלוס/מינוס של השעון | — | ⏳ חסר |
| ידית משיכה (+ למטה) | — | ⏳ חסר |
| נורת חוטם (כבויה/דולקת) | — | ⏳ חסר |
| מעטפת המכשיר | — | ⏳ חסר (להתחיל ממנה כדי לקבוע סגנון) |
| מיכל זכוכית | — | ⏳ חסר |
| כלבלב (עומד/יושב/שמח/ישן) | — | ⏳ חסר |

## פרומפטים
**כפתור האכלה (נוצר):** `[כותרת] A large round arcade push-button seen from the front: translucent glossy hot-pink/red plastic dome with a soft inner glow and a sharp specular highlight, set in a knurled brushed-aluminium bezel ring with a dark inner gap. Square 1024x1024.` — לחוץ: `Same button, but pressed down: the dome sits lower in the bezel, highlight softer, less shadow.`

**כפתור שמע:** `[כותרת] A medium round metal push-button with a knurled rim and a slightly concave brushed-steel top, mounted in a dark ring with a thin LED ring around it, LED off (unlit).` — דולק: `Same, with the LED ring glowing bright lime green.`

**פלוס/מינוס:** `[כותרת] Two small oval chrome push-buttons stacked vertically, vintage car-clock style, tiny and polished, with an engraved plus sign on the top one and an engraved minus sign on the bottom one.` — לחוץ: `Same, pressed.`

**ידית:** `[כותרת] A vertical lever slot panel: brushed-chrome plate with a deep dark vertical slot, small tick-mark notches on both sides, a chrome shaft and a glossy red rubber ball grip at the top of the slot.` — למטה: `Same, with the grip pulled all the way down to the bottom of the slot.`

**נורת חוטם:** `[כותרת] A red indicator lamp shaped like a dog's nose: a chrome bezel in the shape of a dog nose with two nostril curves and a center groove, dark maroon translucent faceted lens, lamp OFF.` — דולקת: `Same, lamp ON: the lens glows intense red with a bright hot centre and a soft red halo.`

**מעטפת:** `[כותרת] The front plate of a rugged superhero gadget device: a purple armored plastic body with chamfered corners, a brushed-aluminium edge trim, subtle scratches, four screws in the corners, ridged side grips, a speaker grille at the top, and EMPTY rectangular cutouts left for a screen, a small counter window, a control panel and a bottom tank. Tall portrait 1024x2048.`

**מיכל:** `[כותרת] A small rectangular glass terrarium-style tank seen from the front: thick glass walls with real reflections and slight green edge tint, brushed-steel corner brackets with screws, a hazard-striped lid with a small hole at the top centre. Interior is EMPTY (transparent). Wide 1024x400.`

**כלבלב:** `[כותרת] A realistic small dog (brown and tan, floppy ears, wearing a red collar with a gold tag) standing, side view facing right, full body, paws visible.` — ואחריו: `same dog sitting`, `same dog, mouth open, tongue out, eyes closed (happy)`, `same dog sleeping curled up`.

## איך משלבים
תמונה → חיתוך לתוחם השקוף → 512px (WebP, כ-60KB) בתיקיית `assets/`; המקור נשמר ב-`source/`. הדף מוסיף מעליה נטייה והבהקים שזזים עם הטלפון וצל חי.
