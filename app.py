

import os
import sqlite3
import logging
import weakref
from datetime import datetime

import tkinter as tk
from tkinter import messagebox, font as tkfont

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageTk, ImageChops
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.ticker import FuncFormatter
import matplotlib

logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
matplotlib.rcParams["font.family"] = ["Segoe UI", "Inter", "Helvetica Neue", "DejaVu Sans"]

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ecommerce.db")

BASE = "#0a0f24"
TXT, TXT2, MUTED = "#f3f6ff", "#b9c1e6", "#8891ba"
BLUE, TEAL, VIOLET = "#6ea8ff", "#34d399", "#a78bfa"
PINK, AMBER, ROSE, CYAN = "#3e1f79", "#fbbf24", "#8658c7", "#22d3ee"
ACCENT = ("#3b82f6", "#8b5cf6")         
M = 8                                   

F = {}                                   


def make_fonts():
    fam = "Segoe UI"
    F.update(
        h1=tkfont.Font(family=fam, size=22, weight="bold"),
        h2=tkfont.Font(family=fam, size=12, weight="bold"),
        body=tkfont.Font(family=fam, size=10),
        small=tkfont.Font(family=fam, size=9),
        th=tkfont.Font(family=fam, size=8, weight="bold"),
        cell=tkfont.Font(family=fam, size=10),
        kpi=tkfont.Font(family=fam, size=19, weight="bold"),
        kpi_s=tkfont.Font(family=fam, size=14, weight="bold"),
        nav=tkfont.Font(family=fam, size=11),
        brand=tkfont.Font(family=fam, size=13, weight="bold"),
        icon=tkfont.Font(family="Segoe UI Symbol", size=12),
    )


def query(sql, params=()):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return rows


def fmt_money(v):
    return f"₹{v:,.2f}" if v is not None else "₹0.00"


def compact(v):
    a = abs(v)
    if a >= 1e7:
        return f"₹{v / 1e7:.1f}Cr"
    if a >= 1e5:
        return f"₹{v / 1e5:.1f}L"
    if a >= 1e3:
        return f"₹{v / 1e3:.0f}k"
    return f"₹{v:.0f}"


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def mix(c1, c2, t):
    a, b = hex_rgb(c1), hex_rgb(c2)
    return "#%02x%02x%02x" % tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))


def fit(text, font, width):
    if font.measure(text) <= width:
        return text
    while text and font.measure(text + "…") > width:
        text = text[:-1]
    return text + "…" if text else ""


def rrect(cv, x0, y0, x1, y1, r, **kw):
    pts = [x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1, x1 - r, y1,
           x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0, x0 + r, y0]
    return cv.create_polygon(pts, smooth=True, **kw)


_NOISE = np.random.default_rng(7).normal(0, 1.5, (256, 256, 1))
RESAMPLE = Image.Resampling


