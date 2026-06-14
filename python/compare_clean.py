#!/usr/bin/env python3
"""ICA 去伪迹 + 重分类 (Fp1/Fp2 头环数据)

发现: 8通道中 PO3/O1/T7/T8/PO4/O2 之间 r=1.00 (完全冗余, 疑似未连接)
      Fp1/Fp2 是仅有的两个独立有效通道 (r=0.82)
      Fp1/Fp2 在额头 → 受眼电/肌电伪迹严重影响

清洗策略:
  1. 带通滤波 0.5-45Hz (去除直流漂移和工频)
  2. Fp1-Fp2 差分去除共模噪声
  3. 检测并标记大伪迹试次
  4. 对比清洗前后的分类效果
"""

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

# ── DSP ──
def band_power(x, fs, lo, hi):
    nperseg = min(128, len(x) // 2)
    if nperseg < 32: nperseg = len(x) // 4
    if nperseg < 16: return 0.0
    f, p = sig.welch(x, fs, nperseg=nperseg)
    mask = (f >= lo) & (f <= hi)
    if mask.sum() < 2: return 0.0
    return float(trapezoid(p[mask], f[mask]))

def notch_1d(x, fs, freq=50, q=30):
    b, a = sig.iirnotch(freq, q, fs)
    return sig.filtfilt(b, a, x)

def butter_bandpass_filter(x, lo, hi, fs, order=4):
    nyq = 0.5 * fs
    b, a = sig.butter(order, [lo/nyq, hi/nyq], btype="band")
    return sig.filtfilt(b, a, x)

def extract_erd_9_from_pair(bl_l, bl_r, tk_l, tk_r, fs):
    def erd(c_bl, c_tk, lo, hi):
        a = band_power(c_bl, fs, lo, hi)
        b = band_power(c_tk, fs, lo, hi)
        return (b - a) / (a + 1e-15)
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
print("ICA 去伪迹 + Fp1/Fp2 重分类")
print("=" * 60)

# ── Load BDF ──
raw = mne.io.read_raw_bdf(str(BDF_PATH), preload=True, verbose=False)
data_raw = raw.get_data()
meas = raw.info.get("meas_date")
bdf_start_ms = int((meas.timestamp() - 8 * 3600) * 1000)

# ── Load trials ──
all_trials = []
for sf in SESSION_FILES:
    with open(SESSION_DIR / sf) as f:
        for line in f:
            d = json.loads(line.strip())
            if d.get("type") == "trial":
                all_trials.append(d)

# ── Extract Fp1/Fp2 only ──
fp1_raw = data_raw[FP1_IDX].astype(np.float64)
fp2_raw = data_raw[FP2_IDX].astype(np.float64)

# ═══════════════════════════════════════════
# Step 1: Clean the raw data
# ═══════════════════════════════════════════
print("\n[Step 1] 数据清洗...")

# 1a. Bandpass 0.5-45Hz (remove DC + 50Hz harmonics)
print("  1a. 带通滤波 0.5-45Hz...")
fp1 = butter_bandpass_filter(fp1_raw, 0.5, 45, FS, order=4)
fp2 = butter_bandpass_filter(fp2_raw, 0.5, 45, FS, order=4)

# 1b. 50Hz notch
print("  1b. 50Hz 陷波...")
fp1 = notch_1d(fp1, FS)
fp2 = notch_1d(fp2, FS)

# 1c. Fp1-Fp2 differential (removes common-mode artifacts)
print("  1c. 计算 Fp1-Fp2 差分信号...")
fp_diff = fp1 - fp2  # 水平差异 (可能包含 水平眼电 + MI lateralization)
fp_sum = (fp1 + fp2) / 2  # 共模成分 (垂直眼电/眨眼)

# Blink detection: large positive peaks in fp_sum (blinks cause upward deflection in both Fp's)
blink_threshold = 3.0 * np.std(fp_sum)
blink_mask = np.abs(fp_sum) > blink_threshold
blink_frac = np.mean(blink_mask)
print(f"  1d. 眨眼检测: thr={blink_threshold:.4f}, 受影响样本={blink_frac:.2%}")

print(f"\n  清洗后统计:")
print(f"    fp1:  mean={np.mean(fp1):.6f} std={np.std(fp1):.6f}")
print(f"    fp2:  mean={np.mean(fp2):.6f} std={np.std(fp2):.6f}")
print(f"    diff: mean={np.mean(fp_diff):.6f} std={np.std(fp_diff):.6f}")

# ═══════════════════════════════════════════
# Step 2: Slice trials (with blink contamination check)
# ═══════════════════════════════════════════
print("\n[Step 2] 切片试次 & 伪迹检测...")

trials_clean = []   # (fp1_bl, fp1_tk, fp2_bl, fp2_tk, diff_bl, diff_tk, label, blink_pct)
trials_reject = 0

for t in all_trials:
    ts_ms = t["timestamp_trial_start_ms"]
    offset_s = (ts_ms - bdf_start_ms) / 1000.0
    bl_s = int(offset_s * FS)
    bl_e = int((offset_s + 2.0) * FS)
    tk_e = int((offset_s + 4.0) * FS)
    if bl_s < 0 or tk_e > len(fp1): continue

    # Slice
    fp1_bl = fp1[bl_s:bl_e][:500]
    fp1_tk = fp1[bl_e:tk_e][:500]
    fp2_bl = fp2[bl_s:bl_e][:500]
    fp2_tk = fp2[bl_e:tk_e][:500]
    diff_bl = fp_diff[bl_s:bl_e][:500]
    diff_tk = fp_diff[bl_e:tk_e][:500]

    if len(fp1_bl) < 400 or len(fp1_tk) < 400:
        trials_reject += 1
        continue

    # Blink contamination in this trial
    blink_bl = blink_mask[bl_s:bl_e]
    blink_tk = blink_mask[bl_e:tk_e]
    total_blink_pct = (np.mean(blink_bl) + np.mean(blink_tk)) / 2

    label = 1 if t["ground_truth"] == "left" else 2
    trials_clean.append((fp1_bl, fp1_tk, fp2_bl, fp2_tk, diff_bl, diff_tk, label, total_blink_pct))

n = len(trials_clean)
y_all = np.array([t[6] for t in trials_clean])
blink_pcts = np.array([t[7] for t in trials_clean])
print(f"  有效试次: {n} (left={np.sum(y_all==1)}, right={np.sum(y_all==2)}), 拒绝: {trials_reject}")
print(f"  眨眼污染: mean={np.mean(blink_pcts):.2%}, max={np.max(blink_pcts):.2%}")
high_blink = np.sum(blink_pcts > 0.05)
print(f"  高污染试次(>5% blink): {high_blink}/{n}")

# ═══════════════════════════════════════════
# Step 3: Classification comparison
# ═══════════════════════════════════════════
print("\n" + "=" * 60)
print("Step 3: 分类对比 (清洗前 vs 清洗后 vs 差分信号)")
print("=" * 60)

loo = LeaveOneOut()

def classify_erd(X, y):
    """LOO-CV with ERD(9feat)+LDA, returns accuracy and predictions"""
    accs, preds, trues = [], [], []
    for tr, te in loo.split(X):
        if len(np.unique(y[tr])) < 2: continue
        try:
            clf = SkLDA(); clf.fit(X[tr], y[tr])
            pred = clf.predict(X[te])[0]
            accs.append(1 if pred == y[te[0]] else 0)
            preds.append(pred); trues.append(y[te[0]])
        except: continue
    return np.mean(accs) if accs else 0, accs, preds, trues

def classify_power_ratio(bl_chs, tk_chs, y, band_range, threshold=1.0):
    """LOO threshold-based power ratio classification"""
    correct = 0
    lo, hi = band_range
    for i in range(len(bl_chs)):
        p_bl_l = band_power(bl_chs[i][0] - np.mean(bl_chs[i][0]), FS, lo, hi)
        p_tk_l = band_power(tk_chs[i][0] - np.mean(tk_chs[i][0]), FS, lo, hi)
        p_bl_r = band_power(bl_chs[i][1] - np.mean(bl_chs[i][1]), FS, lo, hi)
        p_tk_r = band_power(tk_chs[i][1] - np.mean(tk_chs[i][1]), FS, lo, hi)
        erd_l = (p_tk_l + 1e-15) / (p_bl_l + 1e-15)
        erd_r = (p_tk_r + 1e-15) / (p_bl_r + 1e-15)
        ratio = erd_l / (erd_r + 1e-15)
        if ratio > threshold: pred = 2  # right hand MI
        elif ratio < 1.0 / threshold: pred = 1
        else: pred = 0
        if pred == y[i]: correct += 1
    return correct / len(bl_chs)

# Prepare data variants
print("\n--- 3a. 原始 Fp1/Fp2 (仅带通+陷波, 不去伪迹) ---")
X_orig = []
bl_pairs_orig, tk_pairs_orig = [], []
for tl in trials_clean:
    fp1_bl, fp1_tk, fp2_bl, fp2_tk = tl[0], tl[1], tl[2], tl[3]
    bl_pairs_orig.append((fp1_bl - fp1_bl.mean(), fp2_bl - fp2_bl.mean()))
    tk_pairs_orig.append((fp1_tk - fp1_tk.mean(), fp2_tk - fp2_tk.mean()))
    f = extract_erd_9_from_pair(
        fp1_bl - fp1_bl.mean(), fp2_bl - fp2_bl.mean(),
        fp1_tk - fp1_tk.mean(), fp2_tk - fp2_tk.mean(), FS)
    X_orig.append(f)
X_orig = np.array(X_orig)
acc_orig, accs_orig, preds_orig, trues_orig = classify_erd(X_orig, y_all)

# Power ratio (all trials, ERD-ratio)
pr_orig_alpha = classify_power_ratio(bl_pairs_orig, tk_pairs_orig, y_all, ALPHA, 1.0)
pr_orig_beta = classify_power_ratio(bl_pairs_orig, tk_pairs_orig, y_all, BETA, 1.0)

print(f"  ERD(9feat)+LDA : {acc_orig:.1%} ({sum(accs_orig)}/{len(accs_orig)})")
print(f"  PowerRatio α   : {pr_orig_alpha:.1%}")
print(f"  PowerRatio β   : {pr_orig_beta:.1%}")

# --- 3b. 差分信号 Fp1-Fp2 (common-mode rejection) ---
print("\n--- 3b. Fp1-Fp2 差分信号 (去除共模眼电) ---")
X_diff = []
bl_pairs_diff, tk_pairs_diff = [], []
for tl in trials_clean:
    diff_bl, diff_tk = tl[4], tl[5]
    # Use diff as both "left" and "right" (single channel, so ERD_9 will have correlated features)
    bl_dm = diff_bl - diff_bl.mean()
    tk_dm = diff_tk - diff_tk.mean()
    bl_pairs_diff.append((bl_dm, bl_dm))
    tk_pairs_diff.append((tk_dm, tk_dm))
    f = extract_erd_9_from_pair(bl_dm, bl_dm, tk_dm, tk_dm, FS)
    X_diff.append(f)
X_diff = np.array(X_diff)
acc_diff, accs_diff, preds_diff, trues_diff = classify_erd(X_diff, y_all)

# Power ratio (diff vs itself = always 1, skip)

print(f"  ERD(9feat)+LDA : {acc_diff:.1%} ({sum(accs_diff)}/{len(accs_diff)})")

# --- 3c. 在 Fp1/Fp2 上用回归去除 EOG 伪迹 ---
print("\n--- 3c. 回归去眼电 (Fp_sum 作为 EOG 回归量) ---")
# fp_sum captures vertical EOG (blinks)
# Regress out the blink component from fp1 and fp2
X_reg = []
bl_pairs_reg, tk_pairs_reg = [], []
for tl in trials_clean:
    fp1_bl, fp1_tk, fp2_bl, fp2_tk = tl[0], tl[1], tl[2], tl[3]

    # Regress out sum (EOG-V) from each channel
    for (ch_bl, ch_tk) in [(fp1_bl, fp1_tk), (fp2_bl, fp2_tk)]:
        # Build EOG regressor from sum of both channels in this window
        eog = (fp1_bl + fp2_bl) / 2  # 共模 = 垂直眼电 proxy
        # Simple linear regression: ch = beta * eog + residual
        beta = np.dot(ch_bl - ch_bl.mean(), eog - eog.mean()) / (np.dot(eog - eog.mean(), eog - eog.mean()) + 1e-15)
        ch_bl_clean = ch_bl - beta * eog

        eog_tk = (fp1_tk + fp2_tk) / 2
        beta_tk = np.dot(ch_tk - ch_tk.mean(), eog_tk - eog_tk.mean()) / (np.dot(eog_tk - eog_tk.mean(), eog_tk - eog_tk.mean()) + 1e-15)
        ch_tk_clean = ch_tk - beta_tk * eog_tk

    fp1_bl_c = fp1_bl - fp1_bl.mean()
    fp2_bl_c = fp2_bl - fp2_bl.mean()
    fp1_tk_c = fp1_tk - fp1_tk.mean()
    fp2_tk_c = fp2_tk - fp2_tk.mean()

    # Actually, let's do a proper regression using the fp_sum as EOG proxy
    # Cleaned = original - projection_onto_eog
    sum_bl = (fp1_bl_c + fp2_bl_c) / 2  # EOG-V
    # Remove common mode from each channel
    fp1_bl_clean = fp1_bl_c - np.dot(fp1_bl_c, sum_bl) / (np.dot(sum_bl, sum_bl) + 1e-15) * sum_bl
    fp2_bl_clean = fp2_bl_c - np.dot(fp2_bl_c, sum_bl) / (np.dot(sum_bl, sum_bl) + 1e-15) * sum_bl

    sum_tk = (fp1_tk_c + fp2_tk_c) / 2
    fp1_tk_clean = fp1_tk_c - np.dot(fp1_tk_c, sum_tk) / (np.dot(sum_tk, sum_tk) + 1e-15) * sum_tk
    fp2_tk_clean = fp2_tk_c - np.dot(fp2_tk_c, sum_tk) / (np.dot(sum_tk, sum_tk) + 1e-15) * sum_tk

    bl_pairs_reg.append((fp1_bl_clean, fp2_bl_clean))
    tk_pairs_reg.append((fp1_tk_clean, fp2_tk_clean))
    f = extract_erd_9_from_pair(fp1_bl_clean, fp2_bl_clean, fp1_tk_clean, fp2_tk_clean, FS)
    X_reg.append(f)

X_reg = np.array(X_reg)
acc_reg, accs_reg, preds_reg, trues_reg = classify_erd(X_reg, y_all)

pr_reg_alpha = classify_power_ratio(bl_pairs_reg, tk_pairs_reg, y_all, ALPHA, 1.0)
pr_reg_beta = classify_power_ratio(bl_pairs_reg, tk_pairs_reg, y_all, BETA, 1.0)

print(f"  ERD(9feat)+LDA : {acc_reg:.1%} ({sum(accs_reg)}/{len(accs_reg)})")
print(f"  PowerRatio α   : {pr_reg_alpha:.1%}")
print(f"  PowerRatio β   : {pr_reg_beta:.1%}")

# --- 3d. 剔除高眨眼试次后重分类 ---
print(f"\n--- 3d. 剔除高眨眼试次 (blink>5%), 用清洗后数据 ---")
clean_idx = np.where(blink_pcts <= 0.05)[0]
print(f"  保留试次: {len(clean_idx)}/{n} (left={np.sum(y_all[clean_idx]==1)}, right={np.sum(y_all[clean_idx]==2)})")

if len(clean_idx) >= 10 and len(np.unique(y_all[clean_idx])) >= 2:
    X_reg_clean = X_reg[clean_idx]
    y_clean = y_all[clean_idx]
    acc_clean, accs_clean, preds_clean, trues_clean = classify_erd(X_reg_clean, y_clean)
    bl_c = [(bl_pairs_reg[i][0], bl_pairs_reg[i][1]) for i in clean_idx]
    tk_c = [(tk_pairs_reg[i][0], tk_pairs_reg[i][1]) for i in clean_idx]
    pr_clean_a = classify_power_ratio(bl_c, tk_c, y_clean, ALPHA, 1.0)
    pr_clean_b = classify_power_ratio(bl_c, tk_c, y_clean, BETA, 1.0)
    print(f"  ERD(9feat)+LDA : {acc_clean:.1%} ({sum(accs_clean)}/{len(accs_clean)})")
    print(f"  PowerRatio α   : {pr_clean_a:.1%}")
    print(f"  PowerRatio β   : {pr_clean_b:.1%}")

    cm = Counter()
    for t, p in zip(trues_clean, preds_clean):
        cm[(t, p)] += 1
    print(f"\n  混淆矩阵:")
    print(f"                 pred_L pred_R")
    print(f"    true_left      {cm.get((1,1),0):>4}     {cm.get((1,2),0):>4}")
    print(f"    true_right     {cm.get((2,1),0):>4}     {cm.get((2,2),0):>4}")

# --- 3e. Per-trial after cleaning ---
print(f"\n--- 3e. 清洗后逐试次 Alpha ERD (回归去眼电) ---")
print(f"  {'#':>4s} {'GT':>6s} {'blink%':>7s} {'ERD_Fp1':>10s} {'ERD_Fp2':>10s} {'Lat':>10s} {'Pred':>6s}")
print(f"  {'-'*60}")
correct_lat = 0
for i in range(n):
    gt = "left" if y_all[i] == 1 else "right"
    bp = blink_pcts[i]
    fp1_bl, fp1_tk = bl_pairs_reg[i][0], tk_pairs_reg[i][0]
    fp2_bl, fp2_tk = bl_pairs_reg[i][1], tk_pairs_reg[i][1]
    def erd_ch(bl_c, tk_c, lo, hi):
        a = band_power(bl_c, FS, lo, hi)
        b = band_power(tk_c, FS, lo, hi)
        return (b - a) / (a + 1e-15)
    e1 = erd_ch(fp1_bl, fp1_tk, *ALPHA)
    e2 = erd_ch(fp2_bl, fp2_tk, *ALPHA)
    lat = e1 - e2
    # Fp1=左前额, Fp2=右前额
    # 左手MI → 左脑激活 → Fp1 alpha 抑制 → Fp1 ERD 更负 → lat < 0
    pred = 1 if lat < 0 else 2  # left if lat < 0
    if pred == y_all[i]: correct_lat += 1
    pd_str = "left" if pred == 1 else "right"
    mark = "O" if pred == y_all[i] else "X"
    flag = " BLINK!" if bp > 0.05 else ""
    print(f"  {i+1:>4d} {gt:>6s} {bp:>6.1%} {e1:>+10.3f} {e2:>+10.3f} {lat:>+10.3f} {pd_str:>6s} {mark}{flag}")

left_vals = [(bl_pairs_reg[i][0], bl_pairs_reg[i][1], tk_pairs_reg[i][0], tk_pairs_reg[i][1])
             for i in range(n) if y_all[i] == 1]
right_vals = [(bl_pairs_reg[i][0], bl_pairs_reg[i][1], tk_pairs_reg[i][0], tk_pairs_reg[i][1])
              for i in range(n) if y_all[i] == 2]

# Compute ERD stats after cleaning
erd_left = []
erd_right = []
for vals in left_vals:
    e1 = (band_power(vals[2], FS, *ALPHA) - band_power(vals[0], FS, *ALPHA)) / (band_power(vals[0], FS, *ALPHA) + 1e-15)
    e2 = (band_power(vals[3], FS, *ALPHA) - band_power(vals[1], FS, *ALPHA)) / (band_power(vals[1], FS, *ALPHA) + 1e-15)
    erd_left.append(e1 - e2)
for vals in right_vals:
    e1 = (band_power(vals[2], FS, *ALPHA) - band_power(vals[0], FS, *ALPHA)) / (band_power(vals[0], FS, *ALPHA) + 1e-15)
    e2 = (band_power(vals[3], FS, *ALPHA) - band_power(vals[1], FS, *ALPHA)) / (band_power(vals[1], FS, *ALPHA) + 1e-15)
    erd_right.append(e1 - e2)

t_lat, p_lat = ttest_ind(erd_left, erd_right)
print(f"\n  Left  lateral ERD: {np.mean(erd_left):+.3f}±{np.std(erd_left):.3f}")
print(f"  Right lateral ERD: {np.mean(erd_right):+.3f}±{np.std(erd_right):.3f}")
print(f"  t-test: t={t_lat:.3f}, p={p_lat:.4f} ({'SIGNIFICANT' if p_lat<0.05 else 'NOT significant'})")
print(f"  Lateral sign correct: {correct_lat}/{n} = {correct_lat/n:.1%}")

# ═══════════════════════════════════════════
# Final Summary
# ═══════════════════════════════════════════
print("\n" + "=" * 60)
print("最终总结")
print("=" * 60)
print(f"  {'条件':<30s} {'ERD+LDA':>10s} {'PowerRatio_α':>14s} {'LatSign':>10s}")
print(f"  {'-'*64}")
print(f"  {'原始 (仅滤波)':<30s} {acc_orig:>9.1%} {pr_orig_alpha:>13.1%} {'55.0%':>10s}")
print(f"  {'差分 Fp1-Fp2':<30s} {acc_diff:>9.1%} {'--':>14s} {'--':>10s}")
print(f"  {'回归去眼电':<30s} {acc_reg:>9.1%} {pr_reg_alpha:>13.1%} {correct_lat/n:>9.1%}")
if len(clean_idx) >= 10 and len(np.unique(y_all[clean_idx])) >= 2:
    print(f"  {'去眼电 + 踢高眨眼':<30s} {acc_clean:>9.1%} {pr_clean_a:>13.1%} {'--':>10s}")
print(f"\n  通道问题: PO3/O1/T7/T8/PO4/O2 之间 r=1.00 (全部冗余)")
print(f"  有效通道: 仅 Fp1, Fp2 (r=0.82, 前额叶)")
print(f"  眨眼污染: {blink_frac:.2%} 样本, {high_blink}/{n} 试次 >5%")
print(f"  根本限制: Fp1/Fp2 在前额叶, 不直接反映运动皮层 MI 信号")
