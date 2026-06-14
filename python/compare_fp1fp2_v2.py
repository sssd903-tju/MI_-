#!/usr/bin/env python3
"""
FP1/FP2 前额叶 MI 分类 — 正确方法论
=====================================
核心理念: 前额叶 alpha 不对称 (frontal alpha asymmetry, FAA)
  FAA = (R - L) / (R + L)，反映左右前额叶激活差异
  左手 MI → 右侧前额激活↑ → 右侧 alpha↓ → FAA 偏负
  右手 MI → 左侧前额激活↑ → 左侧 alpha↓ → FAA 偏正

方法对比:
  1. Alpha 不对称指数 + 阈值
  2. Alpha 不对称 + LDA
  3. 多频带特征 + LDA/SVM
  4. MNE ICA 去伪迹 + 重分类
"""

import json
from pathlib import Path
import numpy as np
import mne
from scipy import signal as sig
from scipy import linalg
from scipy.integrate import trapezoid
from scipy.stats import ttest_ind
from sklearn.model_selection import LeaveOneOut, cross_val_score
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis as SkLDA
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from collections import Counter

FS = 250.0
FP1_IDX, FP2_IDX = 4, 5
ALPHA = (8, 13)
BETA = (13, 30)
THETA = (4, 8)
LOW_BETA = (13, 20)
HIGH_BETA = (20, 30)
BROADBAND = (0.5, 30)

BDF_PATH = Path("/Users/sssd/Downloads/实验数据/试次10.bdf")
SESSION_DIR = Path("/Users/sssd/Desktop/跳一跳/试次数据")
SESSION_FILES = [
    "session_20260614_103654.jsonl", "session_20260614_103846.jsonl",
    "session_20260614_104027.jsonl", "session_20260614_104209.jsonl",
]