def make_bg(w, h):
    
    sw, sh = max(w // 4, 8), max(h // 4, 8)
    yy, xx = np.mgrid[0:sh, 0:sw]
    u, v = xx / (sw - 1), yy / (sh - 1)
    t = ((u + v) / 2)[..., None]
    arr = np.array(hex_rgb("#070b1c"), float) * (1 - t) + np.array(hex_rgb("#1a0f3c"), float) * t
    aspect = sw / sh
    orbs = [(0.08, 0.12, 0.42, "#2f6bff", .85), (0.92, 0.08, 0.38, "#9b4dff", .80),
            (0.80, 0.95, 0.45, "#9b4dff", .70), (0.20, 0.98, 0.36, "#2f6bff", .60),
            (0.55, 0.50, 0.30, "#3b82f6", .25)]
    for cx, cy, r, col, a in orbs:
        d2 = ((u - cx) * aspect) ** 2 + (v - cy) ** 2
        k = (a * np.exp(-d2 / (2 * (r * .55) ** 2)))[..., None]
        arr = arr * (1 - k) + np.array(hex_rgb(col), float) * k
    im = Image.fromarray(np.clip(arr, 0, 255).astype("uint8")).resize((w, h), RESAMPLE.BICUBIC)
    noise = np.tile(_NOISE, (h // 256 + 1, w // 256 + 1, 1))[:h, :w]
    return Image.fromarray(np.clip(np.asarray(im, float) + noise, 0, 255).astype("uint8"))


def _rr(w, h, r, inset=0.0, ss=4):
    r = min(r, w / 2, h / 2)
    m = Image.new("L", (w * ss, h * ss), 0)
    ImageDraw.Draw(m).rounded_rectangle(
        [inset * ss, inset * ss, (w - inset) * ss - 1, (h - inset) * ss - 1],
        radius=max(r - inset, 1) * ss, fill=255)
    return m.resize((w, h), RESAMPLE.LANCZOS)


def _shadow(img, box, r, blur=4, dy=3, alpha=110):
    x0, y0, x1, y1 = box
    m = Image.new("L", img.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([x0 + 2, y0 + dy, x1 - 2, y1 + dy - 2], r, fill=alpha)
    blk = Image.new("RGBA", img.size, (2, 4, 14, 255))
    blk.putalpha(m.filter(ImageFilter.GaussianBlur(blur)))
    img.alpha_composite(blk)


def glass(img, box, r=22, tint=.085, border=1.0, shadow=True, accent=None):
    """Composite a frosted-glass panel onto `img` (RGBA) inside `box`."""
    x0, y0, x1, y1 = [int(v) for v in box]
    w, h = x1 - x0, y1 - y0
    if w < 8 or h < 8:
        return
    region = np.asarray(img.crop((x0, y0, x1, y1)).convert("RGB"), float)
    if shadow:
        _shadow(img, (x0, y0, x1, y1), r)
    yy, xx = np.mgrid[0:h, 0:w]
    u, v = xx / max(w - 1, 1), yy / max(h - 1, 1)
    d = np.hypot(xx, yy) / (0.75 * max(w, h))
    a = (tint + 0.15 * np.exp(-(d * 2.0) ** 2) + 0.05 * (1 - v))[..., None]   # frost + corner sheen
    out = region * (1 - a) + 255 * a
    if accent:
        c0, c1, k = accent
        g = np.array(hex_rgb(c0), float)[None, None, :] * (1 - u[..., None]) + \
            np.array(hex_rgb(c1), float)[None, None, :] * u[..., None]
        out = out * (1 - k) + g * k
    panel = Image.fromarray(np.clip(out, 0, 255).astype("uint8")).convert("RGBA")
    mask = _rr(w, h, r)
    img.paste(panel, (x0, y0), mask)
    # specular rim: bright top-left, faint bottom-right
    ring = np.asarray(ImageChops.subtract(mask, _rr(w, h, r, inset=1.3)), float) / 255
    s = (u + v) / 2
    rim = ring * border * (0.10 + 0.55 * (1 - s) ** 1.6 + 0.16 * s ** 5) * 255
    layer = Image.new("RGBA", (w, h), (255, 255, 255, 0))
    layer.putalpha(Image.fromarray(np.clip(rim, 0, 255).astype("uint8")))
    img.alpha_composite(layer, (x0, y0))


class Surface(tk.Canvas):
    def __init__(self, parent, app, **kw):
        kw.setdefault("width", 1)
        kw.setdefault("height", 1)
        super().__init__(parent, highlightthickness=0, bd=0, bg=BASE, **kw)
        self.app, self._job, self._photo = app, None, None
        app.surfaces.add(self)
        self.bind("<Configure>", self.schedule)
        self.bind("<Map>", self.schedule)

    def schedule(self, _e=None):
        try:
            if self._job is None:
                self._job = self.after(10, self._run)
        except tk.TclError:
            pass

    def _run(self):
        self._job = None
        try:
            if not self.winfo_ismapped():
                return
            w, h = self.winfo_width(), self.winfo_height()
        except tk.TclError:
            return
        if w > 4 and h > 4:
            self.redraw(w, h)

    def base_img(self, w, h):
        ox = self.winfo_rootx() - self.app.winfo_rootx()
        oy = self.winfo_rooty() - self.app.winfo_rooty()
        return self.app.bg.crop((ox, oy, ox + w, oy + h)).convert("RGBA")

    def show(self, img):
        self._photo = ImageTk.PhotoImage(img)
        items = self.find_withtag("surface")
        if items:
            self.itemconfigure(items[0], image=self._photo)
        else:
            self.create_image(0, 0, anchor="nw", image=self._photo, tags="surface")
            self.tag_lower("surface")

    def redraw(self, w, h):
        self.show(self.base_img(w, h))


class GlassCard(Surface):
    def __init__(self, parent, app, radius=22, tint=.085, **kw):
        super().__init__(parent, app, **kw)
        self.radius, self.tint, self.base = radius, tint, None

    def decorate(self, img, box):
        glass(img, box, self.radius, self.tint)

    def paint(self, w, h):
        pass

    def redraw(self, w, h):
        img = self.base_img(w, h)
        self.decorate(img, (M, M, w - M, h - M))
        self.base = img
        self.show(img)
        self.paint(w, h)


class Header(Surface):
    def __init__(self, parent, app, title, subtitle, badge=None):
        super().__init__(parent, app, height=78)
        self.title, self.subtitle, self.badge = title, subtitle, badge

    def redraw(self, w, h):
        img = self.base_img(w, h)
        bw = F["small"].measure(self.badge) + 42 if self.badge else 0
        if self.badge:
            glass(img, (w - M - bw, 22, w - M, 52), 15, .10, shadow=False)
        self.show(img)
        self.delete("content")
        self.create_text(12, 14, anchor="nw", text=self.title, fill=TXT, font=F["h1"], tags="content")
        self.create_text(14, 50, anchor="nw", text=self.subtitle, fill=MUTED, font=F["body"], tags="content")
        if self.badge:
            self.create_oval(w - M - bw + 14, 33, w - M - bw + 22, 41, fill=TEAL, outline="", tags="content")
            self.create_text(w - M - bw + 30, 37, anchor="w", text=self.badge, fill=TXT2, font=F["small"], tags="content")


class KPICard(GlassCard):
    def __init__(self, parent, app, label, value, color, icon, spark=None):
        super().__init__(parent, app, height=132)
        self.label, self.value, self.color, self.icon, self.spark = label, value, color, icon, spark

    def paint(self, w, h):
        self.delete("content")
        x0, x1 = M + 20, w - M - 20
        self.create_text(x0, M + 18, anchor="nw", text=self.label, fill=TXT2, font=F["small"], tags="content")
        cx, cy = x1 - 12, M + 26
        self.create_oval(cx - 13, cy - 13, cx + 13, cy + 13, fill=mix("#0d1330", self.color, .30),
                         outline=mix("#0d1330", self.color, .55), tags="content")
        self.create_text(cx, cy, text=self.icon, fill=self.color, font=F["icon"], tags="content")
        f = F["kpi"] if F["kpi"].measure(self.value) <= x1 - x0 else F["kpi_s"]
        self.create_text(x0, M + 40, anchor="nw", text=self.value, fill=TXT, font=f, tags="content")
        s = self.spark
        if s and len(s) >= 2:
            top, bot = M + 88, h - M - 16
            lo, hi = min(s), max(s)
            span = (hi - lo) or 1
            pts = []
            for i, val in enumerate(s):
                pts += [x0 + (x1 - x0) * i / (len(s) - 1), bot - (bot - top) * (val - lo) / span]
            self.create_line(*pts, smooth=True, width=2, fill=self.color, capstyle="round", joinstyle="round", tags="content")
            self.create_oval(pts[-2] - 3, pts[-1] - 3, pts[-2] + 3, pts[-1] + 3, fill="white", outline=self.color, width=2, tags="content")


class ChartCard(GlassCard):
    def __init__(self, parent, app, title, draw, subtitle=""):
        super().__init__(parent, app)
        self.title, self.draw, self.subtitle, self._cache = title, draw, subtitle, None

    def paint(self, w, h):
        self.delete("content")
        self.create_text(M + 22, M + 16, anchor="nw", text=self.title, fill=TXT, font=F["h2"], tags="content")
        if self.subtitle:
            self.create_text(w - M - 22, M + 19, anchor="ne", text=self.subtitle, fill=MUTED, font=F["small"], tags="content")
        cw, ch = w - 2 * M - 28, h - 2 * M - 56
        if cw < 100 or ch < 70:
            return
        if not self._cache or self._cache[0] != (cw, ch):          # only re-render matplotlib on resize
            fig = Figure(figsize=(cw / 100, ch / 100), dpi=100)
            fig.patch.set_alpha(0)
            self.draw(fig)
            try:
                fig.tight_layout(pad=.5)
            except Exception:
                pass
            cv = FigureCanvasAgg(fig)
            cv.draw()
            self._cache = ((cw, ch), ImageTk.PhotoImage(Image.fromarray(np.asarray(cv.buffer_rgba()).copy())))
        self.create_image(M + 14, M + 46, anchor="nw", image=self._cache[1], tags="content")


RIGHT = {"revenue", "profit", "lifetime_value", "margin_pct", "quantity", "num_orders", "orders"}
MONEY = {"revenue", "profit", "lifetime_value"}
PRETTY = {"order_id": "Order #", "order_date": "Date", "customer_name": "Customer", "customer_city": "City",
          "customer_state": "State", "product_name": "Product", "quantity": "Qty", "payment_type": "Payment",
          "order_status": "Status", "num_orders": "Orders", "lifetime_value": "Lifetime value", "margin_pct": "Margin"}
STATUS = {"delivered": ("#0f3f34", TEAL), "shipped": ("#14304f", BLUE),
          "returned": ("#4a3510", AMBER), "cancelled": ("#4a1a2a", ROSE)}


def cell_text(col, v):
    if v is None:
        return "—"
    if col in MONEY:
        return fmt_money(v)
    if col == "margin_pct":
        return f"{v:.2f}%"
    if col == "order_date":
        return str(v)[:10]
    return str(v)


class TableCard(GlassCard):
    RH, HH = 34, 30

    def __init__(self, parent, app, title, columns, rows, weights, subtitle=""):
        super().__init__(parent, app)
        self.title, self.cols, self.wts, self.subtitle = title, columns, weights, subtitle
        self.data, self.off, self.hover, self.drag, self._hp = [], 0, None, False, None
        self.set_rows(rows, subtitle)
        self.bind("<Motion>", lambda e: self._set_hover(self._row_at(e)))
        self.bind("<Leave>", lambda e: self._set_hover(None))
        for ev in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.bind(ev, self._wheel)
        self.bind("<ButtonPress-1>", self._press)
        self.bind("<B1-Motion>", self._drag_move)
        self.bind("<ButtonRelease-1>", lambda e: setattr(self, "drag", False))

    def set_rows(self, rows, subtitle=None):
        self.data = [[r[c] for c in self.cols] for r in rows]
        self.off = 0
        if subtitle is not None:
            self.subtitle = subtitle
        self.schedule()

    def geo(self, w, h):
        x0, x1 = M + 22, w - M - 26
        hy = M + 16 + (32 if self.title else 0)
        by = hy + self.HH
        vis = max(int((h - M - 12 - by) // self.RH), 1)
        tot, xs = sum(self.wts), [x0]
        for wt in self.wts:
            xs.append(xs[-1] + (x1 - x0) * wt / tot)
        return x0, x1, hy, by, vis, xs

    def decorate(self, img, box):
        glass(img, box, 22, .085)
        w, h = img.size
        x0, x1, hy, by, vis, xs = self.geo(w, h)
        ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        d.line([(x0, by - 2), (x1, by - 2)], fill=(255, 255, 255, 46), width=1)
        for k in range(1, min(vis, len(self.data))):
            d.line([(x0, by + k * self.RH), (x1, by + k * self.RH)], fill=(255, 255, 255, 16), width=1)
        img.alpha_composite(ov)

    def paint(self, w, h):
        self.delete("content")
        self.delete("hover")
        self.hover = None
        x0, x1, hy, by, vis, xs = self.geo(w, h)
        if self.title:
            self.create_text(x0, M + 16, anchor="nw", text=self.title, fill=TXT, font=F["h2"], tags="content")
        if self.subtitle:
            self.create_text(x1, M + 19, anchor="ne", text=self.subtitle, fill=MUTED, font=F["small"], tags="content")
        for j, c in enumerate(self.cols):
            right = c in RIGHT
            self.create_text(xs[j + 1] - 8 if right else xs[j] + 8, hy + self.HH / 2 - 1,
                             anchor="e" if right else "w", fill=MUTED, font=F["th"], tags="content",
                             text=PRETTY.get(c, c.replace("_", " ").title()).upper())
        n = len(self.data)
        if n == 0:
            self.create_text((x0 + x1) / 2, by + 50, text="No results for this filter", fill=MUTED, font=F["body"], tags="content")
        for k in range(min(vis, n - self.off)):
            row, cy = self.data[self.off + k], by + k * self.RH + self.RH / 2
            for j, c in enumerate(self.cols):
                v, cw = row[j], xs[j + 1] - xs[j] - 16
                if c == "order_status":
                    bg, fg = STATUS.get(v, ("#26304f", TXT2))
                    tw = F["small"].measure(v) + 22
                    rrect(self, xs[j] + 8, cy - 11, xs[j] + 8 + tw, cy + 11, 11, fill=bg, outline=mix(bg, fg, .35), tags="content")
                    self.create_text(xs[j] + 8 + tw / 2, cy, text=v, fill=fg, font=F["small"], tags="content")
                    continue
                right = c in RIGHT
                color = (TEAL if v >= 0 else ROSE) if c == "profit" and v is not None else TXT
                self.create_text(xs[j + 1] - 8 if right else xs[j] + 8, cy, anchor="e" if right else "w",
                                 text=fit(cell_text(c, v), F["cell"], cw), fill=color, font=F["cell"], tags="content")
        if n > vis:
            t0, t1 = by, by + vis * self.RH
            th = max(28, (t1 - t0) * vis / n)
            ty = t0 + (t1 - t0 - th) * self.off / (n - vis)
            rrect(self, x1 + 10, ty, x1 + 15, ty + th, 2.5, fill="#8790c4", outline="", tags="content")

    # -- interaction ---------------------------------------------------
    def _row_at(self, e):
        x0, x1, hy, by, vis, xs = self.geo(self.winfo_width(), self.winfo_height())
        if not (x0 - 8 <= e.x <= x1 + 8) or e.y < by:
            return None
        k = int((e.y - by) // self.RH)
        return k if k < min(vis, len(self.data) - self.off) else None

    def _set_hover(self, k):
        if k == self.hover:
            return
        self.hover = k
        self.delete("hover")
        if k is None or self.base is None:
            return
        x0, x1, hy, by, vis, xs = self.geo(self.winfo_width(), self.winfo_height())
        y = int(by + k * self.RH)
        box = (int(x0 - 8), y + 2, int(x1 + 8), y + self.RH - 2)
        crop = self.base.crop(box).convert("RGBA")
        lit = Image.alpha_composite(crop, Image.new("RGBA", crop.size, (255, 255, 255, 30)))
        out = Image.composite(lit, crop, _rr(crop.size[0], crop.size[1], 10))
        self._hp = ImageTk.PhotoImage(out)
        self.create_image(box[0], box[1], anchor="nw", image=self._hp, tags="hover")
        self.tag_raise("hover", "surface")

    def scroll_to(self, off):
        vis = self.geo(self.winfo_width(), self.winfo_height())[4]
        off = min(max(off, 0), max(len(self.data) - vis, 0))
        if off != self.off:
            self.off = off
            self.paint(self.winfo_width(), self.winfo_height())

    def _wheel(self, e):
        up = getattr(e, "delta", 0) > 0 or e.num == 4
        self.scroll_to(self.off + (-2 if up else 2))

    def _press(self, e):
        x0, x1, hy, by, vis, xs = self.geo(self.winfo_width(), self.winfo_height())
        if e.x > x1 + 4 and len(self.data) > vis:
            self.drag = True
            self._drag_move(e)

    def _drag_move(self, e):
        if not self.drag:
            return
        x0, x1, hy, by, vis, xs = self.geo(self.winfo_width(), self.winfo_height())
        frac = min(max((e.y - by) / (vis * self.RH), 0), 1)
        self.scroll_to(round(frac * (len(self.data) - vis)))


class ChipBar(Surface):
    """Row of glass filter chips (replaces dropdowns)."""

    def __init__(self, parent, app, label, options, var, on_change):
        super().__init__(parent, app, height=44)
        self.label, self.options, self.var, self.cb = label, options, var, on_change
        self.hover, self.rects = None, []
        self.configure(cursor="hand2")
        self.bind("<Motion>", self._motion)
        self.bind("<Leave>", lambda e: self._hover(None))
        self.bind("<Button-1>", self._click)
        var.trace_add("write", lambda *a: self.schedule())

    def layout(self, w):
        lw = max(F["small"].measure(self.label) + 24, 84)
        x, y, rects = lw, 6, []
        for opt in self.options:
            cw = F["body"].measure(opt[:1].upper() + opt[1:]) + 30
            if x + cw > w - M and x > lw:
                x, y = lw, y + 38
            rects.append((x, y, x + cw, y + 32, opt))
            x += cw + 8
        return rects, y + 38

    def redraw(self, w, h):
        rects, need = self.layout(w)
        if need != h:
            self.configure(height=need)
            return
        self.rects = rects
        img = self.base_img(w, h)
        for i, (a, b, c, d, opt) in enumerate(rects):
            sel = opt == self.var.get()
            glass(img, (a, b, c, d), 16, .17 if sel else (.12 if i == self.hover else .055), shadow=False,
                  accent=(ACCENT[0], ACCENT[1], .55) if sel else None)
        self.show(img)
        self.delete("content")
        self.create_text(M + 4, 22, anchor="w", text=self.label.upper(), fill=MUTED, font=F["th"], tags="content")
        for i, (a, b, c, d, opt) in enumerate(rects):
            self.create_text((a + c) / 2, (b + d) / 2, text=opt[:1].upper() + opt[1:], font=F["body"], tags="content",
                             fill=TXT if opt == self.var.get() or i == self.hover else TXT2)

    def _at(self, e):
        for i, (a, b, c, d, opt) in enumerate(self.rects):
            if a <= e.x <= c and b <= e.y <= d:
                return i
        return None

    def _hover(self, i):
        if i != self.hover:
            self.hover = i
            self.schedule()

    def _motion(self, e):
        self._hover(self._at(e))

    def _click(self, e):
        i = self._at(e)
        if i is not None:
            self.var.set(self.rects[i][4])
            self.cb()


NAV = [("Dashboard", "◧"), ("Sales", "☰"), ("Customers", "☺"), ("Products", "❖"), ("Revenue & Profit", "↗")]


class Sidebar(GlassCard):
    def __init__(self, parent, app, on_select):
        super().__init__(parent, app, radius=26, tint=.075, width=246)
        self.active, self.hover, self.on_select = 0, None, on_select
        self.configure(cursor="hand2")
        self.bind("<Motion>", lambda e: self._set_hover(self._hit(e)))
        self.bind("<Leave>", lambda e: self._set_hover(None))
        self.bind("<Button-1>", lambda e: self._hit(e) is not None and self.on_select(self._hit(e)))

    def box(self, i, w):
        y = M + 96 + i * 50
        return (M + 12, y, w - M - 12, y + 42)

    def _hit(self, e):
        w = self.winfo_width()
        for i in range(len(NAV)):
            a, b, c, d = self.box(i, w)
            if a <= e.x <= c and b <= e.y <= d:
                return i
        return None

    def _set_hover(self, i):
        if i != self.hover:
            self.hover = i
            self.schedule()

    def decorate(self, img, box):
        glass(img, box, 26, .075)
        w = img.size[0]
        glass(img, (M + 20, M + 22, M + 64, M + 66), 14, .10, shadow=False, accent=(ACCENT[0], "#a855f7", .85))
        for i in range(len(NAV)):
            if i == self.active:
                glass(img, self.box(i, w), 16, .13, shadow=False, accent=(ACCENT[0], ACCENT[1], .50))
            elif i == self.hover:
                glass(img, self.box(i, w), 16, .09, shadow=False)

    def paint(self, w, h):
        self.delete("content")
        self.create_text(M + 42, M + 44, text="◆", fill="white", font=F["h2"], tags="content")
        self.create_text(M + 76, M + 34, anchor="w", text="E-Commerce", fill=TXT, font=F["brand"], tags="content")
        self.create_text(M + 76, M + 54, anchor="w", text="Data Analysis", fill=TXT2, font=F["small"], tags="content")
        self.create_text(M + 24, M + 80, anchor="w", text="MENU", fill=MUTED, font=F["th"], tags="content")
        for i, (name, ic) in enumerate(NAV):
            a, b, c, d = self.box(i, w)
            col = TXT if i == self.active else TXT2
            self.create_text(a + 24, (b + d) / 2, text=ic, fill=col, font=F["icon"], tags="content")
            self.create_text(a + 46, (b + d) / 2, anchor="w", text=name, fill=col, font=F["nav"], tags="content")
        self.create_text(M + 24, h - M - 42, anchor="w", text="Delivered orders · INR", fill=TXT2, font=F["small"], tags="content")
        self.create_text(M + 24, h - M - 24, anchor="w", text=os.path.basename(DB_PATH), fill=MUTED, font=F["small"], tags="content")


# ------------------------------------------------------------------
# Chart drawing (matplotlib on a transparent figure)
# ------------------------------------------------------------------
def style(ax, grid="y"):
    ax.set_facecolor("none")
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(colors="#a0a9d3", labelsize=8.5, length=0, pad=6)
    if grid:
        ax.grid(axis=grid, color="white", alpha=.10, linewidth=.8)
        ax.set_axisbelow(True)


def month_labels(months):
    dts = [datetime.strptime(m, "%Y-%m") for m in months]
    fmt = "%b" if len({d.year for d in dts}) == 1 else "%b '%y"
    return [d.strftime(fmt) for d in dts]


def wrap(label):
    return label.replace(" ", "\n", 1) if len(label) > 9 and " " in label else label


def glass_bars(ax, x, vals, color, width=.58, alphas=None, horizontal=False, offset=0, **kw):
    from matplotlib.colors import to_rgba
    cols = [to_rgba(color, a) for a in (alphas or [.85] * len(vals))]
    pos = [i + offset for i in x]
    fn = ax.barh if horizontal else ax.bar
    return fn(pos, vals, width if not horizontal else .6, color=cols, edgecolor=(1, 1, 1, .45), linewidth=.9, **kw)


def draw_monthly(monthly, margin=False):
    def draw(fig):
        ax = fig.add_subplot(111)
        style(ax)
        x = list(range(len(monthly)))
        rev, pro = [m["revenue"] for m in monthly], [m["profit"] for m in monthly]
        ax.fill_between(x, rev, color=BLUE, alpha=.16, linewidth=0)
        ax.fill_between(x, pro, color=TEAL, alpha=.12, linewidth=0)
        h1, = ax.plot(x, rev, color=BLUE, lw=2.4, marker="o", ms=5.5, mfc=BLUE, mec=(1, 1, 1, .9), mew=1.2, label="Revenue")
        h2, = ax.plot(x, pro, color=TEAL, lw=2.4, marker="o", ms=5.5, mfc=TEAL, mec=(1, 1, 1, .9), mew=1.2, label="Profit")
        handles = [h1, h2]
        ax.set_xticks(x)
        ax.set_xticklabels(month_labels([m["month"] for m in monthly]))
        ax.set_xlim(-.3, len(x) - .7)
        ax.set_ylim(0, max(rev) * (1.5 if margin else 1.25))
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: compact(v)))
        if margin:
            ax2 = ax.twinx()
            style(ax2, grid=None)
            h3, = ax2.plot(x, [m["margin_pct"] for m in monthly], color=PINK, lw=1.8, ls="--", marker="s", ms=4, label="Margin %")
            mg = [m["margin_pct"] for m in monthly]
            ax2.set_ylim(min(mg) - (max(mg) - min(mg)) * .15, max(mg) + (max(mg) - min(mg)) * .7)
            ax2.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
            handles.append(h3)
        ax.legend(handles=handles, loc="upper left", frameon=False, fontsize=8.5, labelcolor="#dfe4fa",
                  ncol=3, handlelength=1.6, columnspacing=1.4)
    return draw


def draw_top_categories(cats):
    def draw(fig):
        ax = fig.add_subplot(111)
        style(ax)
        x, vals = list(range(len(cats))), [c["revenue"] for c in cats]
        glass_bars(ax, x, vals, VIOLET, alphas=[max(.9 - i * .12, .4) for i in x])
        for i, v in enumerate(vals):
            ax.text(i, v, compact(v), ha="center", va="bottom", color="#dfe4fa", fontsize=8.5, fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels([wrap(c["category"]) for c in cats])
        ax.set_ylim(0, max(vals) * 1.18)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: compact(v)))
    return draw


def draw_states(states):
    def draw(fig):
        ax = fig.add_subplot(111)
        style(ax, grid="x")
        names, vals = [s["customer_state"] for s in states][::-1], [s["revenue"] for s in states][::-1]
        y = list(range(len(names)))
        glass_bars(ax, y, vals, CYAN, horizontal=True, alphas=[.55 + .4 * i / max(len(y) - 1, 1) for i in y])
        for i, v in enumerate(vals):
            ax.text(v, i, "  " + compact(v), va="center", color="#dfe4fa", fontsize=8.5)
        ax.set_yticks(y)
        ax.set_yticklabels(names)
        ax.set_xlim(0, max(vals) * 1.22)
        ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: compact(v)))
    return draw


def draw_rev_vs_profit(perf):
    def draw(fig):
        ax = fig.add_subplot(111)
        style(ax)
        x, w = list(range(len(perf))), .36
        b1 = glass_bars(ax, x, [c["revenue"] for c in perf], BLUE, width=w, offset=-w / 2 - .01, label="Revenue")
        b2 = glass_bars(ax, x, [c["profit"] for c in perf], TEAL, width=w, offset=w / 2 + .01, label="Profit")
        ax.set_xticks(x)
        ax.set_xticklabels([c["category"] for c in perf], fontsize=8, rotation=30, ha="right", rotation_mode="anchor")
        ax.set_ylim(0, max(c["revenue"] for c in perf) * 1.22)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: compact(v)))
        ax.legend(handles=[b1, b2], loc="upper right", frameon=False, fontsize=8.5, labelcolor="#dfe4fa", ncol=2)
    return draw


