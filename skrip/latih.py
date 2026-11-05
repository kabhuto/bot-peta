"""Latih pengenal nomor (<=3 digit) dari potongan titik. python latih.py [folder_mnist]

Data: latih_nyata.npz (dari data_nyata.py) + sintetis (digit MNIST ditempel di latar peta acak,
dekat titik hitam, posisi/rotasi/ukuran diacak).  Validasi: SLS yang ditahan (tidak ikut latihan).
Keluaran: model.pt.  Kelas 0-9 = digit, 10 = kosong (nomor lebih pendek dari 3 digit).
"""
import os, sys, gzip, glob, json, random, numpy as np, torch, torch.nn as nn, torch.nn.functional as F
from PIL import Image, ImageDraw, ImageFilter
Image.MAX_IMAGE_PIXELS = None
SCR = os.path.dirname(os.path.abspath(__file__)); S = 96
MN = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\User\AppData\Local\Temp\claude\d--2026-Quisioner\39da80b5-570c-4db8-b416-2019ca58b199\scratchpad"
HOLD = ("s000302", "s000500", "s000103_Inset1")
torch.manual_seed(0); random.seed(0); np.random.seed(0)

def mnist():
    im = np.frombuffer(gzip.open(os.path.join(MN, "mi.gz")).read(), np.uint8, offset=16).reshape(-1, 28, 28)
    lb = np.frombuffer(gzip.open(os.path.join(MN, "ml.gz")).read(), np.uint8, offset=8)
    return im, lb

class Net(nn.Module):
    def __init__(s):
        super().__init__()
        ch = [1, 24, 48, 96, 128]
        s.c = nn.ModuleList([nn.Conv2d(ch[i], ch[i + 1], 3, padding=1) for i in range(4)])
        s.b = nn.ModuleList([nn.BatchNorm2d(ch[i + 1]) for i in range(4)])
        s.fc = nn.Linear(128 * 6 * 6, 256); s.out = nn.Linear(256, 33); s.dp = nn.Dropout(0.3)
    def forward(s, x):
        for c, b in zip(s.c, s.b): x = F.max_pool2d(F.relu(b(c(x))), 2)
        return s.out(s.dp(F.relu(s.fc(x.flatten(1))))).view(-1, 3, 11)

def etiket(txt):
    t = [int(c) for c in txt][:3]; return t + [10] * (3 - len(t))