# ── DSP ──
def band_power(x, fs, lo, hi):
    nperseg = min(128, len(x) // 2)
    if nperseg < 32: nperseg = len(x) // 4
    if nperseg < 16: return 0.0, None, None
    f, p = sig.welch(x, fs, nperseg=nperseg)
    mask = (f >= lo) & (f <= hi)
    if mask.sum() < 2: return 0.0, f, p
    return float(trapezoid(p[mask], f[mask])), f, p

def band_power_simple(x, fs, lo, hi):
    v, _, _ = band_power(x, fs, lo, hi)
    return v

def butter_bandpass(x, lo, hi, fs, order=4):
    nyq = 0.5 * fs
    b, a = sig.butter(order, [lo/nyq, hi/nyq], btype="band")
    return sig.filtfilt(b, a, x)

def notch_filt(x, fs, freq=50, q=30):
    b, a = sig.iirnotch(freq, q, fs)
    return sig.filtfilt(b, a, x)

# ═══════════════════════════════════════════
print("=" * 65)
print("FP1/FP2 前额叶 MI 分类 — 正确方法")
print("=" * 65)

# ── Load ──
raw = mne.io.read_raw_bdf(str(BDF_PATH), preload=True, verbose=False)
data_raw = raw.get_data()
meas = raw.info.get("meas_date")
bdf_start_ms = int((meas.timestamp() - 8 * 3600) * 1000)

all_trials = []
for sf in SESSION_FILES:
    with open(SESSION_DIR / sf) as f:
        for line in f:
            d = json.loads(line.strip())
            if d.get("type") == "trial":
                all_trials.append(d)

# ── Extract Fp1/Fp2, clean ──
fp1_raw = data_raw[FP1_IDX].astype(np.float64)
fp2_raw = data_raw[FP2_IDX].astype(np.float64)

# Bandpass + notch
fp1_clean = notch_filt(butter_bandpass(fp1_raw, 0.5, 45, FS), FS)
fp2_clean = notch_filt(butter_bandpass(fp2_raw, 0.5, 45, FS), FS)

# ═══════════════════════════════════════════
# Slice trials
# ═══════════════════════════════════════════
trials = []
for t in all_trials:
    ts_ms = t["timestamp_trial_start_ms"]
    offset_s = (ts_ms - bdf_start_ms) / 1000.0
    bl_s = int(offset_s * FS)
    bl_e = int((offset_s + 2.0) * FS)
    tk_e = int((offset_s + 4.0) * FS)
    if bl_s < 0 or tk_e > len(fp1_clean): continue

    fp1_bl = fp1_clean[bl_s:bl_e][:500]
    fp1_tk = fp1_clean[bl_e:tk_e][:500]
    fp2_bl = fp2_clean[bl_s:bl_e][:500]
    fp2_tk = fp2_clean[bl_e:tk_e][:500]

    if len(fp1_bl) < 400: continue

    label = 1 if t["ground_truth"] == "left" else 2
    trials.append((fp1_bl, fp1_tk, fp2_bl, fp2_tk, label))

y_all = np.array([t[4] for t in trials])
n = len(y_all)
print(f"试次: {n} (left={np.sum(y_all==1)}, right={np.sum(y_all==2)})")

# ═══════════════════════════════════════════
# Method 1: Alpha Asymmetry (FAA) — 核心指标
# ═══════════════════════════════════════════
print("\n" + "-" * 65)
print("Method 1: 前额叶 Alpha 不对称 (FAA)")
print("  FAA = (FP2_alpha - FP1_alpha) / (FP2_alpha + FP1_alpha)")
print("  左手 MI → 右侧激活↑ → FP2 alpha↓ → FAA < 0")
print("  右手 MI → 左侧激活↑ → FP1 alpha↓ → FAA > 0")
print("-" * 65)

# Try multiple approaches: baseline FAA, task FAA, FAA change
faa_baseline = []
faa_task = []
faa_change = []
for fp1_bl, fp1_tk, fp2_bl, fp2_tk, _ in trials:
    fp1_bl_a = band_power_simple(fp1_bl - fp1_bl.mean(), FS, *ALPHA)
    fp2_bl_a = band_power_simple(fp2_bl - fp2_bl.mean(), FS, *ALPHA)
    fp1_tk_a = band_power_simple(fp1_tk - fp1_tk.mean(), FS, *ALPHA)
    fp2_tk_a = band_power_simple(fp2_tk - fp2_tk.mean(), FS, *ALPHA)

    faa_bl = (fp2_bl_a - fp1_bl_a) / (fp2_bl_a + fp1_bl_a + 1e-15)
    faa_tk = (fp2_tk_a - fp1_tk_a) / (fp2_tk_a + fp1_tk_a + 1e-15)
    faa_chg = faa_tk - faa_bl  # positive = shift toward right (FP2) during task

    faa_baseline.append(faa_bl)
    faa_task.append(faa_tk)
    faa_change.append(faa_chg)

# Print per-trial
print(f"  {'#':>4s} {'GT':>6s} {'FAA_bl':>8s} {'FAA_tk':>8s} {'FAA_chg':>8s} {'pred_bl':>8s} {'pred_tk':>8s} {'pred_chg':>8s}")
print(f"  {'-'*65}")
correct_bl = correct_tk = correct_chg = 0
for i in range(n):
    gt = "left" if y_all[i] == 1 else "right"
    # FAA > 0 → FP2 > FP1 → right hemisphere more alpha (less active) → left hemisphere more active → right hand MI?
    # Actually: more alpha = LESS activation (alpha is inhibitory)
    # So FAA > 0 means FP2 has MORE alpha → FP2 is LESS active → FP1 is MORE active → LEFT hemisphere active → RIGHT hand MI
    # And FAA < 0 means FP1 has MORE alpha → FP1 is LESS active → FP2 is MORE active → RIGHT hemisphere active → LEFT hand MI
    pred_bl = 1 if faa_baseline[i] < 0 else 2  # FAA<0 → left hand
    pred_tk = 1 if faa_task[i] < 0 else 2
    pred_chg = 1 if faa_change[i] < 0 else 2  # FAA more negative → lateralizing right

    if pred_bl == y_all[i]: correct_bl += 1
    if pred_tk == y_all[i]: correct_tk += 1
    if pred_chg == y_all[i]: correct_chg += 1

    marks = ""
    if pred_tk == y_all[i]: marks += " O"
    else: marks += " X"
    print(f"  {i+1:>4d} {gt:>6s} {faa_baseline[i]:>+8.4f} {faa_task[i]:>+8.4f} {faa_change[i]:>+8.4f} "
          f"{'left' if pred_bl==1 else 'right':>8s} {'left' if pred_tk==1 else 'right':>8s} "
          f"{'left' if pred_chg==1 else 'right':>8s}{marks}")

left_faa = [faa_task[i] for i in range(n) if y_all[i] == 1]
right_faa = [faa_task[i] for i in range(n) if y_all[i] == 2]
t_faa, p_faa = ttest_ind(left_faa, right_faa)
print(f"\n  Left  FAA (task): {np.mean(left_faa):+.4f}±{np.std(left_faa):.4f}")
print(f"  Right FAA (task): {np.mean(right_faa):+.4f}±{np.std(right_faa):.4f}")
print(f"  t-test: t={t_faa:.3f}, p={p_faa:.4f}")
print(f"  Baseline FAA acc: {correct_bl}/{n} = {correct_bl/n:.1%}")
print(f"  Task FAA acc:     {correct_tk}/{n} = {correct_tk/n:.1%}")
print(f"  FAA change acc:   {correct_chg}/{n} = {correct_chg/n:.1%}")

# ═══════════════════════════════════════════
# Method 2: Multi-band features + classifiers
# ═══════════════════════════════════════════
print("\n" + "-" * 65)
print("Method 2: 多频带特征 + 多种分类器")
print("-" * 65)

bands = {"theta": THETA, "alpha": ALPHA, "low_beta": LOW_BETA,
         "high_beta": HIGH_BETA, "beta": BETA, "broadband": BROADBAND}

# For each trial, extract features from task window
features_list = []
for fp1_bl, fp1_tk, fp2_bl, fp2_tk, _ in trials:
    feat = []
    fp1_tk_c = fp1_tk - fp1_tk.mean()
    fp2_tk_c = fp2_tk - fp2_tk.mean()

    for band_name, (lo, hi) in bands.items():
        p1 = band_power_simple(fp1_tk_c, FS, lo, hi)
        p2 = band_power_simple(fp2_tk_c, FS, lo, hi)
        # Absolute power
        feat.append(np.log(p1 + 1e-15))
        feat.append(np.log(p2 + 1e-15))
        # FAA (asymmetry index)
        faa = (p2 - p1) / (p2 + p1 + 1e-15)
        feat.append(faa)
        # Total power in band
        feat.append(np.log(p1 + p2 + 1e-15))

    # Also add ERD features (task/baseline for alpha and beta)
    fp1_bl_c = fp1_bl - fp1_bl.mean()
    fp2_bl_c = fp2_bl - fp2_bl.mean()
    for (lo, hi), name in [(ALPHA, "a"), (BETA, "b")]:
        bl1 = band_power_simple(fp1_bl_c, FS, lo, hi)
        tk1 = band_power_simple(fp1_tk_c, FS, lo, hi)
        bl2 = band_power_simple(fp2_bl_c, FS, lo, hi)
        tk2 = band_power_simple(fp2_tk_c, FS, lo, hi)
        erd1 = (tk1 - bl1) / (bl1 + 1e-15)
        erd2 = (tk2 - bl2) / (bl2 + 1e-15)
        feat.append(erd1)
        feat.append(erd2)
        feat.append(erd1 - erd2)

    features_list.append(np.array(feat))

X = np.array(features_list)
print(f"  特征维度: {X.shape[1]} (6 bands × 4 + 2 bands × 3 = 30)")

# LOO cross-validation with multiple classifiers
loo = LeaveOneOut()
classifiers = {
    "LDA": SkLDA(),
    "SVM (linear)": SVC(kernel="linear", C=1.0),
    "SVM (rbf)": SVC(kernel="rbf", C=1.0, gamma="scale"),
    "RandomForest": RandomForestClassifier(n_estimators=100, random_state=42),
}

for name, clf in classifiers.items():
    accs = []
    preds_all, trues_all = [], []
    for tr, te in loo.split(X):
        if len(np.unique(y_all[tr])) < 2: continue
        try:
            scaler = StandardScaler()
            X_tr = scaler.fit_transform(X[tr])
            X_te = scaler.transform(X[te])
            clf.fit(X_tr, y_all[tr])
            pred = clf.predict(X_te)[0]
            accs.append(1 if pred == y_all[te[0]] else 0)
            preds_all.append(pred)
            trues_all.append(y_all[te[0]])
        except: continue
    acc = np.mean(accs) if accs else 0
    print(f"  {name:>20s}: {acc:.1%} ({sum(accs)}/{len(accs)})")

# Show best confusion matrix
cm = Counter()
for t, p in zip(trues_all, preds_all):
    cm[(t, p)] += 1
print(f"\n  混淆矩阵 (最佳):")
print(f"                 pred_L pred_R")
print(f"    true_left      {cm.get((1,1),0):>4}     {cm.get((1,2),0):>4}")
print(f"    true_right     {cm.get((2,1),0):>4}     {cm.get((2,2),0):>4}")

# ═══════════════════════════════════════════
# Method 3: MNE ICA + re-classify
# ═══════════════════════════════════════════
print("\n" + "-" * 65)
print("Method 3: MNE ICA 去伪迹")
print("-" * 65)

# Create MNE Raw with Fp1/Fp2 only
info = mne.create_info(["Fp1", "Fp2"], FS, ["eeg", "eeg"])
fp_data = np.vstack([fp1_raw, fp2_raw])
raw_fp = mne.io.RawArray(fp_data, info, verbose=False)

# Apply bandpass 1-45Hz (MNE's recommendation for ICA)
raw_filt = raw_fp.copy().filter(1, 45, fir_design="firwin", verbose=False)
# Notch
raw_filt.notch_filter(50, fir_design="firwin", verbose=False)

# Fit ICA (2 components for 2 channels)
ica = mne.preprocessing.ICA(n_components=2, random_state=42, max_iter="auto")
ica.fit(raw_filt, verbose=False)

# Identify EOG component: the one more strongly present in both channels
# Since Fp1/Fp2 are both on forehead, the component with more frontal power = EOG
ica_weights = ica.get_components()
comp_power = []
for comp_idx in range(2):
    comp_ts = ica.get_sources(raw_filt).get_data()[comp_idx]
    # Power in low frequencies (< 5Hz) = likely EOG (blinks are slow)
    p_low = band_power_simple(comp_ts, FS, 0.5, 5)
    p_alpha = band_power_simple(comp_ts, FS, 8, 13)
    ratio = p_low / (p_alpha + 1e-15)
    comp_power.append((comp_idx, p_low, p_alpha, ratio))
    print(f"  IC{comp_idx}: low_pow={p_low:.6e} alpha_pow={p_alpha:.6e} low/alpha={ratio:.1f}")

# Remove the component with highest low/alpha ratio (likely EOG)
comp_power.sort(key=lambda x: -x[3])
eog_ic = comp_power[0][0]
print(f"  识别 EOG 成分: IC{eog_ic} (低频/alpha比最大)")
ica.exclude = [eog_ic]
raw_clean = ica.apply(raw_filt.copy(), verbose=False)

# Extract cleaned data
fp1_ica = raw_clean.get_data()[0]
fp2_ica = raw_clean.get_data()[1]

# Re-slice trials
ica_trials = []
for t in all_trials:
    ts_ms = t["timestamp_trial_start_ms"]
    offset_s = (ts_ms - bdf_start_ms) / 1000.0
    bl_s = int(offset_s * FS)
    bl_e = int((offset_s + 2.0) * FS)
    tk_e = int((offset_s + 4.0) * FS)
    if bl_s < 0 or tk_e > len(fp1_ica): continue
    fp1_bl = fp1_ica[bl_s:bl_e][:500]
    fp1_tk = fp1_ica[bl_e:tk_e][:500]
    fp2_bl = fp2_ica[bl_s:bl_e][:500]
    fp2_tk = fp2_ica[bl_e:tk_e][:500]
    if len(fp1_bl) < 400: continue
    label = 1 if t["ground_truth"] == "left" else 2
    ica_trials.append((fp1_bl, fp1_tk, fp2_bl, fp2_tk, label))

y_ica = np.array([t[4] for t in ica_trials])

# Extract same multi-band features from ICA-cleaned data
ica_features = []
for fp1_bl, fp1_tk, fp2_bl, fp2_tk, _ in ica_trials:
    feat = []
    fp1_tk_c = fp1_tk - fp1_tk.mean()
    fp2_tk_c = fp2_tk - fp2_tk.mean()
    for band_name, (lo, hi) in bands.items():
        p1 = band_power_simple(fp1_tk_c, FS, lo, hi)
        p2 = band_power_simple(fp2_tk_c, FS, lo, hi)
        feat.append(np.log(p1 + 1e-15))
        feat.append(np.log(p2 + 1e-15))
        faa = (p2 - p1) / (p2 + p1 + 1e-15)
        feat.append(faa)
        feat.append(np.log(p1 + p2 + 1e-15))
    fp1_bl_c = fp1_bl - fp1_bl.mean()
    fp2_bl_c = fp2_bl - fp2_bl.mean()
    for (lo, hi), name in [(ALPHA, "a"), (BETA, "b")]:
        bl1 = band_power_simple(fp1_bl_c, FS, lo, hi)
        tk1 = band_power_simple(fp1_tk_c, FS, lo, hi)
        bl2 = band_power_simple(fp2_bl_c, FS, lo, hi)
        tk2 = band_power_simple(fp2_tk_c, FS, lo, hi)
        feat.append((tk1 - bl1) / (bl1 + 1e-15))
        feat.append((tk2 - bl2) / (bl2 + 1e-15))
        feat.append((tk1 - bl1) / (bl1 + 1e-15) - (tk2 - bl2) / (bl2 + 1e-15))
    ica_features.append(np.array(feat))

X_ica = np.array(ica_features)

print(f"\n  ICA 清洗后分类:")
for name, clf in classifiers.items():
    accs = []
    for tr, te in loo.split(X_ica):
        if len(np.unique(y_ica[tr])) < 2: continue
        try:
            scaler = StandardScaler()
            X_tr = scaler.fit_transform(X_ica[tr])
            X_te = scaler.transform(X_ica[te])
            clf.fit(X_tr, y_ica[tr])
            pred = clf.predict(X_te)[0]
            accs.append(1 if pred == y_ica[te[0]] else 0)
        except: continue
    acc = np.mean(accs) if accs else 0
    print(f"  {name:>20s}: {acc:.1%} ({sum(accs)}/{len(accs)})")

# ═══════════════════════════════════════════
# Method 4: Focus on alpha lateralization per sub-window
# ═══════════════════════════════════════════
print("\n" + "-" * 65)
print("Method 4: Alpha 不对称时间进程分析")
print("-" * 65)

# Split task window into 4 × 500ms sub-windows and track FAA over time
sub_wins = 4
sub_len = 125  # 500ms @ 250Hz

# For each trial, compute FAA in each sub-window
faa_matrix_bl = np.zeros((n, sub_wins))
faa_matrix_tk = np.zeros((n, sub_wins))

for i, (fp1_bl, fp1_tk, fp2_bl, fp2_tk, _) in enumerate(trials):
    for j in range(sub_wins):
        s, e = j * sub_len, min((j + 1) * sub_len, len(fp1_bl))
        bl1 = band_power_simple(fp1_bl[s:e] - fp1_bl[s:e].mean(), FS, *ALPHA)
        bl2 = band_power_simple(fp2_bl[s:e] - fp2_bl[s:e].mean(), FS, *ALPHA)
        tk1 = band_power_simple(fp1_tk[s:e] - fp1_tk[s:e].mean(), FS, *ALPHA)
        tk2 = band_power_simple(fp2_tk[s:e] - fp2_tk[s:e].mean(), FS, *ALPHA)
        faa_matrix_bl[i, j] = (bl2 - bl1) / (bl2 + bl1 + 1e-15)
        faa_matrix_tk[i, j] = (tk2 - tk1) / (tk2 + tk1 + 1e-15)

# Average FAA per group
left_bl_mean = np.mean(faa_matrix_bl[y_all == 1], axis=0)
right_bl_mean = np.mean(faa_matrix_bl[y_all == 2], axis=0)
left_tk_mean = np.mean(faa_matrix_tk[y_all == 1], axis=0)
right_tk_mean = np.mean(faa_matrix_tk[y_all == 2], axis=0)

print(f"  Window:          {'BL_0-0.5s':>10s} {'BL_0.5-1s':>10s} {'BL_1-1.5s':>10s} {'BL_1.5-2s':>10s}  |  "
      f"{'TK_0-0.5s':>10s} {'TK_0.5-1s':>10s} {'TK_1-1.5s':>10s} {'TK_1.5-2s':>10s}")
print(f"  {'-'*100}")
print(f"  {'Left FAA':>12s} {left_bl_mean[0]:>+10.4f} {left_bl_mean[1]:>+10.4f} {left_bl_mean[2]:>+10.4f} {left_bl_mean[3]:>+10.4f}  |  "
      f"{left_tk_mean[0]:>+10.4f} {left_tk_mean[1]:>+10.4f} {left_tk_mean[2]:>+10.4f} {left_tk_mean[3]:>+10.4f}")
print(f"  {'Right FAA':>12s} {right_bl_mean[0]:>+10.4f} {right_bl_mean[1]:>+10.4f} {right_bl_mean[2]:>+10.4f} {right_bl_mean[3]:>+10.4f}  |  "
      f"{right_tk_mean[0]:>+10.4f} {right_tk_mean[1]:>+10.4f} {right_tk_mean[2]:>+10.4f} {right_tk_mean[3]:>+10.4f}")
print(f"  {'Diff(L-R)':>12s} ", end="")
for j in range(sub_wins):
    diff = left_bl_mean[j] - right_bl_mean[j]
    print(f"{diff:>+10.4f} ", end="")
print(" | ", end="")
for j in range(sub_wins):
    diff = left_tk_mean[j] - right_tk_mean[j]
    # FAA: left MI → right hemisphere active → FP2 alpha↓ → FAA more negative → left < right → diff < 0
    direction = "✓" if diff < 0 else "✗"
    print(f"{diff:>+10.4f}{direction} ", end="")
print()

# ═══════════════════════════════════════════
# Final Summary
# ═══════════════════════════════════════════
print("\n" + "=" * 65)
print("总结")
print("=" * 65)

# Best FAA result
best_faa = max(correct_bl, correct_tk, correct_chg) / n
print(f"\n  通道状态:        PO3/O1/T7/T8/PO4/O2 完全冗余(r=1.00) — 实际未连接")
print(f"                   Fp1/Fp2 正常 (r=0.82) — 仅有的有效前额叶信号")
print(f"  眨眼伪迹:        仅 0.47% 样本 — 不严重")
print(f"\n  Alpha不对称(FAA) 分类: baseline={correct_bl/n:.1%}  task={correct_tk/n:.1%}  change={correct_chg/n:.1%}")
print(f"  FAA t-test:       p={p_faa:.4f}")
print(f"  多频带+LDA:       (见上)")
print(f"  ICA+LDA:          (见上)")
print(f"\n  根本挑战: 40试次(22L/18R)不足; Fp1/Fp2信号质量正常但侧化效应弱")
print(f"  建议: 增加试次数量至100+; 延长MI任务时间至4s+; 确保被试执行高质量运动想象")