# ------------------------------------------------------------------
# Pages
# ------------------------------------------------------------------
class Page(Surface):
    def __init__(self, parent, app, title, subtitle, badge="Delivered orders", cols=1):
        super().__init__(parent, app)
        Header(self, app, title, subtitle, badge).grid(row=0, column=0, columnspan=cols, sticky="ew")


def place_row(parent, row, items, weights, **kw):
    for c, (it, wt) in enumerate(zip(items, weights)):
        it.grid(row=row, column=c, sticky="nsew", **kw)
        parent.grid_columnconfigure(c, weight=wt, uniform="g")


class DashboardPage(Page):
    def __init__(self, parent, app):
        super().__init__(parent, app, "Executive Overview", "How the store is performing across delivered orders", cols=5)
        k = query("""
            SELECT COUNT(*) AS total_orders, ROUND(SUM(revenue),2) AS total_revenue,
                   ROUND(SUM(profit),2) AS total_profit, ROUND(AVG(revenue),2) AS aov,
                   COUNT(DISTINCT customer_name) AS total_customers
            FROM sales WHERE order_status = 'delivered'""")[0]
        monthly = query("""
            SELECT strftime('%Y-%m', order_date) AS month, ROUND(SUM(revenue),2) AS revenue,
                   ROUND(SUM(profit),2) AS profit, COUNT(*) AS orders, COUNT(DISTINCT customer_name) AS customers
            FROM sales WHERE order_status='delivered' GROUP BY month ORDER BY month""")
        aov = [m["revenue"] / m["orders"] for m in monthly]
        cards = [
            KPICard(self, app, "Total Revenue", fmt_money(k["total_revenue"]), BLUE, "₹", [m["revenue"] for m in monthly]),
            KPICard(self, app, "Total Profit", fmt_money(k["total_profit"]), TEAL, "↗", [m["profit"] for m in monthly]),
            KPICard(self, app, "Total Orders", str(k["total_orders"]), VIOLET, "▤", [m["orders"] for m in monthly]),
            KPICard(self, app, "Avg Order Value", fmt_money(k["aov"]), AMBER, "◈", aov),
            KPICard(self, app, "Customers", str(k["total_customers"]), PINK, "☺", [m["customers"] for m in monthly]),
        ]
        place_row(self, 1, cards, [1] * 5)
        cats = query("""SELECT category, ROUND(SUM(revenue),2) AS revenue FROM sales
                        WHERE order_status='delivered' GROUP BY category ORDER BY revenue DESC LIMIT 5""")
        ChartCard(self, app, "Monthly Revenue & Profit", draw_monthly(monthly), "Delivered orders").grid(
            row=2, column=0, columnspan=3, sticky="nsew")
        ChartCard(self, app, "Top 5 Categories by Revenue", draw_top_categories(cats)).grid(
            row=2, column=3, columnspan=2, sticky="nsew")
        self.grid_rowconfigure(2, weight=1)


