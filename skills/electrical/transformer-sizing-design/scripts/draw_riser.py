#!/usr/bin/env python3
"""
draw_riser.py - Generate a one-line / riser SVG from size_transformer.py JSON.

The sizer is the single source of truth. This script computes NOTHING; it only
draws what the JSON says, so the diagram can never disagree with the schedule.

USAGE
  python3 size_transformer.py <flags> --format json | python3 draw_riser.py --out T-1_riser.svg
  python3 draw_riser.py --in result.json --out /mnt/user-data/outputs/T-1_riser.svg

Reads JSON from stdin unless --in is given. Writes SVG to --out
(default /mnt/user-data/outputs/<tag>_riser.svg) and prints the path.
"""
import argparse
import json
import sys
import os

# ---- palette ----
INK = "#1a1d23"
MUTE = "#6b7280"
ACCENT = "#1d4ed8"     # transformer / primary
SEC = "#b45309"        # secondary
GND = "#047857"        # grounding
BOX = "#f8fafc"
BOXLINE = "#cbd5e1"
CITE = "#94a3b8"

W, H = 780, 1040
CX = 270               # vertical bus centerline
AX = 430               # annotation column left edge


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def callout(y, lines, color=INK):
    """A leader line from the bus to an annotation block at AX, top-aligned to y."""
    out = [f'<line x1="{CX+44}" y1="{y}" x2="{AX-14}" y2="{y}" '
           f'stroke="{BOXLINE}" stroke-width="1"/>']
    dy = y - 7 * (len(lines))
    for i, (txt, c, sz, weight) in enumerate(lines):
        out.append(f'<text x="{AX}" y="{dy + i*16 + 12}" font-family="ui-sans-serif,Segoe UI,Arial" '
                   f'font-size="{sz}" font-weight="{weight}" fill="{c}">{esc(txt)}</text>')
    return "\n".join(out)


def device_box(y, label, color):
    """Molded-case breaker / disconnect symbol: a square on the line."""
    s = 22
    return (f'<rect x="{CX-s//2}" y="{y-s//2}" width="{s}" height="{s}" rx="3" '
            f'fill="white" stroke="{color}" stroke-width="2.2"/>'
            f'<line x1="{CX-s//2+3}" y1="{y+s//2-3}" x2="{CX+s//2-3}" y2="{y-s//2+3}" '
            f'stroke="{color}" stroke-width="2"/>')


def panel_box(y, h, tag, sub):
    out = [f'<rect x="{CX-95}" y="{y}" width="190" height="{h}" rx="6" '
           f'fill="{BOX}" stroke="{INK}" stroke-width="2"/>',
           f'<text x="{CX}" y="{y+26}" text-anchor="middle" font-family="ui-sans-serif,Segoe UI,Arial" '
           f'font-size="18" font-weight="700" fill="{INK}">{esc(tag)}</text>']
    if sub:
        out.append(f'<text x="{CX}" y="{y+h-12}" text-anchor="middle" '
                   f'font-family="ui-sans-serif,Segoe UI,Arial" font-size="11.5" fill="{MUTE}">{esc(sub)}</text>')
    return "\n".join(out)


def transformer(y):
    """Delta-wye two-winding symbol: two overlapping circles, Δ over Y, neutral tap."""
    r = 30
    top, bot = y, y + 46
    out = [
        f'<circle cx="{CX}" cy="{top}" r="{r}" fill="white" stroke="{ACCENT}" stroke-width="2.4"/>',
        f'<circle cx="{CX}" cy="{bot}" r="{r}" fill="white" stroke="{SEC}" stroke-width="2.4"/>',
        # delta triangle in top coil
        f'<path d="M{CX-11},{top+7} L{CX+11},{top+7} L{CX},{top-12} Z" fill="none" '
        f'stroke="{ACCENT}" stroke-width="2"/>',
        # wye in bottom coil
        f'<path d="M{CX},{bot} L{CX},{bot-13} M{CX},{bot} L{CX-11},{bot+8} M{CX},{bot} L{CX+11},{bot+8}" '
        f'fill="none" stroke="{SEC}" stroke-width="2"/>',
    ]
    return "\n".join(out), top - r, bot + r, bot


