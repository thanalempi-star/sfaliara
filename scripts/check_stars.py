"""Fear Stars: τρέχουσα κατάσταση σημάτων για το BTC.

Χρήση: python3 -I scripts/check_stars.py <coinstats_chart.json>
Το αρχείο είναι η έξοδος του CoinStats get-coin-chart-by-id (bitcoin, period=all):
λίστα από [unix_time, price, ...]. Η λογική είναι ίδια με το fear_stars.html.
"""
import datetime as dt
import json
import sys

P = dict(wDD=30, wMA=25, wRSI=20, wROC=15, maLen=50, rsiLen=14, rocLen=13,
         ddFull=80, maFull=50, rocFull=50, t1=55, t2=65, t3=75, t4=85, reset=10)
STARS = ["—", "★", "★★", "★★★", "★★★★"]


def weekly(rows):
    wk = {}
    for t, p, *_ in rows:
        d = dt.datetime.fromtimestamp(t, dt.UTC).date()
        wk.setdefault(d - dt.timedelta(days=d.weekday()), []).append(p)
    return [(k, v[0], max(v), min(v), v[-1]) for k, v in sorted(wk.items())]


def clamp01(x):
    return max(0.0, min(1.0, x))


def compute(W):
    n, C = len(W), [w[4] for w in W]
    L = P["rsiLen"]
    rsi, ag, al = [None] * n, 0.0, 0.0
    for i in range(1, n):
        ch = C[i] - C[i - 1]
        g, l = max(ch, 0), max(-ch, 0)
        if i <= L:
            ag += g / L
            al += l / L
            if i < L:
                continue
        else:
            ag = (ag * (L - 1) + g) / L
            al = (al * (L - 1) + l) / L
        rsi[i] = 100 if al == 0 else 100 - 100 / (1 + ag / al)
    fear, dd, lvl = [], [], []
    ath = 0.0
    for i in range(n):
        ath = max(ath, W[i][2])
        d = (ath - C[i]) / ath * 100
        num, den = clamp01(d / P["ddFull"]) * 100 * P["wDD"], P["wDD"]
        if i >= P["maLen"] - 1:
            ma = sum(C[i - P["maLen"] + 1:i + 1]) / P["maLen"]
            num += clamp01((1 - C[i] / ma) * 100 / P["maFull"]) * 100 * P["wMA"]
            den += P["wMA"]
        if rsi[i] is not None:
            num += clamp01((50 - rsi[i]) / 30) * 100 * P["wRSI"]
            den += P["wRSI"]
        if i >= P["rocLen"]:
            num += clamp01(-(C[i] / C[i - P["rocLen"]] - 1) * 100 / P["rocFull"]) * 100 * P["wROC"]
            den += P["wROC"]
        f = num / den
        fear.append(f)
        dd.append(d)
        lvl.append(4 if f >= P["t4"] else 3 if f >= P["t3"] else 2 if f >= P["t2"] else 1 if f >= P["t1"] else 0)
    sigs, last = [], 0
    for i in range(n):
        if fear[i] < P["t1"] - P["reset"]:
            last = 0
        if lvl[i] > last:
            sigs.append((i, lvl[i]))
            last = lvl[i]
    return fear, dd, lvl, sigs, last


def price_for(W, target):
    """Τιμή κλεισίματος αυτής της εβδομάδας που φέρνει τον φόβο στο target (ο φόβος πέφτει όσο ανεβαίνει η τιμή)."""
    lo, hi = 1.0, W[-1][4] * 3
    for _ in range(60):
        mid = (lo + hi) / 2
        k, o, h, l, _c = W[-1]
        f = compute(W[:-1] + [(k, o, max(h, mid), min(l, mid), mid)])[0][-1]
        lo, hi = (mid, hi) if f >= target else (lo, mid)
    return lo


def main():
    W = weekly(json.load(open(sys.argv[1])))
    fear, dd, lvl, sigs, cycle = compute(W)
    i = len(W) - 1
    wk_end = W[i][0] + dt.timedelta(days=6)
    print(f"Τελευταία τιμή: ${W[i][4]:,.0f}  (εβδομάδα {W[i][0]:%d/%m}–{wk_end:%d/%m/%Y}, κλείνει Κυριακή)")
    print(f"Φόβος τώρα: {fear[i]:.1f}/100  ζώνη: {STARS[lvl[i]]}  | από ATH: -{dd[i]:.1f}%")
    print(f"Προηγούμενη (κλειστή) εβδομάδα: φόβος {fear[i-1]:.1f}  ζώνη: {STARS[lvl[i-1]]}")
    print(f"Μέγιστο επίπεδο στον τρέχοντα κύκλο φόβου: {STARS[cycle]}"
          + ("" if cycle else f" (ο κύκλος ξεκινά από την αρχή κάτω από {P['t1']-P['reset']})"))
    new = [s for s in sigs if s[0] == i]
    print("ΝΕΟ ΣΗΜΑ αυτή την εβδομάδα (επιβεβαιώνεται με το κλείσιμο): " + (f"BUY {STARS[new[0][1]]}" if new else "όχι"))
    print("Τελευταία σήματα:")
    for j, lv in sigs[-5:][::-1]:
        print(f"  {W[j][0]:%d/%m/%Y}  BUY {STARS[lv]:<5} ${W[j][4]:,.0f}  (φόβος {fear[j]:.0f})")
    print("Κλείσιμο εβδομάδας που χρειάζεται για κάθε ζώνη:")
    for lv, t in enumerate([P["t1"], P["t2"], P["t3"], P["t4"]], 1):
        flag = "" if lv > cycle else "  (έχει ήδη δοθεί σε αυτόν τον κύκλο)"
        print(f"  {STARS[lv]:<5} φόβος ≥ {t}: κάτω από ${price_for(W, t):,.0f}{flag}")


if __name__ == "__main__":
    main()
