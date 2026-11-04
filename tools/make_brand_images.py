"""Regenerate BAMedia brand images (og cards + favicons). Run from repo root: python3 tools/make_brand_images.py"""
from PIL import Image, ImageDraw, ImageFont
D="/usr/share/fonts/truetype/dejavu/"
NAVY=(15,31,58); GOLD=(201,150,58); WHITE=(255,255,255); MUTED=(160,176,200)
def card(path, l1, l2, sub, fine):
    im=Image.new("RGB",(1200,630),NAVY); d=ImageDraw.Draw(im)
    d.rectangle([0,618,1200,630],fill=GOLD)
    d.rounded_rectangle([80,80,152,152],radius=16,fill=WHITE)
    d.text((116,116),"BA",font=ImageFont.truetype(D+"DejaVuSans-Bold.ttf",32),fill=NAVY,anchor="mm")
    d.text((172,116),"Bay Area Media",font=ImageFont.truetype(D+"DejaVuSans-Bold.ttf",40),fill=WHITE,anchor="lm")
    serif=ImageFont.truetype(D+"DejaVuSerif-Bold.ttf",60)
    d.text((80,230),l1,font=serif,fill=WHITE); d.text((80,310),l2,font=serif,fill=WHITE)
    d.text((80,430),sub,font=ImageFont.truetype(D+"DejaVuSans.ttf",30),fill=GOLD)
    d.text((80,490),fine,font=ImageFont.truetype(D+"DejaVuSans.ttf",28),fill=MUTED)
    im.save(path,optimize=True)
card("assets/og-image.png","A Bay Area media company","with a growing family of brands.","Custom Concierge  ·  Urban Concierge - Bay Area","bamedia.agency  ·  San Francisco Bay Area")
card("assets/og-law.png","Fast, careful follow-up for","every inquiry and every client.","Client concierge for injury & DUI law firms  ·  CA · NV · AZ","Firm-approved answers. Attorneys stay in control.")
def icon(n,path):
    i=Image.new("RGB",(n,n),NAVY); g=ImageDraw.Draw(i)
    g.rectangle([0,int(n*.875),n,n],fill=GOLD)
    g.text((n/2,n*.47),"BA",font=ImageFont.truetype(D+"DejaVuSans-Bold.ttf",int(n*.40)),fill=WHITE,anchor="mm")
    i.save(path,optimize=True)
icon(32,"favicon-32.png"); icon(180,"apple-touch-icon.png")
