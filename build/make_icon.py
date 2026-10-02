"""Génère assets/icon.ico et assets/logo.png (dégradé indigo -> violet, monogramme S et flèches d'échange)."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
S = 1024


def draw():
    grad = Image.new("RGBA", (S, S))
    top, bot = (99, 102, 241), (139, 92, 246)
    px = grad.load()
    for y in range(S):
        for x in range(S):
            t = (x + y) / (2 * S)
            px[x, y] = tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3)) + (255,)
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, S - 1, S - 1), radius=230, fill=255)
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    img.paste(grad, (0, 0), mask)

    d = ImageDraw.Draw(img)
    # Reflet discret en haut
    hl = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(hl).ellipse((-300, -700, S + 300, 420), fill=(255, 255, 255, 34))
    img = Image.alpha_composite(img, Image.composite(hl, Image.new("RGBA", (S, S)), mask))
    d = ImageDraw.Draw(img)

    font = None
    for f in ("C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf"):
        if Path(f).exists():
            font = ImageFont.truetype(f, 600)
            break
    d.text((S / 2, S / 2 - 30), "S", font=font, fill="white", anchor="mm")

    # Flèches d'échange (bas)
    w = 46
    y1, y2 = 820, 900
    d.line((300, y1, 724, y1), fill="white", width=w)
    d.polygon([(724 + 10, y1 - 62), (724 + 10, y1 + 62), (800, y1)], fill="white")
    d.line((300, y2, 724, y2), fill=(255, 255, 255, 170), width=w)
    d.polygon([(300 - 10, y2 - 62), (300 - 10, y2 + 62), (224, y2)], fill=(255, 255, 255, 170))
    return img


def wizard(icon):
    """Images de l'assistant d'installation (Inno Setup, échelle 200 %)."""
    W, H = 328, 628
    big = Image.new("RGB", (W, H))
    px = big.load()
    a, b = (14, 21, 40), (49, 46, 129)
    for y in range(H):
        for x in range(W):
            t = (y / H) * 0.8 + (x / W) * 0.2
            px[x, y] = tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))
    big.paste(icon.resize((150, 150), Image.LANCZOS), ((W - 150) // 2, 150), icon.resize((150, 150), Image.LANCZOS))
    d = ImageDraw.Draw(big)
    fb = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 34)
    fr = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 19)
    d.text((W / 2, 345), "SallyTraduction", font=fb, fill="white", anchor="mm")
    d.text((W / 2, 385), "Traduction technique", font=fr, fill=(196, 200, 255), anchor="mm")
    d.text((W / 2, 410), "100 % locale", font=fr, fill=(196, 200, 255), anchor="mm")
    small = Image.new("RGB", (110, 116), (255, 255, 255))
    ic = icon.resize((96, 96), Image.LANCZOS)
    small.paste(ic, (7, 10), ic)
    return big, small


if __name__ == "__main__":
    img = draw()
    out = ROOT / "assets"
    out.mkdir(exist_ok=True)
    img.resize((256, 256), Image.LANCZOS).save(out / "logo.png")
    img.save(out / "icon.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    big, small = wizard(img)
    big.save(out / "wizard_large.bmp")
    small.save(out / "wizard_small.bmp")
    print("icône, logo et images d'installation créés dans", out)