def ground_symbol(x, y, color):
    return (f'<line x1="{x}" y1="{y-14}" x2="{x}" y2="{y}" stroke="{color}" stroke-width="2"/>'
            f'<line x1="{x-13}" y1="{y}" x2="{x+13}" y2="{y}" stroke="{color}" stroke-width="2"/>'
            f'<line x1="{x-8}" y1="{y+5}" x2="{x+8}" y2="{y+5}" stroke="{color}" stroke-width="2"/>'
            f'<line x1="{x-4}" y1="{y+10}" x2="{x+4}" y2="{y+10}" stroke="{color}" stroke-width="2"/>')


def main():
    ap = argparse.ArgumentParser(description="Draw a one-line/riser SVG from sizer JSON")
    ap.add_argument("--in", dest="infile", default=None, help="JSON file (default: stdin)")
    ap.add_argument("--out", default=None, help="output SVG path")
    args = ap.parse_args()

    raw = open(args.infile).read() if args.infile else sys.stdin.read()
    d = json.loads(raw)
    pri, sec, gnd = d["primary"], d["secondary"], d["grounding"]
    tag = d.get("tag", "T-1")
    out_path = args.out or f"/mnt/user-data/outputs/{tag}_riser.svg"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    def amp(x):
        return f"{x} A" if x is not None else "see flag"

    s = []
    s.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="ui-sans-serif,Segoe UI,Arial">')
    s.append(f'<rect width="{W}" height="{H}" fill="white"/>')
    s.append(f'<text x="40" y="44" font-size="22" font-weight="800" fill="{INK}">'
             f'{esc(tag)} \u2014 Transformer Riser / One-Line</text>')
    s.append(f'<text x="40" y="66" font-size="13" fill="{MUTE}">'
             f'{esc(d["kva"])} kVA, {esc(pri["v_label"])} \u2192 {esc(sec["v_label"])}'
             f'{" (SDS)" if gnd.get("sds") else ""} \u00b7 NEC 2023 \u00b7 first-pass, verify before issue</text>')

    # vertical geometry
    y_src_top, src_h = 96, 60
    y_src_bot = y_src_top + src_h
    y_pri_ocpd = 250
    y_xfmr = 360
    txf_svg, txf_top, txf_bot, wye_y = transformer(y_xfmr)
    y_sec_ocpd = 600
    y_load_top, load_h = 720, 60

    # ---- conductor bus (drawn first, behind devices) ----
    s.append(f'<line x1="{CX}" y1="{y_src_bot}" x2="{CX}" y2="{txf_top}" stroke="{ACCENT}" stroke-width="2.6"/>')
    s.append(f'<line x1="{CX}" y1="{txf_bot}" x2="{CX}" y2="{y_load_top}" stroke="{SEC}" stroke-width="2.6"/>')

    # ---- source panel ----
    s.append(panel_box(y_src_top, src_h, d.get("source_tag", "HP"),
                       f'source \u00b7 {pri["v_label"]} {pri["phase"]}\u03c6'))

    # ---- primary feeder callout ----
    pc = (f'PARALLEL sets - size by hand' if pri["parallel"]
          else f'{pri["conductor"]} {pri["material"]} ({pri["term"]}\u00b0C, {pri["conductor_amp"]} A)')
    pri_egc = pri.get("egc")
    if pri_egc:
        pc += f' + {pri_egc} EGC'
    s.append(callout((y_src_bot + y_pri_ocpd)//2, [
        ("PRIMARY FEEDER", ACCENT, 11, 700),
        (pc, INK, 13, 600),
        (f'{pri["fla"]} A FLA \u00d7125%; ' + ("tap 240.21(B)" if pri["tap"] else "240.4 / 240.4(B)")
         + ("; EGC 250.122" if pri_egc else ""), CITE, 11, 400),
    ]))

    # ---- primary OCPD ----
    s.append(device_box(y_pri_ocpd, "", ACCENT))
    op_disp = amp(pri["ocpd"]) if pri["ocpd"] is not None else "by upstream branch"
    s.append(callout(y_pri_ocpd, [
        ("PRIMARY OCPD", ACCENT, 11, 700),
        (op_disp, INK, 15, 700),
        (f'Table 450.3(B), {pri["ocpd_pct"]}% basis', CITE, 11, 400),
    ]))

    # ---- transformer ----
    s.append(txf_svg)
    s.append(callout(y_xfmr + 23, [
        (f'{tag}  {d["kva"]} kVA', ACCENT, 14, 700),
        (f'{pri["v_label"]} \u2192 {sec["v_label"]}', INK, 12, 600),
        (f'{pri["conn"]}-{sec["conn"]}' + (f', {d["k_factor"]}' if d.get("k_factor") else ''), MUTE, 11, 400),
        (d.get("install", ""), CITE, 10.5, 400),
    ]))

    # ---- grounding branch (SDS) ----
    if gnd.get("sds"):
        gx, gy = 120, wye_y + 70
        s.append(f'<line x1="{CX}" y1="{wye_y}" x2="{gx}" y2="{wye_y}" stroke="{GND}" stroke-width="2"/>')
        s.append(f'<line x1="{gx}" y1="{wye_y}" x2="{gx}" y2="{gy}" stroke="{GND}" stroke-width="2"/>')
        s.append(ground_symbol(gx, gy, GND))
        s.append(f'<text x="{gx}" y="{gy+34}" text-anchor="middle" font-size="11" font-weight="700" fill="{GND}">SDS GROUND</text>')
        s.append(f'<text x="{gx}" y="{gy+50}" text-anchor="middle" font-size="10.5" fill="{MUTE}">SBJ {esc(gnd["sbj"])} \u00b7 250.102(C)(1)</text>')
        s.append(f'<text x="{gx}" y="{gy+64}" text-anchor="middle" font-size="10.5" fill="{MUTE}">GEC {esc(gnd["gec"])} \u00b7 250.66</text>')
        s.append(f'<text x="{gx}" y="{gy+78}" text-anchor="middle" font-size="10" fill="{CITE}">bond N-G at ONE point</text>')

    # ---- secondary OCPD (main) ----
    if sec["ocpd"] is not None:
        s.append(device_box(y_sec_ocpd, "", SEC))
        cap = "panel-bus capped (408.36)" if sec.get("panel_bus") else "Table 450.3(B) \u2264125%"
        s.append(callout(y_sec_ocpd, [
            ("SECONDARY MAIN OCPD", SEC, 11, 700),
            (amp(sec["ocpd"]), INK, 15, 700),
            (cap, CITE, 11, 400),
        ]))
    else:
        s.append(callout(y_sec_ocpd, [
            ("NO SECONDARY OCPD", SEC, 11, 700),
            ("primary-only protection", INK, 13, 600),
            ("sec. conductors per 240.4(F)/450.3(B)", CITE, 11, 400),
        ]))

    # ---- secondary feeder callout ----
    scd = ('PARALLEL sets - size by hand' if sec["parallel"]
           else f'{sec["conductor"]} {sec["material"]} ({sec["term"]}\u00b0C, {sec["conductor_amp"]} A)')
    sec_egc = sec.get("egc")
    if sec_egc:
        scd += f' + {sec_egc} EGC'
    s.append(callout((y_sec_ocpd + y_load_top)//2, [
        ("SECONDARY FEEDER", SEC, 11, 700),
        (scd, INK, 13, 600),
        ((sec.get("tap_rule") or "240.21(C)") + ("; EGC 250.122" if sec_egc else ""), CITE, 11, 400),
    ]))

    # ---- load panel ----
    busnote = f'{sec.get("panel_bus"):g} A bus' if sec.get("panel_bus") else f'{sec["v_label"]}'
    s.append(panel_box(y_load_top, load_h, d.get("load_tag", "LP"), f'load \u00b7 {busnote}'))

    # ---- footer note ----
    note_y = y_load_top + load_h + 56
    s.append(f'<text x="40" y="{note_y}" font-size="11" fill="{MUTE}">'
             f'Conductors first-pass at {pri["term"]}\u00b0C, no derating. Verify Table 310.16 with</text>')
    s.append(f'<text x="40" y="{note_y+15}" font-size="11" fill="{MUTE}">'
             f'ambient/CCC derating (310.15) and actual lug temp ratings (110.14(C)) before issue.</text>')
    if d.get("flags"):
        s.append(f'<text x="40" y="{note_y+37}" font-size="11" font-weight="700" fill="{SEC}">'
                 f'{len(d["flags"])} flag(s) from the sizer \u2014 read them with the schedule.</text>')

    s.append('</svg>')

    with open(out_path, "w") as f:
        f.write("\n".join(s))
    print(out_path)


if __name__ == "__main__":
    main()
