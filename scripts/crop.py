"""usage: crop.py <paper_dir> '<json {name:[page,x0,y0,x1,y1]}>'  -> figs/<name>.png + pages/contact.png"""
import sys, json
from PIL import Image, ImageOps
d, spec = sys.argv[1], json.loads(sys.argv[2])
ims = []
for n, (p, a, b, c, e) in spec.items():
    im = Image.open(f'{d}/pages/hi-{p:02d}.png').convert('RGB'); w, h = im.size
    cr = im.crop((int(a*w), int(b*h), int(c*w), int(e*h)))
    bb = ImageOps.invert(cr).getbbox(); cr = cr.crop(bb) if bb else cr
    cr = ImageOps.expand(cr, 14, fill='white')
    if cr.width > 1600: cr = cr.resize((1600, int(cr.height*1600/cr.width)), Image.LANCZOS)
    cr.save(f'{d}/figs/{n}.png', optimize=True); ims.append(cr); print(n, cr.size)
W = 700; H = sum(int(i.height*W/i.width) + 16 for i in ims)
s = Image.new('RGB', (W + 20, H), 'gray'); y = 0
for i in ims:
    j = i.resize((W, int(i.height*W/i.width))); s.paste(j, (10, y)); y += j.height + 16
s.save(f'{d}/pages/contact.png')
