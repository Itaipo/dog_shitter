"""מעבד את תמונות ה-GPT המקוריות (assets/source/*_original.png) לנכסים קלים לדף.

מה הוא עושה: חותך לתוחם, מסיר הילות שנאפו בשקיפות (glow), מפצל זוגות כפתורים,
מנקה את המיכל, מפרק את הידית לצלחת + כדור, ושומר WebP עם שקיפות.
הרצה:  python tools/process_assets.py   (נדרש: pillow, numpy)
"""
import json, os
import numpy as np
from PIL import Image, ImageFilter

SRC = 'assets/source/'
OUT = 'assets/'
sizes = {}


def load(name):
    return Image.open(SRC + name + '_original.png').convert('RGBA')


def clean_alpha(im, lo, hi, blur=0.8):
    """מסיר שקיפות חלשה (הילה): alpha<lo -> 0, alpha>hi -> 255, ביניהם רמפה רכה."""
    a = im.split()[3].filter(ImageFilter.GaussianBlur(blur))
    arr = np.array(a).astype('float32')
    arr = np.clip((arr - lo) / float(hi - lo), 0, 1) * 255
    out = im.copy()
    out.putalpha(Image.fromarray(arr.astype('uint8')))
    return out


def bbox(im, thr=8):
    a = np.array(im.split()[3])
    ys, xs = np.where(a > thr)
    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1


def crop_resize(im, box, width, margin=0):
    l, t, r, b = box
    l, t = max(0, l - margin), max(0, t - margin)
    r, b = min(im.width, r + margin), min(im.height, b + margin)
    c = im.crop((l, t, r, b))
    h = round(c.height * width / c.width)
    return c.resize((width, h), Image.LANCZOS)


def save(im, name, q=88):
    path = OUT + name + '.webp'
    im.save(path, 'WEBP', quality=q, method=6)
    sizes[name] = [im.width, im.height]
    print(f'{name:16s} {im.width}x{im.height}  {os.path.getsize(path)//1024} KB')


# --- מעטפת ---
sh = load('shell'); save(crop_resize(sh, bbox(sh, 20), 783), 'shell', 92)

# --- שמע ---
for n in ('audio_off', 'audio_on'):
    im = load(n); save(crop_resize(im, bbox(im, 20), 384, 6), n)

# --- פלוס/מינוס: מפצלים שני כפתורים ---
for n, gaps in (('pm_up', 646), ('pm_down', 643)):
    im = load(n); a = np.array(im.split()[3])
    for label, (y0, y1) in (('plus', (0, gaps)), ('minus', (gaps, im.height))):
        part = im.crop((0, y0, im.width, y1))
        save(crop_resize(part, bbox(part, 30), 256, 4), f'{n.replace("pm", label)}')

# --- נורת חוטם: מורידים את ההילה הצרובה; הזוהר ייעשה ב-CSS ---
off = load('lamp_off'); on = clean_alpha(load('lamp_on'), 235, 252)
boff = bbox(clean_alpha(off, 200, 250), 20)
save(crop_resize(off, boff, 480, 4), 'lamp_off')
bon = bbox(on, 20)
print('lamp bbox off', boff, 'on', bon)
save(crop_resize(on, bon, 480, 4), 'lamp_on')

# --- מיכל זכוכית: מנקים שאריות "משבצות שקיפות" מעל המכסה ובתוך הזכוכית ---
tk = load('tank'); arr = np.array(tk)
arr[:58, :, 3] = 0                              # שאריות מעל המכסה
arr[172:505, 258:1738, 3] = 0                   # פנים המיכל — שקוף לגמרי
tk = Image.fromarray(arr)
save(crop_resize(tk, bbox(tk, 20), 1000), 'tank')

