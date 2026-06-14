#!/usr/bin/env python3
"""对比 CSP+LDA, ERD+LDA, Power Ratio 在 T7/T8 通道上的表现"""

import json
from pathlib import Path
import numpy as np
import mne
from scipy import signal as sig
from scipy import linalg
from scipy.integrate import trapezoid
from scipy.stats import ttest_ind
from sklearn.model_selection import LeaveOneOut
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis as SkLDA
from collections import Counter

FS = 250.0
T7_IDX, T8_IDX = 2, 3
FP1_IDX, FP2_IDX = 4, 5
ALPHA = (8, 13)
BETA = (13, 30)
BROADBAND = (0.5, 30)

BDF_PATH = Path("/Users/sssd/Downloads/实验数据/试次10.bdf")
SESSION_DIR = Path("/Users/sssd/Desktop/跳一跳/试次数据")
SESSION_FILES = [
    "session_20260614_103654.jsonl", "session_20260614_103846.jsonl",
    "session_20260614_104027.jsonl", "session_20260614_104209.jsonl",
]

# ── DSP utils ──
def band_power(x, fs, lo, hi):
    nperseg = min(128, len(x) // 2)
    if nperseg < 32: nperseg = len(x) // 4
    if nperseg < 16: return 0.0
    f, p = sig.welch(x, fs, nperseg=nperseg)
    mask = (f >= lo) & (f <= hi)
    if mask.sum() < 2: return 0.0
    return float(trapezoid(p[mask], f[mask]))

def notch_2d(d, fs, freq=50, q=30):
    b, a = sig.iirnotch(freq, q, fs)
    out = np.zeros_like(d)
    for ch in range(d.shape[0]):
        out[ch] = sig.filtfilt(b, a, d[ch])
    return out

def bandpass_2d(d, lo, hi, fs, order=4):
    nyq = 0.5 * fs
    b, a = sig.butter(order, [lo/nyq, hi/nyq], btype="band")
    out = np.zeros_like(d)
    for ch in range(d.shape[0]):
        out[ch] = sig.filtfilt(b, a, d[ch])
    return out

def csp_fit(X1, X2, n_comp=4):
    n_ch = X1[0].shape[0]
    cov1 = sum(np.cov(x - x.mean(axis=1, keepdims=True)) for x in X1) / len(X1)
    cov2 = sum(np.cov(x - x.mean(axis=1, keepdims=True)) for x in X2) / len(X2)
    cov_c = cov1 + cov2 + 1e-6 * np.eye(n_ch)
    evals, evecs = linalg.eigh(cov1, cov_c)
    idx = np.argsort(evals)[::-1]
    evecs = evecs[:, idx]
    W = np.hstack([evecs[:, :n_comp//2], evecs[:, -n_comp//2:]])
    return W

def csp_transform(W, X):
    Z = W.T @ X
    var = np.var(Z, axis=1)
    return np.log(var / (var.sum() + 1e-15))

def extract_erd_9(bl, tk, li, ri, fs):
    def erd(c_bl, c_tk, lo, hi):
        a = band_power(c_bl, fs, lo, hi)
        b = band_power(c_tk, fs, lo, hi)
        return (b - a) / (a + 1e-15)
    bl_l = bl[li] - bl[li].mean()
    bl_r = bl[ri] - bl[ri].mean()
    tk_l = tk[li] - tk[li].mean()
    tk_r = tk[ri] - tk[ri].mean()
    return np.array([
        erd(bl_l, tk_l, *BROADBAND), erd(bl_r, tk_r, *BROADBAND),
        erd(bl_l, tk_l, *BROADBAND) - erd(bl_r, tk_r, *BROADBAND),
        erd(bl_l, tk_l, *ALPHA), erd(bl_r, tk_r, *ALPHA),
        erd(bl_l, tk_l, *ALPHA) - erd(bl_r, tk_r, *ALPHA),
        erd(bl_l, tk_l, *BETA), erd(bl_r, tk_r, *BETA),
        erd(bl_l, tk_l, *BETA) - erd(bl_r, tk_r, *BETA),
    ])

# ═══════════════════════════════════════════
print("=" * 60)
print("MI 分类对比 — T7/T8 (感觉运动皮层)")
print("=" * 60)

# ── Load BDF ──
raw = mne.io.read_raw_bdf(str(BDF_PATH), preload=True, verbose=False)
data_raw = raw.get_data()
meas = raw.info.get("meas_date")
bdf_start_ms = int((meas.timestamp() - 8 * 3600) * 1000)
print(f"BDF: {raw.ch_names}, {data_raw.shape[1]/FS:.0f}s @ {FS}Hz")
print(f"T7=idx{T7_IDX}, T8=idx{T8_IDX}  |  Fp1=idx{FP1_IDX}, Fp2=idx{FP2_IDX}")

# ── Load trials ──
all_trials = []
for sf in SESSION_FILES:
    with open(SESSION_DIR / sf) as f:
        for line in f:
            d = json.loads(line.strip())
            if d.get("type") == "trial":
                all_trials.append(d)

# Slice windows
windows_bl, windows_tk, y_all = [], [], []
for t in all_trials:
    ts_ms = t["timestamp_trial_start_ms"]
    offset_s = (ts_ms - bdf_start_ms) / 1000.0
    bl_s = int(offset_s * FS)
    bl_e = int((offset_s + 2.0) * FS)
    tk_e = int((offset_s + 4.0) * FS)
    if bl_s < 0 or tk_e > data_raw.shape[1]: continue
    bl = data_raw[:, bl_s:bl_e][:, :500]
    tk = data_raw[:, bl_e:tk_e][:, :500]
    if bl.shape[1] < 400 or tk.shape[1] < 400: continue
    windows_bl.append(bl)
    windows_tk.append(tk)
    y_all.append(1 if t["ground_truth"] == "left" else 2)

y_all = np.array(y_all)
n = len(y_all)
print(f"试次: {n} (left={np.sum(y_all==1)}, right={np.sum(y_all==2)})")

# ═══════════════════════════════════════════
# Per-trial Alpha ERD analysis
# ═══════════════════════════════════════════
print("\n" + "-" * 75)
print("T7/T8 Alpha ERD 逐试次分析")
print(f"  (T7=左半球感觉运动区, T8=右半球感觉运动区)")
print(f"  (左手MI→右侧激活→T8 ERD更强→lateral<0, 右手MI→左侧激活→T7 ERD更强→lateral>0)")
print("-" * 75)

correct_sign = 0
erd_vals = []
for i in range(n):
    bl_f = notch_2d(windows_bl[i], FS)
    tk_f = notch_2d(windows_tk[i], FS)
    def erd_ch(idx):
        bl_c = bl_f[idx] - bl_f[idx].mean()
        tk_c = tk_f[idx] - tk_f[idx].mean()
        a = band_power(bl_c, FS, *ALPHA)
        b = band_power(tk_c, FS, *ALPHA)
        return (b - a) / (a + 1e-15)
    e7 = erd_ch(T7_IDX)
    e8 = erd_ch(T8_IDX)
    lat = e7 - e8
    # T7 ERD > T8 ERD (lateral > 0) → T7 side stronger activation → right hand MI → label=2
    pred = 2 if lat > 0 else 1
    if pred == y_all[i]: correct_sign += 1
    erd_vals.append((e7, e8, lat, y_all[i]))
    gt_str = "left" if y_all[i] == 1 else "right"
    pd_str = "left" if pred == 1 else "right"
    mark = "O" if pred == y_all[i] else "X"
    print(f"  #{i+1:>2d} GT={gt_str:>5s}  ERD_T7={e7:+8.3f}  ERD_T8={e8:+8.3f}  lat={lat:+8.3f}  pred={pd_str:>5s}  {mark}")

left_vals = [v for v in erd_vals if v[3] == 1]
right_vals = [v for v in erd_vals if v[3] == 2]
print(f"\n  Left  (n={len(left_vals)}):  ERD_T7={np.mean([v[0] for v in left_vals]):+.3f}+-{np.std([v[0] for v in left_vals]):.3f}   ERD_T8={np.mean([v[1] for v in left_vals]):+.3f}+-{np.std([v[1] for v in left_vals]):.3f}")
print(f"  Right (n={len(right_vals)}): ERD_T7={np.mean([v[0] for v in right_vals]):+.3f}+-{np.std([v[0] for v in right_vals]):.3f}   ERD_T8={np.mean([v[1] for v in right_vals]):+.3f}+-{np.std([v[1] for v in right_vals]):.3f}")

t_lat, p_lat = ttest_ind([v[2] for v in left_vals], [v[2] for v in right_vals])
print(f"  Lateral ERD t-test: t={t_lat:.3f}, p={p_lat:.4f} ({'SIGNIFICANT' if p_lat < 0.05 else 'NOT significant'})")
print(f"  Correct by sign:   {correct_sign}/{n} = {correct_sign/n:.1%}")

# ═══════════════════════════════════════════
# Method 3: Power Ratio
# ═══════════════════════════════════════════
print("\n" + "-" * 60)
print("Method 3: Power Ratio (T7/T8 频带功率比)")
print("-" * 60)

best_pr_erd = None
best_pr_task = None

for label, (lo, hi) in [("Alpha (8-13Hz)", ALPHA), ("Beta (13-30Hz)", BETA), ("Broad (0.5-30Hz)", BROADBAND)]:
    # ERD ratio (baseline normalized)
    best_a, best_t = 0, 0
    for th in [1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.8, 2.0, 2.5, 3.0]:
        correct = 0
        for i in range(n):
            bl_f = notch_2d(windows_bl[i], FS)
            tk_f = notch_2d(windows_tk[i], FS)
            p_bl_l = band_power(bl_f[T7_IDX] - bl_f[T7_IDX].mean(), FS, lo, hi)
            p_tk_l = band_power(tk_f[T7_IDX] - tk_f[T7_IDX].mean(), FS, lo, hi)
            p_bl_r = band_power(bl_f[T8_IDX] - bl_f[T8_IDX].mean(), FS, lo, hi)
            p_tk_r = band_power(tk_f[T8_IDX] - tk_f[T8_IDX].mean(), FS, lo, hi)
            erd_l = (p_tk_l + 1e-15) / (p_bl_l + 1e-15)
            erd_r = (p_tk_r + 1e-15) / (p_bl_r + 1e-15)
            ratio = erd_l / (erd_r + 1e-15)
            if ratio > th: pred = 1
            elif ratio < 1.0 / th: pred = 2
            else: pred = 0
            if pred == y_all[i]: correct += 1
        acc = correct / n
        if acc > best_a: best_a, best_t = acc, th
    print(f"  {label:22s} ERD-ratio  best thr={best_t:.1f}  acc={best_a:.1%}")
    if best_a > (best_pr_erd[2] if best_pr_erd else 0):
        best_pr_erd = (label, best_t, best_a)

    # Task-only power ratio
    best_a2, best_t2 = 0, 0
    for th in [1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.8, 2.0]:
        correct = 0
        for i in range(n):
            tk_f = notch_2d(windows_tk[i], FS)
            p_l = band_power(tk_f[T7_IDX] - tk_f[T7_IDX].mean(), FS, lo, hi)
            p_r = band_power(tk_f[T8_IDX] - tk_f[T8_IDX].mean(), FS, lo, hi)
            ratio = p_l / (p_r + 1e-15)
            if ratio > th: pred = 1
            elif ratio < 1.0 / th: pred = 2
            else: pred = 0
            if pred == y_all[i]: correct += 1
        acc = correct / n
        if acc > best_a2: best_a2, best_t2 = acc, th
    print(f"  {label:22s} task-only  best thr={best_t2:.1f}  acc={best_a2:.1%}")
    if best_a2 > (best_pr_task[2] if best_pr_task else 0):
        best_pr_task = (label, best_t2, best_a2)

# ═══════════════════════════════════════════
# Method 1: CSP + LDA
# ═══════════════════════════════════════════
print("\n" + "-" * 60)
print("Method 1: CSP + LDA (8-30Hz bandpass)")
print("-" * 60)

csp_bl = [bandpass_2d(windows_bl[i], 8, 30, FS) for i in range(n)]
csp_tk = [bandpass_2d(windows_tk[i], 8, 30, FS) for i in range(n)]
csp_full = [bandpass_2d(np.hstack([windows_bl[i], windows_tk[i]]), 8, 30, FS) for i in range(n)]

loo = LeaveOneOut()
csp_best = ("", 0)

for name, dat, n_comp in [("8ch baseline(2s)", csp_bl, 4), ("8ch task(2s)", csp_tk, 4),
                            ("8ch full(4s)", csp_full, 4)]:
    accs = []
    for tr, te in loo.split(dat):
        X1_tr = [dat[i] for i in tr if y_all[i] == 1]
        X2_tr = [dat[i] for i in tr if y_all[i] == 2]
        if len(X1_tr) < 2 or len(X2_tr) < 2: continue
        try:
            W = csp_fit(X1_tr, X2_tr, n_comp=n_comp)
            X_tr = np.array([csp_transform(W, dat[i]) for i in tr])
            X_te = np.array([csp_transform(W, dat[te[0]])])
            clf = SkLDA(); clf.fit(X_tr, y_all[tr])
            pred = clf.predict(X_te)[0]
            accs.append(1 if pred == y_all[te[0]] else 0)
        except: continue
    acc = np.mean(accs) if accs else 0
    print(f"  CSP+LDA {name:>22s}: {acc:.1%} ({sum(accs)}/{len(accs)})")
    if acc > csp_best[1]: csp_best = (name, acc)

# CSP with T7/T8 only
csp_t78_tk = [bandpass_2d(windows_tk[i][[T7_IDX, T8_IDX]], 8, 30, FS) for i in range(n)]
csp_t78_full = [bandpass_2d(np.hstack([windows_bl[i][[T7_IDX, T8_IDX]], windows_tk[i][[T7_IDX, T8_IDX]]]), 8, 30, FS) for i in range(n)]

for name, dat, n_comp in [("T7T8 task(2s)", csp_t78_tk, 2), ("T7T8 full(4s)", csp_t78_full, 2)]:
    accs = []
    for tr, te in loo.split(dat):
        X1_tr = [dat[i] for i in tr if y_all[i] == 1]
        X2_tr = [dat[i] for i in tr if y_all[i] == 2]
        if len(X1_tr) < 2 or len(X2_tr) < 2: continue
        try:
            W = csp_fit(X1_tr, X2_tr, n_comp=n_comp)
            X_tr = np.array([csp_transform(W, dat[i]) for i in tr])
            X_te = np.array([csp_transform(W, dat[te[0]])])
            clf = SkLDA(); clf.fit(X_tr, y_all[tr])
            pred = clf.predict(X_te)[0]
            accs.append(1 if pred == y_all[te[0]] else 0)
        except: continue
    acc = np.mean(accs) if accs else 0
    print(f"  CSP+LDA {name:>22s}: {acc:.1%} ({sum(accs)}/{len(accs)})")
    if acc > csp_best[1]: csp_best = (name, acc)

# ═══════════════════════════════════════════
# Method 2: ERD(9feat) + LDA
# ═══════════════════════════════════════════
print("\n" + "-" * 60)
print("Method 2: ERD(9feat) + LDA")
print("-" * 60)

# T7/T8
X_erd = np.array([extract_erd_9(notch_2d(windows_bl[i], FS), notch_2d(windows_tk[i], FS),
                                 T7_IDX, T8_IDX, FS) for i in range(n)])
erd_accs, erd_preds, erd_trues = [], [], []
for tr, te in loo.split(X_erd):
    if len(np.unique(y_all[tr])) < 2: continue
    clf = SkLDA(); clf.fit(X_erd[tr], y_all[tr])
    pred = clf.predict(X_erd[te])[0]
    erd_accs.append(1 if pred == y_all[te[0]] else 0)
    erd_preds.append(pred); erd_trues.append(y_all[te[0]])

erd_acc = np.mean(erd_accs) if erd_accs else 0
print(f"  ERD(T7/T8)+LDA LOO: {erd_acc:.1%} ({sum(erd_accs)}/{len(erd_accs)})")

clf_all = SkLDA(); clf_all.fit(X_erd, y_all)
fnames = ["ERD_T7(broad)", "ERD_T8(broad)", "lat(broad)",
          "ERD_a_T7", "ERD_a_T8", "lat_a",
          "ERD_b_T7", "ERD_b_T8", "lat_b"]
print("\n  LDA 特征权重:")
for name, c in zip(fnames, clf_all.coef_[0]):
    bar = "#" * min(50, int(abs(c) * 50))
    print(f"    {name:20s} {c:+8.4f}  {bar}")

cm = Counter()
for t, p in zip(erd_trues, erd_preds):
    cm[(t, p)] += 1
print(f"\n  混淆矩阵 (T7/T8):")
print(f"                 pred_left  pred_right")
print(f"    true_left       {cm.get((1,1),0):>4}         {cm.get((1,2),0):>4}")
print(f"    true_right      {cm.get((2,1),0):>4}         {cm.get((2,2),0):>4}")

# Fp1/Fp2 for comparison
X_erd_fp = np.array([extract_erd_9(notch_2d(windows_bl[i], FS), notch_2d(windows_tk[i], FS),
                                    FP1_IDX, FP2_IDX, FS) for i in range(n)])
fp_accs, fp_preds, fp_trues = [], [], []
for tr, te in loo.split(X_erd_fp):
    if len(np.unique(y_all[tr])) < 2: continue
    clf = SkLDA(); clf.fit(X_erd_fp[tr], y_all[tr])
    pred = clf.predict(X_erd_fp[te])[0]
    fp_accs.append(1 if pred == y_all[te[0]] else 0)
    fp_preds.append(pred); fp_trues.append(y_all[te[0]])

fp_acc = np.mean(fp_accs) if fp_accs else 0
print(f"\n  ERD(Fp1/Fp2)+LDA LOO: {fp_acc:.1%} ({sum(fp_accs)}/{len(fp_accs)})")

cm_fp = Counter()
for t, p in zip(fp_trues, fp_preds):
    cm_fp[(t, p)] += 1
print(f"\n  混淆矩阵 (Fp1/Fp2):")
print(f"                 pred_left  pred_right")
print(f"    true_left       {cm_fp.get((1,1),0):>4}         {cm_fp.get((1,2),0):>4}")
print(f"    true_right      {cm_fp.get((2,1),0):>4}         {cm_fp.get((2,2),0):>4}")

# ═══════════════════════════════════════════
# Final Summary
# ═══════════════════════════════════════════
print("\n" + "=" * 60)
print("总结对比: T7/T8 vs Fp1/Fp2")
print("=" * 60)
print(f"  {'Method':<35s} {'T7/T8':>8s} {'Fp1/Fp2':>8s}")
print(f"  {'-'*51}")
print(f"  {'CSP(8ch)+LDA (best)':<35s} {csp_best[1]:>7.1%}    60.0%")
print(f"  {'ERD(9feat)+LDA':<35s} {erd_acc:>7.1%}   {fp_acc:>7.1%}")
print(f"  {'Power Ratio ERD (best)':<35s} {best_pr_erd[2]:>7.1%}    47.5%")
print(f"  {'Power Ratio task-only (best)':<35s} {best_pr_task[2]:>7.1%}    55.0%")
print(f"  {'Lateral sign heuristic':<35s} {correct_sign/n:>7.1%}    55.0%")

print(f"\n  数据: {n} 试次 (left={np.sum(y_all==1)}, right={np.sum(y_all==2)})")
print(f"  T7/T8 lateral ERD t-test: p={p_lat:.4f}")
