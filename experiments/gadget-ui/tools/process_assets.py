"""מעבד את תמונות ה-GPT המקוריות (assets/source/*_original.png) לנכסים קלים לדף.

מה הוא עושה: חותך לתוחם, מסיר רקע ירוק (chroma key) או הילות שנאפו בשקיפות, מפצל זוגות כפתורים,
מנקה את המיכל, מחשב נקודת עיגון לכלבלב (לפי הקולר האדום) ושומר WebP עם שקיפות + sizes.json.
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


def key_green(im, thr=60):
    """מסיר רקע ירוק אחיד (#00FF00) בעזרת מטינג: רק אזור שמחובר לשולי התמונה ובקרבת הקצה נחשב, כך
    שהשתקפויות ירוקות בתוך החפץ (כרום) לא הופכות לחורים. בקצוות מפרידים את הצבע מהרקע (unmix)."""
    a = np.array(im.convert('RGB')).astype('float32')
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    d = g - np.maximum(r, b)
    from scipy import ndimage
    lab, n = ndimage.label(d > thr)                                # רכיבי רקע; נשארים רק אלה שנוגעים בשולי התמונה
    edge = np.unique(np.concatenate([lab[0, :], lab[-1, :], lab[:, 0], lab[:, -1]])); edge = edge[edge > 0]
    region = np.isin(lab, edge)
    zone = ndimage.binary_dilation(region, iterations=3)
    t = np.clip(d / 255.0, 0, 1)
    alpha = np.where(zone, 1 - t, 1.0)
    alpha = np.where(region & (alpha < 0.06), 0.0, alpha)
    alpha = np.clip((alpha - 0.04) / 0.96, 0, 1)
    bgc = np.array([0.0, 255.0, 0.0])
    safe = np.maximum(alpha, 0.08)[..., None]
    fg = (a - (1 - alpha)[..., None] * bgc) / safe
    edge_px = zone & (alpha < 0.995)
    fg = np.where(edge_px[..., None], np.clip(fg, 0, 255), a)
    # ניקוי ירוק שיורי בקצוות: הירוק לא יעלה על שילוב של אדום וכחול (פרווה כתומה/חומה)
    fg[..., 1] = np.where(edge_px, np.minimum(fg[..., 1], 0.80 * fg[..., 0] + 0.10 * fg[..., 2]), fg[..., 1])
    alpha = np.array(Image.fromarray((alpha * 255).astype('uint8')).filter(ImageFilter.MinFilter(3))).astype('float32') / 255.0
    out = Image.fromarray(fg.astype('uint8'))
    al = Image.fromarray((alpha * 255).astype('uint8')).filter(ImageFilter.GaussianBlur(0.5))
    out = out.convert('RGBA'); out.putalpha(al)
    return out


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


def save(im, name, q=88, **extra):
    path = OUT + name + '.webp'
    im.save(path, 'WEBP', quality=q, method=6)
    sizes[name] = {'w': im.width, 'h': im.height, **extra}
    print(f'{name:16s} {im.width}x{im.height}  {os.path.getsize(path)//1024} KB')


def collar_anchor(im):
    """מרכז הקולר האדום כשבר מרוחב התמונה: נקודת עיגון קבועה לכלב בין תנוחות שונות."""
    a = np.array(im)
    r, g, b, al = a[..., 0].astype(int), a[..., 1].astype(int), a[..., 2].astype(int), a[..., 3]
    m = (r > 150) & (g < 70) & (b < 80) & (al > 200)
    xs = np.where(m)[1]
    return float(xs.mean() / im.width) if xs.size > 40 else 0.5


# --- מעטפת ---
sh = load('shell'); save(crop_resize(sh, bbox(sh, 20), 783), 'shell', 92)

# --- שמע: כבוי / דולק / לחוץ ---
for n in ('audio_off', 'audio_on'):
    im = load(n); save(crop_resize(im, bbox(im, 20), 384, 6), n)
ad = key_green(load('audio_down')); save(crop_resize(ad, bbox(ad, 20), 384, 6), 'audio_down')

# --- פלוס/מינוס: מפצלים שני כפתורים ---
for n, gap in (('pm_up', 646), ('pm_down', 643)):
    im = load(n)
    for label, (y0, y1) in (('plus', (0, gap)), ('minus', (gap, im.height))):
        part = im.crop((0, y0, im.width, y1))
        save(crop_resize(part, bbox(part, 30), 256, 4), n.replace('pm', label))

# --- נורת חוטם: מסירים את ההילה הצרובה; הזוהר נעשה ב-CSS ---
off = load('lamp_off'); on = clean_alpha(load('lamp_on'), 235, 252)
save(crop_resize(off, bbox(clean_alpha(off, 200, 250), 20), 480, 4), 'lamp_off')
save(crop_resize(on, bbox(on, 20), 480, 4), 'lamp_on')

# --- מיכל זכוכית: מנקים שאריות "משבצות שקיפות" ---
tk = load('tank'); arr = np.array(tk)
arr[:58, :, 3] = 0
arr[172:505, 258:1738, 3] = 0
tk = Image.fromarray(arr); save(crop_resize(tk, bbox(tk, 20), 1000), 'tank')

# --- רקע המיכל (דיורמה מיניאטורית, אטום) ---
bk = Image.open(SRC + 'tank_back_box_original.png').convert('RGB')   # דיורמה בתוך קופסת זכוכית (עומק: קירות צד, רצפה, תאורה)
bk = bk.resize((1500, round(bk.height * 1500 / bk.width)), Image.LANCZOS)
bk.save(OUT + 'tank_back.webp', 'WEBP', quality=84, method=6); sizes['tank_back'] = {'w': bk.width, 'h': bk.height}
print('tank_back', bk.size, os.path.getsize(OUT + 'tank_back.webp') // 1024, 'KB')

# --- ידית: צלחת ריקה + כדור עם מוט (שניהם על רקע ירוק) ---
pl = key_green(load('lever_plate_empty')); plb = bbox(pl, 40)
plate = pl.crop(plb); ph, pw = plate.height, plate.width
pa = np.array(plate); lum = pa[..., :3].mean(axis=2)
col = lum[:, pw // 2]
dark = col < 90                                       # החריץ = הכהה בעמודת המרכז (בלי 4% מהקצוות, שם מסגרת הצלחת)
idx = np.where(dark[int(ph * .04):int(ph * .96)])[0] + int(ph * .04)
slot_top, slot_bot = idx.min() / ph, idx.max() / ph
w_out = 320
save(plate.resize((w_out, round(ph * w_out / pw)), Image.LANCZOS), 'lever_plate', 90,
     slotTop=round(slot_top, 4), slotBot=round(slot_bot, 4))
print('lever slot', slot_top, slot_bot)
bl = key_green(load('lever_ball_shaft')); blb = bbox(bl, 40)
ball = bl.crop(blb)
# רוחב הכדור עצמו (בלי המוט) = רוחב הגוף העליון; נשמר כיחס לרוחב התמונה
ba = np.array(ball.split()[3]); row = np.where(ba[int(ball.height * .35)] > 128)[0]
ball_w_frac = float((row.max() - row.min()) / ball.width)
save(ball.resize((220, round(ball.height * 220 / ball.width)), Image.LANCZOS), 'lever_ball', 90, ballFrac=round(ball_w_frac, 3))

# --- כלבלב: כל התנוחות באותו קנה מידה, עם נקודת עיגון (קולר) ---
SC = 0.45
dogs = {'dog_walk_1': 'g', 'dog_walk_2': 'g', 'dog_walk_3': 'g', 'dog_walk_4': 'g',
        'dog_bark': 'g', 'dog_eat': 'g', 'dog_alert': 'g',
        'dog_sit': 'a', 'dog_sit_happy': 'a', 'dog_sleep': 'a', 'dog_stand': 'a'}
for n, kind in dogs.items():
    im = load(n)
    im = key_green(im) if kind == 'g' else clean_alpha(im, 215, 250, 1.2)
    l, t, r, b = bbox(im, 30)
    c = im.crop((l, t, r, b)); ax = collar_anchor(c)
    c = c.resize((round(c.width * SC), round(c.height * SC)), Image.LANCZOS)
    save(c, n, 86, ax=round(ax, 3))

json.dump(sizes, open(OUT + 'sizes.json', 'w'))