# --- ידית: צלחת מלבנית (בלי כדור ובלי מוט) + כדור אדום בנפרד ---
lv = load('lever_top'); la = np.array(lv)
PX0, PY0, PX1, PY1 = 382, 294, 643, 1452              # תוחם הצלחת בתמונה המקורית (נמדד)
pa = la[PY0:PY1, PX0:PX1, :].copy(); ph, pw = pa.shape[:2]
# 1) הכדור כיסה את הקצה העליון: ממלאים בפלדה נקייה מתחתיו, ומציירים קו הבהק דק לקצה
top_edge_col = pa[2, 6, :3].copy()
pa[0:30, 10:pw - 10, :] = pa[34:64, 10:pw - 10, :]
pa[1:4, 10:pw - 10, :3] = np.clip(top_edge_col.astype(int) + 30, 0, 255).astype('uint8')
pa[0, 10:pw - 10, :3] = (top_edge_col * 0.45).astype('uint8')
# 2) מוחקים את מוט הכרום: פלדה מעל החריץ (מועתקת מימין לחריץ), וחריץ כהה בתוכו (מועתק מלמטה)
SX0, SX1 = 84, 160
SLOT_TOP = 405 - PY0
pa[30:SLOT_TOP, SX0:SX1, :] = pa[30:SLOT_TOP, SX0 + 92:SX1 + 92, :]
pa[SLOT_TOP:SLOT_TOP + 140, 70:176, :] = pa[SLOT_TOP + 300:SLOT_TOP + 440, 70:176, :]
# 3) אלפא: מלבן מעוגל מלא (מסיר את ההילה והכתמים החצי-שקופים)
mask = Image.new('L', (pw * 4, ph * 4), 0)
from PIL import ImageDraw
ImageDraw.Draw(mask).rounded_rectangle((0, 0, pw * 4 - 1, ph * 4 - 1), radius=24 * 4, fill=255)
mask = mask.resize((pw, ph), Image.LANCZOS)
plate_img = Image.fromarray(pa); plate_img.putalpha(mask)
w_out = 320; scale = w_out / pw
save(plate_img.resize((w_out, round(ph * scale)), Image.LANCZOS), 'lever_plate')
# מיקום החריץ (שבר מגובה הצלחת) למסלול הכדור — נמדד על התמונה המקורית (חריץ 410..1330 מתוך צלחת 294..1452)
sizes['lever_geom'] = {'slotTop': (410 - PY0) / ph, 'slotBot': (1330 - PY0) / ph, 'slotX': 0.5}
# הכדור: אליפסה לפי תוחם הפיקסלים האדומים (מוציא גם את הברק הלבן שבתוכו)
R, G, B, AL = la[:, :, 0].astype(int), la[:, :, 1].astype(int), la[:, :, 2].astype(int), la[:, :, 3]
red = (R > 140) & (G < 80) & (B < 80) & (AL > 200)
ys, xs = np.where(red[:320]); bx0, by0, bx1, by1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
bw, bh = bx1 - bx0, by1 - by0
bm = Image.new('L', (bw * 4, bh * 4), 0); ImageDraw.Draw(bm).ellipse((4, 4, bw * 4 - 5, bh * 4 - 5), fill=255)
bm = bm.resize((bw, bh), Image.LANCZOS)
ball = Image.fromarray(la[by0:by1, bx0:bx1, :]); ball.putalpha(bm)
save(ball.resize((200, round(bh * 200 / bw)), Image.LANCZOS), 'lever_ball')
sizes['lever_ball_to_plate'] = bw / pw                  # יחס רוחב כדור לרוחב צלחת

# --- כלבלב: מסירים הילה, חותכים, ובאותו קנה מידה (0.45 מהמקור) ---
SC = 0.45
for n in ('dog_stand', 'dog_sit', 'dog_sit_happy', 'dog_sleep'):
    im = clean_alpha(load(n), 215, 250, 1.2)
    l, t, r, b = bbox(im, 30)
    c = im.crop((l, t, r, b)); c = c.resize((round(c.width * SC), round(c.height * SC)), Image.LANCZOS)
    save(c, n, 86)

json.dump(sizes, open(OUT + 'sizes.json', 'w'))