def sintetis(bg, dig, lab, n):
    X, Y = [], []
    for _ in range(n):
        b = bg[random.randrange(len(bg))]
        im = Image.fromarray(b).convert("L")
        if random.random() < .5: im = im.transpose(Image.FLIP_LEFT_RIGHT) if random.random() < .5 else im
        k = random.choice([1, 1, 2, 2, 2, 3]); idx = [random.randrange(len(dig)) for _ in range(k)]
        h = random.randint(14, 30); strip = Image.new("L", (k * h * 3 // 4 + 4, h + 4), 0); txt = ""
        for j, i in enumerate(idx):
            d = Image.fromarray(dig[i]).resize((h * 3 // 4, h), Image.BILINEAR); strip.paste(d, (j * h * 3 // 4 + 2, 2)); txt += str(lab[i])
        strip = strip.rotate(random.uniform(-20, 20), expand=True, resample=Image.BILINEAR)
        a = np.asarray(im).astype(float); s = np.asarray(strip).astype(float) / 255
        cx, cy = random.choice([(S // 2 - 8, 14), (S // 2 + 6, 30), (S // 2 + 20, 20), (S // 2 - 6, S - 30)]) if False else (random.randint(8, S - 8 - s.shape[1]), random.randint(8, S - 8 - s.shape[0]))
        reg = a[cy:cy + s.shape[0], cx:cx + s.shape[1]]
        ink = random.uniform(5, 50); reg[:] = reg * (1 - s) + ink * s
        yy, xx = np.ogrid[:S, :S]; r = random.randint(3, 5)
        a[(yy - S // 2) ** 2 + (xx - S // 2) ** 2 < r * r] = random.uniform(5, 40)
        out = Image.fromarray(a.clip(0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(random.uniform(0, 1.2)))
        X.append(np.asarray(out)); Y.append(etiket(txt))
    return np.array(X), np.array(Y)

def skor(lp, i, num):
    """log-probabilitas nomor `num` (string angka) untuk potongan ke-i"""
    t = etiket(num); return sum(float(lp[i, k, t[k]]) for k in range(3))

def kandidat(lp, benar, pool, k=8, ulang=5):
    """akurasi bila dipilih dari k kandidat (benar + k-1 nomor acak dari pool); dihitung `ulang` kali"""
    rnd = random.Random(1); ok = tot = 0
    for _ in range(ulang):
        for i, b in enumerate(benar):
            lain = rnd.sample([p for p in pool if p != b], min(k - 1, len(pool) - 1)); c = [b] + lain
            ok += max(c, key=lambda n: skor(lp, i, n)) == b; tot += 1
    return ok / max(1, tot)

def augment(x):
    x = x.float() / 255
    x = x * (0.8 + 0.4 * torch.rand(len(x), 1, 1, 1)) + 0.1 * (torch.rand(len(x), 1, 1, 1) - .5)
    sh = torch.randint(-3, 4, (2,)); x = torch.roll(x, (int(sh[0]), int(sh[1])), (2, 3))
    return x

if __name__ == "__main__":
    d = np.load(os.path.join(SCR, "latih_nyata.npz")); X, Y, T = d["X"], d["Y"], d["T"]
    hold = np.isin(T, HOLD); print("nyata latih", (~hold).sum(), "validasi", hold.sum())
    dig, lab = mnist(); dig = dig[:20000]; lab = lab[:20000]
    bg = X  # latar: potongan nyata (sudah memuat titik & tulisan; tambahan derau yang masuk akal)
    xs, ys = sintetis(bg, dig, lab, 9000)
    xr = X[~hold]; yr = np.array([etiket(v) for v in Y[~hold]])
    xr = np.concatenate([xr] * 12); yr = np.concatenate([yr] * 12)
    Xt = torch.tensor(np.concatenate([xs, xr]))[:, None]; Yt = torch.tensor(np.concatenate([ys, yr]))
    Xv = torch.tensor(X[hold])[:, None].float() / 255; Yv = torch.tensor([etiket(v) for v in Y[hold]])
    m = Net(); opt = torch.optim.AdamW(m.parameters(), 2e-3, weight_decay=1e-4)
    EP = int(os.environ.get("EP", 14)); sch = torch.optim.lr_scheduler.OneCycleLR(opt, 3e-3, total_steps=EP * (len(Xt) // 128 + 1))
    for ep in range(EP):
        m.train(); perm = torch.randperm(len(Xt)); tl = 0
        for i in range(0, len(Xt), 128):
            ix = perm[i:i + 128]; out = m(augment(Xt[ix])); loss = F.cross_entropy(out.reshape(-1, 11), Yt[ix].reshape(-1))
            opt.zero_grad(); loss.backward(); opt.step(); sch.step(); tl += loss.item() * len(ix)
        m.eval()
        with torch.no_grad(): pv = m(Xv).argmax(2)
        acc = (pv == Yv).all(1).float().mean().item()
        with torch.no_grad(): lp = F.log_softmax(m(Xv), 2)
        bebas = [str(int("".join(str(int(d)) for d in row if d < 10) or 0)) for row in pv]
        accK = kandidat(lp, [str(int("".join(str(int(d)) for d in r if d < 10) or 0)) for r in Yv], pool=sorted({str(int("".join(str(int(d)) for d in r if d < 10) or 0)) for r in Yv}))
        print(f"ep{ep} loss={tl/len(Xt):.3f} validasi bebas={acc*100:.0f}% | pilih dari 8 kandidat={accK*100:.0f}% (n={len(Xv)})", flush=True)
    torch.save(m.state_dict(), os.path.join(SCR, "model.pt"))