class SalesPage(Page):
    COLS = ["order_id", "order_date", "customer_name", "customer_city", "product_name", "category",
            "quantity", "revenue", "profit", "payment_type", "order_status"]
    W = [.7, 1.3, 1.3, 1.0, 1.5, 1.1, .55, 1.2, 1.2, 1.3, 1.1]

    def __init__(self, parent, app):
        super().__init__(parent, app, "Sales", "Every order — click a chip to filter", badge="All statuses")
        self.category_var, self.status_var = tk.StringVar(value="All"), tk.StringVar(value="All")
        cats = ["All"] + [r["category"] for r in query("SELECT DISTINCT category FROM sales ORDER BY category")]
        stats = ["All"] + [r["order_status"] for r in query("SELECT DISTINCT order_status FROM sales ORDER BY order_status")]
        ChipBar(self, app, "Status", stats, self.status_var, self.refresh).grid(row=1, column=0, sticky="ew")
        ChipBar(self, app, "Category", cats, self.category_var, self.refresh).grid(row=2, column=0, sticky="ew")
        self.table = TableCard(self, app, "Orders", self.COLS, [], self.W)
        self.table.grid(row=3, column=0, sticky="nsew")
        self.grid_rowconfigure(3, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.refresh()

    def refresh(self):
        sql = f"SELECT {', '.join(self.COLS)} FROM sales WHERE 1=1"
        params = []
        if self.category_var.get() != "All":
            sql += " AND category = ?"
            params.append(self.category_var.get())
        if self.status_var.get() != "All":
            sql += " AND order_status = ?"
            params.append(self.status_var.get())
        rows = query(sql + " ORDER BY order_date DESC", params)
        self.table.set_rows(rows, f"{len(rows)} orders")


class CustomersPage(Page):
    def __init__(self, parent, app):
        super().__init__(parent, app, "Customers", "Lifetime value, loyalty and where your revenue comes from", cols=6)
        r = query("""
            WITH oc AS (SELECT customer_name, COUNT(*) AS orders FROM sales
                        WHERE order_status='delivered' GROUP BY customer_name)
            SELECT SUM(CASE WHEN orders>1 THEN 1 ELSE 0 END) AS repeat_customers, COUNT(*) AS total_customers,
                   ROUND(100.0*SUM(CASE WHEN orders>1 THEN 1 ELSE 0 END)/COUNT(*),2) AS repeat_rate_pct
            FROM oc""")[0]
        kp = [KPICard(self, app, "Total Customers", str(r["total_customers"]), PINK, "☺"),
              KPICard(self, app, "Repeat Customers", str(r["repeat_customers"]), VIOLET, "↻"),
              KPICard(self, app, "Repeat Rate", f"{r['repeat_rate_pct']}%", TEAL, "%")]
        for c, card in enumerate(kp):
            card.grid(row=1, column=c * 2, columnspan=2, sticky="nsew")
        top = query("""
            SELECT customer_name, customer_city, customer_state, COUNT(*) AS num_orders,
                   ROUND(SUM(revenue),2) AS lifetime_value
            FROM sales WHERE order_status='delivered'
            GROUP BY customer_name, customer_city, customer_state ORDER BY lifetime_value DESC LIMIT 15""")
        states = query("""SELECT customer_state, ROUND(SUM(revenue),2) AS revenue FROM sales
                          WHERE order_status='delivered' GROUP BY customer_state ORDER BY revenue DESC""")
        TableCard(self, app, "Top 15 Customers by Lifetime Value",
                  ["customer_name", "customer_city", "customer_state", "num_orders", "lifetime_value"], top,
                  [1.5, 1.2, .7, .8, 1.3]).grid(row=2, column=0, columnspan=4, sticky="nsew")
        ChartCard(self, app, "Revenue by State", draw_states(states)).grid(row=2, column=4, columnspan=2, sticky="nsew")
        self.grid_rowconfigure(2, weight=1)
        for c in range(6):
            self.grid_columnconfigure(c, weight=1, uniform="g")


class ProductsPage(Page):
    def __init__(self, parent, app):
        super().__init__(parent, app, "Products", "Category margins and your best and worst sellers", cols=9)
        perf = query("""
            SELECT category, ROUND(SUM(revenue),2) AS revenue, ROUND(SUM(profit),2) AS profit,
                   ROUND(100.0*SUM(profit)/NULLIF(SUM(revenue),0),2) AS margin_pct
            FROM sales WHERE order_status='delivered' GROUP BY category ORDER BY revenue DESC""")
        top_p = query("""SELECT product_name, category, ROUND(SUM(revenue),2) AS revenue FROM sales
                         WHERE order_status='delivered' GROUP BY product_name, category ORDER BY revenue DESC LIMIT 5""")
        bot_p = query("""SELECT product_name, category, ROUND(SUM(revenue),2) AS revenue FROM sales
                         WHERE order_status='delivered' GROUP BY product_name, category ORDER BY revenue ASC LIMIT 5""")
        TableCard(self, app, "Category Performance", ["category", "revenue", "profit", "margin_pct"], perf,
                  [1.4, 1, 1, .8]).grid(row=1, column=0, columnspan=5, sticky="nsew")
        TableCard(self, app, "Top / Bottom 5 Products by Revenue", ["product_name", "category", "revenue"],
                  list(top_p) + list(bot_p), [1.5, 1.2, 1]).grid(row=2, column=0, columnspan=5, sticky="nsew")
        ChartCard(self, app, "Revenue vs Profit by Category", draw_rev_vs_profit(perf)).grid(
            row=1, column=5, rowspan=2, columnspan=4, sticky="nsew")
        for r in (1, 2):
            self.grid_rowconfigure(r, weight=1, uniform="r")
        for c in range(9):
            self.grid_columnconfigure(c, weight=1, uniform="g")


class RevenuePage(Page):
    def __init__(self, parent, app):
        super().__init__(parent, app, "Revenue & Profit", "Monthly trend, margin and how customers pay", cols=3)
        t = query("""
            SELECT ROUND(SUM(revenue),2) AS total_revenue, ROUND(SUM(profit),2) AS total_profit,
                   ROUND(100.0*SUM(profit)/NULLIF(SUM(revenue),0),2) AS margin_pct
            FROM sales WHERE order_status='delivered'""")[0]
        monthly = query("""
            SELECT strftime('%Y-%m', order_date) AS month, ROUND(SUM(revenue),2) AS revenue,
                   ROUND(SUM(profit),2) AS profit, ROUND(100.0*SUM(profit)/NULLIF(SUM(revenue),0),2) AS margin_pct
            FROM sales WHERE order_status='delivered' GROUP BY month ORDER BY month""")
        pay = query("""SELECT payment_type, COUNT(*) AS orders, ROUND(SUM(revenue),2) AS revenue FROM sales
                       WHERE order_status='delivered' GROUP BY payment_type ORDER BY revenue DESC""")
        place_row(self, 1, [
            KPICard(self, app, "Total Revenue", fmt_money(t["total_revenue"]), BLUE, "₹", [m["revenue"] for m in monthly]),
            KPICard(self, app, "Total Profit", fmt_money(t["total_profit"]), TEAL, "↗", [m["profit"] for m in monthly]),
            KPICard(self, app, "Overall Margin", f"{t['margin_pct']}%", PINK, "%", [m["margin_pct"] for m in monthly]),
        ], [1, 1, 1])
        ChartCard(self, app, "Monthly Revenue, Profit & Margin", draw_monthly(monthly, margin=True)).grid(
            row=2, column=0, columnspan=3, sticky="nsew")
        TableCard(self, app, "Revenue by Payment Type", ["payment_type", "orders", "revenue"], pay,
                  [1.6, 1, 1.2]).grid(row=3, column=0, columnspan=3, sticky="nsew")
        self.grid_rowconfigure(2, weight=1, uniform="r")
        self.grid_rowconfigure(3, weight=1, uniform="r")


PAGES = [DashboardPage, SalesPage, CustomersPage, ProductsPage, RevenuePage]


class ECommerceApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("E-Commerce Data Analysis — Desktop")
        self.geometry("1320x820")
        self.minsize(1100, 680)
        self.configure(bg=BASE)
        self.ok = False
        try:
            query("SELECT 1 FROM sales LIMIT 1")
        except sqlite3.OperationalError:
            messagebox.showerror("Database not found", "ecommerce.db has no 'sales' table.\nRun generate_data.py first.")
            self.destroy()
            return
        make_fonts()
        self.ok = True
        self.surfaces = weakref.WeakSet()
        self._size = (1320, 820)
        self.bg = make_bg(*self._size)

        root = Surface(self, self)
        root.pack(fill="both", expand=True)
        self.sidebar = Sidebar(root, self, self.show)
        self.sidebar.pack(side="left", fill="y", padx=(8, 0), pady=8)
        self.content = Surface(root, self)
        self.content.pack(side="left", fill="both", expand=True, padx=(0, 8), pady=8)

        self.pages, self.current = {}, None
        self.show(0)
        self.bind("<Configure>", self._on_configure)
        for i in range(len(NAV)):
            self.bind(f"<Control-Key-{i + 1}>", lambda e, i=i: self.show(i))

    def show(self, i):
        if self.current is not None:
            self.current.pack_forget()
        if i not in self.pages:
            self.pages[i] = PAGES[i](self.content, self)
        self.current = self.pages[i]
        self.current.pack(fill="both", expand=True)
        self.sidebar.active = i
        self.sidebar.schedule()

    def _on_configure(self, e):
        if e.widget is not self or (e.width, e.height) == self._size or e.width < 300:
            return
        self._size = (e.width, e.height)
        self.bg = make_bg(*self._size)
        for s in list(self.surfaces):
            try:
                if s.winfo_ismapped():
                    s.schedule()
            except tk.TclError:
                pass


if __name__ == "__main__":
    app = ECommerceApp()
    if app.ok:
        app.mainloop()
