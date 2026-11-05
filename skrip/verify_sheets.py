import sys, os, json, math, sqlite3
from PIL import Image, ImageDraw, ImageFont
Image.MAX_IMAGE_PIXELS = None
SCR = os.path.dirname(os.path.abspath(__file__))
png, tag, draft = sys.argv[1:4]
cand = {o["id"]: o for o in json.load(open(os.path.join(SCR, tag + "_cand.json")))}
c = sqlite3.connect(draft)
t = c.execute("select table_name from gpkg_contents where data_type='features'").fetchone()[0]
rows = c.execute(f'select no_bang,blob_id,status_pindah,jarak_pindah_m from "{t}" where blob_id is not null order by cast(no_bang as integer)').fetchall()
imrgb = Image.open(png).convert("RGB")
font = ImageFont.truetype("arial.ttf", 22)
CW, CH, COLS, ROWS = 200, 210, 6, 5
PER = COLS * ROWS
W0, H0 = 105, 38
for s in range(math.ceil(len(rows) / PER)):
    sheet = Image.new("RGB", (CW * COLS, CH * ROWS), "white"); dr = ImageDraw.Draw(sheet)
    for k, (nb, bid, st, dj) in enumerate(rows[s * PER:(s + 1) * PER]):
        o = cand[int(bid)]
        box = (int(o["cx"] - W0), int(o["cy"] - H0), int(o["cx"] + 25), int(o["cy"] + H0))
        cr = imrgb.crop(box)
        ImageDraw.Draw(cr).ellipse([W0 - 13, H0 - 13, W0 + 13, H0 + 13], outline=(255, 0, 0), width=2)
        cr = cr.rotate(90, expand=True)
        cr = cr.resize((cr.width * 3, cr.height * 3), Image.LANCZOS); cr.thumbnail((CW - 6, CH - 34))
        x = (k % COLS) * CW; y = (k // COLS) * CH
        sheet.paste(cr, (x + 3, y + 30)); dr.rectangle([x, y, x + CW - 1, y + CH - 1], outline="gray")
        dr.text((x + 6, y + 3), f"{int(nb)}{'?' if st == 'dipindah_cek' else ''}  d{bid}", fill="red", font=font)
    sheet.save(os.path.join(SCR, f"{tag}_vsheet{s}.jpg"), quality=90)
print(len(rows), "potongan,", math.ceil(len(rows) / PER), "lembar")
