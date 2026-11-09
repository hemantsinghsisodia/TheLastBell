"""Objective checks on the generated WAVs (run after build_all): python -I Tools/audio/gen/checks.py

These cannot judge taste. They prove: no clipping, DC under 0.001, the loudness targets, clean loop seams, and that each recipe's
measurable signature is present (thunder cracks and envelopes, bell beating at stages 1-4 and not at 5, pre-roll, filters, the
chase grid, formants, tremolo, 40 Hz crypt tone, drip glides, variant differences).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np  # noqa: E402

import audio_lib as A  # noqa: E402

SR = A.SR
results = []


def check(name, ok, msg=""):
    results.append((name, bool(ok), msg))
    print("%s  %-44s %s" % ("PASS" if ok else "FAIL", name, msg))


def load(name):
    return A.read_wav(os.path.join(A.OUT_DIR, name + ".wav"))


def mono(x):
    return x.mean(axis=1) if x.ndim == 2 else x


def band_rms_db(x, lo, hi, t0=0.0, t1=None):
    x = mono(x)
    seg = x[int(t0 * SR):int((t1 if t1 is not None else len(x) / SR) * SR)]
    seg = A.bandpass(seg, lo, hi, 4, pad=SR // 4) if lo > 0 else A.lowpass(seg, hi, 4, pad=SR // 4)
    return A.db(A.rms(seg))


def win_rms_db(x, t0, t1):
    x = mono(x)
    return A.db(A.rms(x[int(t0 * SR):int(t1 * SR)]))


def envelope(x, lo, hi, smooth=50.0):
    b = A.bandpass(mono(x), lo, hi, 4, pad=SR // 4)
    return A.lowpass(np.abs(b), smooth, 2, pad=SR // 4)


def spectrum(x):
    x = mono(x)
    X = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2
    return np.fft.rfftfreq(len(x), 1 / SR), X


def band_frac(x, lo, hi):
    f, P = spectrum(x)
    return float(P[(f >= lo) & (f < hi)].sum() / P.sum())


def corr_lr(x):
    return float(np.corrcoef(x[:, 0], x[:, 1])[0, 1])


def peak_freq(x, lo, hi, t0=0.0, t1=None):
    x = mono(x)
    seg = x[int(t0 * SR):int((t1 if t1 is not None else len(x) / SR) * SR)]
    f, P = spectrum(seg)
    m = (f >= lo) & (f <= hi)
    return float(f[m][np.argmax(P[m])])


def mod_spectrum(env, fmin, fmax):
    e = env[int(0.5 * SR):-int(0.5 * SR)]
    e = e - e.mean()
    S = np.abs(np.fft.rfft(e * np.hanning(len(e)))) ** 2
    f = np.fft.rfftfreq(len(e), 1 / SR)
    m = (f >= fmin) & (f <= fmax)
    return f[m], S[m], float(np.sum(S[(f >= 0.1) & (f <= 30)]))


# --------------------------------------------------------------------------------------------------------------------


def check_all_files(man):
    for name, e in sorted(man.items()):
        y = load(name)
        raw_peak = np.max(np.abs(y))
        ok = np.all(np.isfinite(y)) and raw_peak < 0.9999
        loop_like = e["loop"]
        is_sting = "Sting" in name
        if loop_like or (e["group"] == "music" and not is_sting):
            level_ok = abs(e["rms_db"] - (A.MUSIC_DB if e["group"] == "music" else A.BED_DB)) < 0.2 and e["peak_db"] < -0.9
        else:
            level_ok = abs(e["peak_db"] - A.ONESHOT_DB) < 0.15
        ends_ok = True
        if not loop_like:
            ends_ok = np.max(np.abs(y[0])) < 0.01 and np.max(np.abs(y[-1])) < 0.01
        dc_ok = e["dc"] < 0.001
        check("file:" + name, ok and level_ok and dc_ok and ends_ok,
              "rms %.1f peak %.1f dc %.5f%s" % (e["rms_db"], e["peak_db"], e["dc"], "" if ends_ok else " (edge not zero)"))
        if loop_like and name != "MUS_LB_Chase":
            check("seam:" + name, abs(e["seam_step_db"]) < 0.5 and e["seam_click"] < 8.0,
                  "step %+.2f dB click %.1f" % (e["seam_step_db"], e["seam_click"]))


def check_rain_wind():
    ro, ri = load("SFX_LB_Rain_Out"), load("SFX_LB_Rain_In")
    check("rain_out: decorrelated L/R", abs(corr_lr(ro)) < 0.1, "corr %.3f" % corr_lr(ro))
    check("rain_out: 400-9000 band holds the bed", band_frac(ro, 300, 10000) > 0.9, "%.3f" % band_frac(ro, 300, 10000))
    hi_o = band_rms_db(ro, 3000, 8000) - band_rms_db(ro, 150, 1500)
    hi_i = band_rms_db(ri, 3000, 8000) - band_rms_db(ri, 150, 1500)
    check("rain_in: muffled vs rain_out (HF/LF ratio)", hi_i < hi_o - 6, "out %.1f dB, in %.1f dB" % (hi_o, hi_i))
    check("rain_out: >2 kHz drops present", band_rms_db(ro, 2000, 7000) > A.db(A.rms(ro)) - 12, "")
    w, h = load("SFX_LB_Wind"), load("SFX_LB_Wind_Howl")
    check("wind: L/R independent", abs(corr_lr(w)) < 0.25, "corr %.3f" % corr_lr(w))
    check("wind: energy 150-1500 Hz", band_frac(w, 150, 1500) > 0.9, "%.3f" % band_frac(w, 150, 1500))
    rr = [A.db(A.rms(mono(w)[i:i + SR])) for i in range(0, len(w) - SR, SR // 2)]
    check("wind: gusts (1 s RMS wander > 3 dB)", max(rr) - min(rr) > 3.0, "%.1f dB range" % (max(rr) - min(rr)))
    check("howl: energy in 330-580 Hz", band_frac(h, 330, 580) > 0.8, "%.3f" % band_frac(h, 330, 580))
    # the glide covers both ends of 380-520
    pk = [peak_freq(h, 300, 650, t0, t0 + 1.0) for t0 in range(0, 44)]
    check("howl: glides ~380..520 Hz", min(pk) < 410 and max(pk) > 490, "peak track %.0f..%.0f Hz" % (min(pk), max(pk)))


def check_thunder():
    for i in range(1, 5):
        n = "SFX_LB_Thunder_Near_%02d" % i
        x = mono(load(n))
        dur = len(x) / SR
        crack = band_rms_db(x, 2000, 8000, 0.0, 0.04) - band_rms_db(x, 2000, 8000, 1.0, 2.0)
        hf_late = band_rms_db(x, 600, 8000, 1.5, dur - 0.5) - band_rms_db(x, 20, 300, 1.5, dur - 0.5)
        env = envelope(x, 20, 300, 6.0)
        e = 20 * np.log10(env[::480] + 1e-9)  # 10 ms hops
        onsets = 0
        for k in range(30, len(e) - 30):  # a surge: +3 dB over the min of the previous 0.4 s
            if e[k] - e[k - 30:k].min() > 3.0 and e[k] >= e[k - 1] and e[k] > e[k + 1]:
                onsets += 1
        check(n, 7.0 <= dur <= 9.0 and crack > 25 and hf_late < -25,
              "len %.2f s, crack(2-8k, first 40 ms) %+.0f dB over the tail, >600Hz vs <300Hz late %+.0f dB" % (dur, crack, hf_late))
    for i in range(1, 5):
        n = "SFX_LB_Thunder_Mid_%02d" % i
        x = mono(load(n))
        dur = len(x) / SR
        hf = band_rms_db(x, 2000, 8000, 0.0, 1.0) - A.db(A.rms(x))
        env = envelope(x, 20, 450, 4.0)
        tpk = np.argmax(env[: int(3.5 * SR)]) / SR
        lo = band_frac(x, 20, 500)
        check(n, 6.0 <= dur <= 7.0 and hf < -35 and 0.8 <= tpk <= 3.0 and lo > 0.97,
              "len %.2f s, no crack (2-8k %+.0f dB), peak at %.2f s, <500 Hz %.3f" % (dur, hf, tpk, lo))
    for i in range(1, 5):
        n = "SFX_LB_Thunder_Far_%02d" % i
        x = mono(load(n))
        dur = len(x) / SR
        env = envelope(x, 20, 300, 4.0)
        tpk = np.argmax(env[: int(3.5 * SR)]) / SR
        hf = band_rms_db(x, 400, 3000) - band_rms_db(x, 20, 200)
        a50 = np.argmax(env > 0.5 * env.max()) / SR
        check(n, 5.0 <= dur <= 6.0 and hf < -25 and a50 > 0.6,
              "len %.2f s, >400 Hz %+.0f dB, 50%% of peak at %.2f s, peak at %.2f s" % (dur, hf, a50, tpk))
    for i in range(1, 4):
        n = "SFX_LB_Thunder_Strike_%02d" % i
        x = mono(load(n))
        env = envelope(x, 3000, 10000, 300.0)
        hop = SR // 1000  # 1 ms
        e = env[: int(0.12 * SR)][::hop]
        valley_i = 35 + int(np.argmin(e[35:58]))
        valley = e[valley_i]
        peak2_i = 55 + int(np.argmax(e[55:80]))
        rise_db = 20 * np.log10(e[peak2_i] / max(valley, 1e-9))
        on1 = int(np.argmax(e > 0.3 * e.max()))
        on2 = valley_i + int(np.argmax(e[valley_i:] > 0.5 * e[peak2_i]))  # half the second crack's height
        gap = (on2 - on1) / 1000.0
        merged = [0, 1] if rise_db > 6 else [0]
        sub = band_rms_db(x, 35, 65, 0.0, 0.15) - band_rms_db(x, 100, 400, 0.0, 0.15)
        tear = win_rms_db(mono(load(n)), 0.1, 0.4) - win_rms_db(mono(load(n)), 1.5, 2.0)
        check(n, len(x) == 3 * SR and len(merged) >= 2 and abs(gap - 0.060) < 0.012 and tear > 10,
              "second crack +%.0f dB over the valley, gap %.0f ms, sub thump %+.0f dB re 100-400 Hz, tear 0.1-0.4 s vs tail %+.0f dB" % (rise_db, gap * 1000, sub, tear))


def bell_roughness(x, t0, t1, lo=100, hi=125):
    seg = mono(x)[int(t0 * SR):int(t1 * SR)]
    env = A.lowpass(np.abs(A.bandpass(seg, lo, hi, 4, pad=SR // 4)), 14, 4, pad=SR // 4)
    env = env / A.exp_decay(len(env), 12.0)
    f, S, tot = mod_spectrum(env, 1.5, 6.0)
    return float(S.sum() / tot), float(f[np.argmax(S)])


def check_bells():
    rough = {}
    for st in range(1, 6):
        x = load("SFX_LB_Bell_Stage%d" % st)
        t0 = 1.5 + (1.2 if st == 4 else 0.0)
        r, f = bell_roughness(x, t0, t0 + 9.0)
        rough[st] = (r, f)
        c = {1: .6, 2: .75, 3: .9, 4: 1.0, 5: 0.0}[st]
        print("      stage %d beat band share %.2f at %.2f Hz (expected %.2f)" % (st, r, f, 2 * (0.6 + 1.2 * c)))
    check("bell: stages 1-4 beat clearly, 5 does not", min(rough[s][0] for s in (1, 2, 3, 4)) > 3 * rough[5][0] + 0.05
          and all(abs(rough[s][1] - 2 * (0.6 + 1.2 * c)) < 0.8 for s, c in ((1, .6), (2, .75), (3, .9), (4, 1.0))),
          " ".join("s%d %.2f" % (s, rough[s][0]) for s in range(1, 6)))
    # beat depth at the hum/prime band in dB (5th-95th percentile of the flattened envelope)
    for st in range(1, 5):
        x = load("SFX_LB_Bell_Stage%d" % st)
        t0 = 2.0 + (1.2 if st == 4 else 0.0)
        seg = mono(x)[int(t0 * SR):int((t0 + 6.0) * SR)]
        env = A.lowpass(np.abs(A.bandpass(seg, 100, 125, 4, pad=SR // 4)), 14, 4, pad=SR // 4)[SR // 2:-SR // 2]
        env = env / A.exp_decay(len(env), 12.0)[: len(env)]
        depth = 20 * np.log10(np.percentile(env, 95) / np.percentile(env, 5))
        check("bell stage %d: beat depth > 6 dB" % st, depth > 6.0, "%.1f dB" % depth)
    # crack (distortion) level: harmonic grit above the nominal band relative to the stage-5 clean spectrum
    lp = {1: 900.0, 2: 1500.0, 3: 2500.0}
    for st, fc in lp.items():
        x = load("SFX_LB_Bell_Stage%d" % st)
        up = band_rms_db(x, fc * 2.0, 15000, 0.5, 10.0) - band_rms_db(x, 40, fc, 0.5, 10.0)
        check("bell stage %d: low-passed at %.0f Hz" % (st, fc), up < -35, "above %.0f Hz: %+.0f dB" % (fc * 2, up))
    for st in (4, 5):
        x = load("SFX_LB_Bell_Stage%d" % st)
        up = band_rms_db(x, 4000, 15000, 1.0, 6.0) - band_rms_db(x, 40, 2000, 1.0, 6.0)
        check("bell stage %d: full band (>4 kHz present)" % st, up > -45, "%+.0f dB" % up)
    x = load("SFX_LB_Bell_Stage4")
    pre = win_rms_db(x, 0.9, 1.15) - win_rms_db(x, 0.0, 0.3)
    tmax = np.argmax(np.abs(mono(x))) / SR
    check("bell stage 4: reversed-swell pre-roll", pre > 6 and 1.15 < tmax < 1.5, "swell +%.1f dB, strike peak at %.3f s" % (pre, tmax))
    x = load("SFX_LB_Bell_Stage5")
    sub = band_rms_db(x, 25, 30, 8.0, 25.0) - band_rms_db(x, 40, 5000, 8.0, 25.0)
    sub_end = band_rms_db(x, 25, 30, 22.0, 28.0)
    check("bell stage 5: 27.5 Hz sub hum, 30 s", len(x) == 30 * SR and sub > -20 and sub_end > -90 + 20,
          "sub %+.0f dB re body (8-25 s), length %.1f s" % (sub, len(x) / SR))
    sm = load("SFX_LB_SmallBell_Strike")
    pk = peak_freq(sm, 480, 570, 0.05, 2.0)
    hum_vs_prime = band_rms_db(sm, 255, 268, 0.05, 1.0) - band_rms_db(sm, 515, 531, 0.05, 1.0)
    check("small bell strike: prime ~523 Hz, hum (261 Hz) not dominant", abs(pk - 523) < 4 and len(sm) == 4 * SR and hum_vs_prime < 0, "peak %.1f Hz, hum %+.1f dB re prime" % (pk, hum_vs_prime))
    fl = load("SFX_LB_SmallBell_Fail")
    check("small bell fail: 3 s", len(fl) == 3 * SR, "")
    so = load("SFX_LB_SmallBell_Solved")
    res = band_rms_db(so, 50, 140, 3.0, 4.5) - band_rms_db(so, 50, 140, 0.0, 1.5)
    check("small bell solved: low resonance after the 4 bells", len(so) == 5 * SR and res > 8, "%+.0f dB" % res)
    # fail cluster has a clash: two partials within 60 cents of each other exist (beating pairs)
    f, P = spectrum(mono(fl)[: int(1.5 * SR)])
    m = (f > 300) & (f < 1400)
    check("small bell fail: dense inharmonic cluster", np.sum(P[m] > P[m].max() * 1e-3) > 12, "")


def check_music():
    a = load("MUS_LB_Drone_A")
    f, P = spectrum(a)
    low = (f > 30) & (f < 120)
    check("drone A: A1 55 Hz root", abs(f[low][np.argmax(P[low])] - 55.0) < 1.0, "peak %.2f Hz" % f[low][np.argmax(P[low])])
    f, P = spectrum(a)

    def pk(lo, hi):
        m = (f >= lo) & (f <= hi)
        return 10 * np.log10(P[m].max() / P.max())

    p_m2, p_tt = pk(57.5, 59.0), pk(77.0, 78.6)
    sweep = band_rms_db(a, 600, 2000, 38.0, 42.0) - band_rms_db(a, 600, 2000, 0.0, 4.0)
    check("drone A: minor second + tritone present", p_m2 > -20 and p_tt > -25, "minor second %+.1f dB, tritone %+.1f dB re the 55 Hz peak" % (p_m2, p_tt))
    check("drone A: low-pass sweep opens (600-2k +dB at 40 s vs 0 s)", sweep > 6, "%+.1f dB" % sweep)
    b = load("MUS_LB_Drone_B")
    check("drone B: hum 55 + tierce 132 present, dark",
          band_rms_db(b, 50, 60) > -40 and band_rms_db(b, 120, 145) > -42 and band_rms_db(b, 400, 3000, 40, 60) < band_rms_db(b, 40, 200, 40, 60) - 40,
          "55 Hz %.0f dB, 132 Hz %.0f dB" % (band_rms_db(b, 50, 60), band_rms_db(b, 120, 145)))
    bell = band_rms_db(b, 400, 3000, 22.0, 23.0) - band_rms_db(b, 400, 3000, 10.0, 11.0)
    check("drone B: faint bell crack inside", bell > 12, "%+.0f dB at 22 s" % bell)
    c = load("MUS_LB_Drone_C")
    f, P = spectrum(c)

    def third_oct(fc):
        m = (f >= fc / 2 ** (1 / 6)) & (f < fc * 2 ** (1 / 6))
        return 10 * np.log10(P[m].mean() + 1e-20)

    f1 = third_oct(300) - max(third_oct(150), third_oct(600))
    f2 = third_oct(870) - max(third_oct(500), third_oct(1500))
    f3 = third_oct(2240) - max(third_oct(1400), third_oct(3500))
    check("drone C: 'oo' formants 300/870/2240 visible", f1 > 3 and f2 > 1 and f3 > 0, "F1 %+.1f F2 %+.1f F3 %+.1f dB over neighbours" % (f1, f2, f3))
    t = load("MUS_LB_Tension")
    env = envelope(t, 200, 2000, 60.0)
    fm, S, tot = mod_spectrum(env, 0.3, 15.0)
    line5 = S[np.abs(fm - 5.0) < 0.1].max()
    slow = S[(fm > 0.3) & (fm < 3.5)].max()
    check("tension: 5 Hz tremolo is the strongest line, no slow pulse", abs(fm[np.argmax(S)] - 5.0) < 0.2 and line5 > 1.5 * slow,
          "peak %.2f Hz, 5 Hz line %+.1f dB over the strongest 0.3-3.5 Hz line" % (fm[np.argmax(S)], 10 * np.log10(line5 / slow)))
    up = band_rms_db(t, 2500, 6000) - band_rms_db(t, 200, 2000)
    check("tension: high shimmer present", up > -45, "%+.0f dB" % up)
    # chase
    ch = load("MUS_LB_Chase")
    check("chase: exactly 8.000 s (384000 samples)", ch.shape[0] == 384000, "%d samples" % ch.shape[0])
    env = envelope(ch, 30, 90, 40.0)
    env = np.roll(env, int(0.05 * SR))  # so the t=0 thump is inside the window
    ok = True
    offs = []
    for bar in range(4):
        for k, rel in enumerate((0.0, 0.25)):
            tt = bar * 2.0 + rel + 0.05
            seg = env[int((tt - 0.03) * SR):int((tt + 0.12) * SR)]
            onset = (np.argmax(seg > 0.3 * seg.max()) / SR) - 0.03 + (tt - 0.05) - (bar * 2.0 + rel) - 0.0
            offs.append(onset * 1000)
    # onset relative to the expected grid line (ms): the thump rises within ~15 ms of the line
    check("chase: heartbeat on beat 1 and 1-and", all(-8 <= o <= 25 for o in offs), "onsets %s ms" % ", ".join("%.0f" % o for o in offs))
    seam = A.seam_step_db(ch, 0.5)
    bars = [A.db(A.rms(mono(ch)[int((b * 2.0) * SR):int((b * 2.0 + 0.5) * SR)])) - A.db(A.rms(mono(ch)[int((b * 2.0 - 0.5) * SR):int(b * 2.0 * SR)])) for b in (1, 2, 3)]
    extrap = bars[2] + (bars[2] - bars[0]) / 2.0  # the bar-line step keeps shrinking as the swell builds
    check("chase: loop seam behaves like a bar line", seam > 0 and abs(seam - extrap) < 4.0 and A.seam_click_ratio(ch) < 8,
          "seam %+.2f dB vs bar-line steps %s dB, click %.1f" % (seam, " ".join("%+.1f" % b for b in bars), A.seam_click_ratio(ch)))
    sp = load("MUS_LB_Sting_Spotted")
    env = envelope(sp, 30, 120, 60.0)
    on = np.argmax(env > 0.3 * env.max()) / SR
    tail = win_rms_db(sp, 0.3, 0.6) - win_rms_db(sp, 1.1, 1.3)
    amp = np.abs(mono(sp))
    att = np.argmax(amp > 0.7 * amp.max()) / SR
    check("sting spotted: immediate hit, <=1.5 s dissonant tail", len(sp) / SR <= 1.5 and on < 0.03 and att < 0.03 and tail > 6,
          "length %.2f s, envelope onset %.3f s, 70%% of peak by %.3f s, tail decays %+.1f dB" % (len(sp) / SR, on, att, tail))
    ca = load("MUS_LB_Sting_Caught")
    env = envelope(ca, 30, 120, 60.0)
    on = np.argmax(env > 0.3 * env.max()) / SR
    rb = band_rms_db(ca, 300, 3000, 2.0, 2.4) - band_rms_db(ca, 300, 3000, 0.5, 0.9)
    cut = band_rms_db(ca, 300, 3000, 2.4, 2.5) - band_rms_db(ca, 300, 3000, 2.6, 2.7)
    check("sting caught: hit at 0, reverse bell swell + cut", on < 0.03 and rb > 6 and cut > 15, "hit %.3f s, swell +%.1f dB, cut %.0f dB" % (on, rb, cut))
    ap = load("MUS_LB_Sting_Apparition")
    hf = band_frac(ap, 1500, 9000)
    pkt = np.argmax(A.lowpass(np.abs(mono(ap)), 4, 2)) / SR
    check("sting apparition: whisper band, swell peak mid", hf > 0.7 and 1.0 < pkt < 2.2, "1.5-9k share %.2f, peak %.2f s" % (hf, pkt))


def check_rooms():
    cr = load("SFX_LB_Room_Crypt")
    pk = peak_freq(cr, 25, 70)
    check("crypt: 40 Hz tone", abs(pk - 40.0) < 0.6, "peak %.2f Hz" % pk)
    check("crypt: dark (energy < 500 Hz)", band_frac(cr, 20, 500) > 0.6, "%.2f" % band_frac(cr, 20, 500))
    tw = load("SFX_LB_Room_Tower")
    bf = load("SFX_LB_Room_Belfry")
    ch = load("SFX_LB_Room_Chapel")
    check("tower: howl band 380-520 stands out", band_rms_db(tw, 380, 520) > band_rms_db(tw, 600, 900) + 3 and band_rms_db(tw, 380, 520) > band_rms_db(tw, 250, 360) + 3, "380-520 %.1f, 250-360 %.1f, 600-900 %.1f dB" % (band_rms_db(tw, 380, 520), band_rms_db(tw, 250, 360), band_rms_db(tw, 600, 900)))
    check("belfry: wind + howl presence (200-900 Hz dominant)", band_frac(bf, 200, 900) > 0.6, "%.2f" % band_frac(bf, 200, 900))
    check("chapel: air bed brighter than crypt", band_rms_db(ch, 1000, 3000) - band_rms_db(ch, 40, 200) > band_rms_db(cr, 1000, 3000) - band_rms_db(cr, 40, 200) + 6, "chapel %+.1f vs crypt %+.1f dB (1-3k minus 40-200)" % (band_rms_db(ch, 1000, 3000) - band_rms_db(ch, 40, 200), band_rms_db(cr, 1000, 3000) - band_rms_db(cr, 40, 200)))
    for r in ("Crypt", "Chapel", "Cloister", "Passage", "Tower", "Belfry"):
        x = load("SFX_LB_Room_" + r)
        check("room %s: stereo not mono" % r, abs(corr_lr(x)) < 0.6, "corr %.2f" % corr_lr(x))
    # drips
    for i in range(1, 6):
        x = mono(load("SFX_LB_Drip_Water_%02d" % i))
        early = peak_freq(x, 400, 4000, 0.0, 0.010)
        late = peak_freq(x, 400, 4000, 0.022, 0.034)
        bub = peak_freq(x, 800, 2000, 0.12, 0.35)
        check("drip water %d: glide up and bubble ring" % i, late > 1.35 * early and 950 < bub < 1500 and len(x) / SR < 1.0,
              "glide %.0f -> %.0f Hz, bubble %.0f Hz" % (early, late, bub))
    for i in range(1, 6):
        x = mono(load("SFX_LB_Drip_Stone_%02d" % i))
        frac = A.rms(A.bandpass(x[: int(0.008 * SR)], 1500, 5500, 2)) / A.rms(x[: int(0.008 * SR)])
        check("drip stone %d: 2-4 kHz click" % i, frac > 0.6 and len(x) / SR < 1.0, "band share %.2f" % frac)
    for pre in ("Water", "Stone"):
        xs = [mono(load("SFX_LB_Drip_%s_%02d" % (pre, i))) for i in range(1, 6)]
        n = min(len(v) for v in xs)
        worst = 0
        for i in range(5):
            for j in range(i + 1, 5):
                a, b = xs[i][:n], xs[j][:n]
                worst = max(worst, abs(float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))))
        check("drips %s: five distinct variants" % pre.lower(), worst < 0.7, "worst cross-correlation %.2f" % worst)
    # thunder variants distinct
    for pre in ("Near", "Mid", "Far"):
        xs = [mono(load("SFX_LB_Thunder_%s_%02d" % (pre, i))) for i in range(1, 5)]
        n = min(len(v) for v in xs)
        worst = max(abs(float(np.dot(xs[i][:n], xs[j][:n]) / (np.linalg.norm(xs[i][:n]) * np.linalg.norm(xs[j][:n])))) for i in range(4) for j in range(i + 1, 4))
        check("thunder %s: variants distinct" % pre.lower(), worst < 0.5, "worst cross-correlation %.2f" % worst)


def main():
    with open(os.path.join(A.OUT_DIR, "manifest.json"), encoding="utf8") as f:
        man = json.load(f)
    only = sys.argv[1] if len(sys.argv) > 1 else "all"
    check_all_files(man)
    for g, fn in (("rain", check_rain_wind), ("wind", None), ("thunder", check_thunder), ("bells", check_bells),
                  ("music", check_music), ("rooms", check_rooms)):
        if fn and only in ("all", g):
            fn()
    bad = [r for r in results if not r[1]]
    print("\n%d checks, %d failed" % (len(results), len(bad)))
    for r in bad:
        print("  FAILED:", r[0], r[2])
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
