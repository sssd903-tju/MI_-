#!/usr/bin/env python3
"""
三种 MI 分类方法对比（头环 FP1/FP2）
=====================================
Method 1: CSP + LDA      — 共空间模式 + 线性判别
Method 2: ERD + LDA      — 9维 ERD 特征 + LDA
Method 3: Power Ratio    — 频带功率比阈值法

数据: 试次10.bdf (8ch 250Hz) + 4×10=40 试次 JSONL
头环通道: Fp1(idx=4), Fp2(idx=5)
"""

import json
import sys
import time
from pathlib import Path
from datetime import timedelta

import mne
import numpy as np
from scipy import signal as sig
from scipy import linalg
from scipy.integrate import trapezoid
from sklearn.model_selection import LeaveOneOut
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis as SkLDA

# ── 路径 ──
BDF_PATH = Path("/Users/sssd/Downloads/实验数据/试次10.bdf")
SESSION_DIR = Path("/Users/sssd/Desktop/跳一跳/试次数据")
SESSION_FILES = [
    "session_20260614_103654.jsonl",
    "session_20260614_103846.jsonl",
    "session_20260614_104027.jsonl",
    "session_20260614_104209.jsonl",
]

# ── 配置 ──
FS = 250.0
FP1_IDX, FP2_IDX = 4, 5  # Fp1, Fp2 in 8ch montage
BASELINE_S = 2.0          # baseline 窗口 (trial_start 后 0-2s)
TASK_S = 2.0              # task 窗口 (trial_start 后 2-4s)
BASELINE_N = int(FS * BASELINE_S)
TASK_N = int(FS * TASK_S)

# 频带定义
ALPHA = (8, 13)
BETA = (13, 30)
BROADBAND = (0.5, 30)

print("=" * 60)
print("MI 分类方法对比 — 头环 Fp1/Fp2")
print("=" * 60)

# ═══════════════════════════════════════════════════════════
# 1. 加载数据
# ═══════════════════════════════════════════════════════════

print("\n[1] 加载 BDF...")
raw = mne.io.read_raw_bdf(str(BDF_PATH), preload=True, verbose=False)
data = raw.get_data()  # (n_ch, n_samples)
ch_names = raw.ch_names
n_samples = data.shape[1]

# 获取 BDF 起始时间戳 (unix ms)
# 设备记录的是北京时间 (CST=UTC+8)，但 MNE 将其标记为 UTC
# 需减去 8 小时以对齐 Godot 的 Unix 时间戳
meas = raw.info.get("meas_date")
if hasattr(meas, "timestamp"):
    # datetime object
    if meas.tzinfo is not None:
        # MNE says UTC, but it's actually CST → subtract 8h
        bdf_start_ms = int((meas.timestamp() - 8 * 3600) * 1000)
    else:
        bdf_start_ms = int(meas.timestamp() * 1000)
else:
    bdf_start_ms = int(meas * 1000) if meas else 0

print(f"  通道: {ch_names}, 形状: {data.shape}, 采样率: {FS}Hz")
print(f"  BDF 起始: {bdf_start_ms} ms (UTC)")
print(f"  Fp1=idx{FP1_IDX}, Fp2=idx{FP2_IDX}")

# 加载所有试次
print("\n[2] 加载试次标签...")
all_trials = []
for sf in SESSION_FILES:
    path = SESSION_DIR / sf
    with open(path) as f:
        for line in f:
            d = json.loads(line.strip())
            if d.get("type") == "trial":
                all_trials.append(d)

print(f"  共 {len(all_trials)} 试次")
left_count = sum(1 for t in all_trials if t["ground_truth"] == "left")
right_count = sum(1 for t in all_trials if t["ground_truth"] == "right")
print(f"  left={left_count}, right={right_count}")

# ═══════════════════════════════════════════════════════════
# 2. 时间对齐 & 切片
# ═══════════════════════════════════════════════════════════

print("\n[3] 切片试次窗口...")

def extract_windows(data, trials, bdf_start_ms):
    """从 EEG data 中提取每个试次的 baseline + task 窗口。

    时间对齐:
      trial_start_ms (Godot unix ms) → bdf 内的 sample index.
      sample_idx = (trial_start_ms - bdf_start_ms) / 1000 * FS
    """
    windows_bl = []
    windows_tk = []
    labels = []
    valid = 0
    skipped = 0

    for t in trials:
        gt = t["ground_truth"]
        ts_ms = t["timestamp_trial_start_ms"]

        # BDF 内偏移 (秒)
        offset_s = (ts_ms - bdf_start_ms) / 1000.0

        bl_start = int(offset_s * FS)
        bl_end   = int((offset_s + BASELINE_S) * FS)
        tk_end   = int((offset_s + BASELINE_S + TASK_S) * FS)

        if bl_start < 0 or tk_end > data.shape[1]:
            skipped += 1
            continue

        bl = data[:, bl_start:bl_end]   # (n_ch, baseline_n)
        tk = data[:, bl_end:tk_end]     # (n_ch, task_n)

        if bl.shape[1] < BASELINE_N * 0.8 or tk.shape[1] < TASK_N * 0.8:
            skipped += 1
            continue

        # 截断到固定长度
        bl = bl[:, :BASELINE_N]
        tk = tk[:, :TASK_N]

        windows_bl.append(bl)
        windows_tk.append(tk)
        labels.append(1 if gt == "left" else 2)  # 1=left, 2=right
        valid += 1

    return windows_bl, windows_tk, np.array(labels), valid, skipped

windows_bl, windows_tk, y, valid, skipped = extract_windows(data, all_trials, bdf_start_ms)

print(f"  有效试次: {valid}, 跳过: {skipped}")
print(f"  left(1)={np.sum(y==1)}, right(2)={np.sum(y==2)}")

if valid < 10:
    print("错误: 有效试次不足，请检查时间对齐")
    sys.exit(1)

# ═══════════════════════════════════════════════════════════
# 工具函数: 带通功率
# ═══════════════════════════════════════════════════════════

def band_power(x, fs, low, high):
    """Welch 法计算频带功率"""
    nperseg = min(128, len(x) // 2)
    if nperseg < 32:
        nperseg = len(x) // 4
    if nperseg < 16:
        return 0.0
    f, p = sig.welch(x, fs, nperseg=nperseg)
    mask = (f >= low) & (f <= high)
    if mask.sum() < 2:
        return 0.0
    return float(trapezoid(p[mask], f[mask]))

def notch_filter_2d(data, fs, freq=50, q=30):
    """50Hz 陷波 (对 2D array)"""
    b, a = sig.iirnotch(freq, q, fs)
    out = np.zeros_like(data)
    for ch in range(data.shape[0]):
        out[ch] = sig.filtfilt(b, a, data[ch])
    return out

def butter_bandpass(low, high, fs, order=4):
    nyq = 0.5 * fs
    low_n = low / nyq
    high_n = high / nyq
    b, a = sig.butter(order, [low_n, high_n], btype="band")
    return b, a

def bandpass_2d(data, low, high, fs, order=4):
    b, a = butter_bandpass(low, high, fs, order)
    out = np.zeros_like(data)
    for ch in range(data.shape[0]):
        out[ch] = sig.filtfilt(b, a, data[ch])
    return out

# ═══════════════════════════════════════════════════════════
# Method 1: CSP + LDA
# ═══════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("Method 1: CSP + LDA")
print("=" * 60)

def csp_fit(X1, X2, n_components=2):
    """Fit CSP spatial filter.
    X1: list of (n_ch, n_samples) arrays for class 1
    X2: list of (n_ch, n_samples) arrays for class 2
    """
    n_ch = X1[0].shape[0]

    # Compute average covariance
    cov1 = np.zeros((n_ch, n_ch))
    for x in X1:
        xc = x - x.mean(axis=1, keepdims=True)
        cov1 += np.cov(xc)
    cov1 /= len(X1)

    cov2 = np.zeros((n_ch, n_ch))
    for x in X2:
        xc = x - x.mean(axis=1, keepdims=True)
        cov2 += np.cov(xc)
    cov2 /= len(X2)

    # Regularized composite covariance
    cov_c = cov1 + cov2
    cov_c += 1e-6 * np.eye(n_ch)

    # Eigen decomposition
    eigenvalues, eigenvectors = linalg.eigh(cov1, cov_c)

    # Sort descending (best CSP components)
    idx = np.argsort(eigenvalues)[::-1]
    eigenvectors = eigenvectors[:, idx]

    # Take top and bottom n_components//2
    W = np.hstack([
        eigenvectors[:, :n_components // 2],
        eigenvectors[:, -n_components // 2:]
    ])
    return W

def csp_transform(W, X):
    """Apply CSP filter, return log-variance features."""
    Z = W.T @ X  # (n_components, n_samples)
    var = np.var(Z, axis=1)
    return np.log(var / (var.sum() + 1e-15))

# CSP 需要 task 窗口数据 (已经是 MI 相关时段)
# 对 8 通道做 8-30Hz 带通
print("  预处理: 8-30Hz 带通滤波...")
csp_data = []
for bl, tk in zip(windows_bl, windows_tk):
    # 使用 task 窗口（2-4s 已经包含 MI 成分）
    tk_filt = bandpass_2d(tk, 8, 30, FS)
    csp_data.append(tk_filt)

# 也尝试直接用全窗口（baseline + task）
csp_full = []
for bl, tk in zip(windows_bl, windows_tk):
    full = np.hstack([bl, tk])
    full_filt = bandpass_2d(full, 8, 30, FS)
    csp_full.append(full_filt)

csp_accs_lo = []
csp_accs_full = []
loo = LeaveOneOut()

for train_idx, test_idx in loo.split(csp_data):
    X1_train = [csp_data[i] for i in train_idx if y[i] == 1]
    X2_train = [csp_data[i] for i in train_idx if y[i] == 2]
    X_test = csp_data[test_idx[0]]
    y_test = y[test_idx[0]]

    if len(X1_train) < 2 or len(X2_train) < 2:
        continue

    try:
        W = csp_fit(X1_train, X2_train, n_components=4)
        # Extract features
        X_feat_train = np.array([csp_transform(W, x) for x in csp_data for _ in [0]])
        # Actually need to map back to training indices
        X_feat_train = np.array([csp_transform(W, csp_data[i]) for i in train_idx])
        X_feat_test = np.array([csp_transform(W, X_test)])

        # LDA
        clf = SkLDA()
        clf.fit(X_feat_train, y[train_idx])
        pred = clf.predict(X_feat_test)[0]
        if pred == y_test:
            csp_accs_lo.append(1)
        else:
            csp_accs_lo.append(0)
    except Exception as e:
        continue

for train_idx, test_idx in loo.split(csp_full):
    X1_train = [csp_full[i] for i in train_idx if y[i] == 1]
    X2_train = [csp_full[i] for i in train_idx if y[i] == 2]
    X_test = csp_full[test_idx[0]]
    y_test = y[test_idx[0]]

    if len(X1_train) < 2 or len(X2_train) < 2:
        continue

    try:
        W = csp_fit(X1_train, X2_train, n_components=4)
        X_feat_train = np.array([csp_transform(W, csp_full[i]) for i in train_idx])
        X_feat_test = np.array([csp_transform(W, X_test)])
        clf = SkLDA()
        clf.fit(X_feat_train, y[train_idx])
        pred = clf.predict(X_feat_test)[0]
        csp_accs_full.append(1 if pred == y_test else 0)
    except:
        continue

csp_acc_lo = np.mean(csp_accs_lo) if csp_accs_lo else 0
csp_acc_full = np.mean(csp_accs_full) if csp_accs_full else 0
print(f"  CSP(task window) LOO: {csp_acc_lo:.1%} ({sum(csp_accs_lo)}/{len(csp_accs_lo)})")
print(f"  CSP(full window) LOO: {csp_acc_full:.1%} ({sum(csp_accs_full)}/{len(csp_accs_full)})")

# ═══════════════════════════════════════════════════════════
# Method 2: ERD + LDA (9 features)
# ═══════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("Method 2: ERD + LDA")
print("=" * 60)

def extract_erd_features(bl_data, tk_data, left_idx, right_idx, fs):
    """9 维 ERD 特征: 宽带 + alpha + beta，各有 left/right/lateral"""

    def erd(ch_bl, ch_tk, lo, hi):
        a = band_power(ch_bl, fs, lo, hi)
        b = band_power(ch_tk, fs, lo, hi)
        return (b - a) / (a + 1e-15)

    bl_l = bl_data[left_idx] - bl_data[left_idx].mean()
    bl_r = bl_data[right_idx] - bl_data[right_idx].mean()
    tk_l = tk_data[left_idx] - tk_data[left_idx].mean()
    tk_r = tk_data[right_idx] - tk_data[right_idx].mean()

    # Broadband (0.5-30Hz)
    e_l = erd(bl_l, tk_l, *BROADBAND)
    e_r = erd(bl_r, tk_r, *BROADBAND)
    lat = e_l - e_r

    # Alpha (8-13Hz)
    a_l = erd(bl_l, tk_l, *ALPHA)
    a_r = erd(bl_r, tk_r, *ALPHA)
    lat_a = a_l - a_r

    # Beta (13-30Hz)
    b_l = erd(bl_l, tk_l, *BETA)
    b_r = erd(bl_r, tk_r, *BETA)
    lat_b = b_l - b_r

    return np.array([e_l, e_r, lat,
                     a_l, a_r, lat_a,
                     b_l, b_r, lat_b])

# 对所有试次提取 ERD 特征 (带 50Hz 陷波)
print("  预处理: 50Hz 陷波...")
erd_features = []
for i, (bl, tk) in enumerate(zip(windows_bl, windows_tk)):
    bl_filt = notch_filter_2d(bl, FS, freq=50, q=30)
    tk_filt = notch_filter_2d(tk, FS, freq=50, q=30)
    f = extract_erd_features(bl_filt, tk_filt, FP1_IDX, FP2_IDX, FS)
    erd_features.append(f)

X_erd = np.array(erd_features)

# LOO cross-validation
erd_accs = []
erd_preds = []
erd_trues = []

for train_idx, test_idx in loo.split(X_erd):
    X_tr, X_te = X_erd[train_idx], X_erd[test_idx]
    y_tr, y_te = y[train_idx], y[test_idx]

    # 检查训练集是否有两类
    if len(np.unique(y_tr)) < 2:
        continue

    clf = SkLDA()
    clf.fit(X_tr, y_tr)
    pred = clf.predict(X_te)[0]
    erd_accs.append(1 if pred == y_te[0] else 0)
    erd_preds.append(pred)
    erd_trues.append(y_te[0])

erd_acc = np.mean(erd_accs) if erd_accs else 0
print(f"  ERD+LDA LOO: {erd_acc:.1%} ({sum(erd_accs)}/{len(erd_accs)})")

# 显示特征重要性
if erd_accs:
    clf_all = SkLDA()
    clf_all.fit(X_erd, y)
    feature_names = [
        "ERD_Fp1(broad)", "ERD_Fp2(broad)", "lateral(broad)",
        "ERD_a_Fp1", "ERD_a_Fp2", "lateral_a",
        "ERD_b_Fp1", "ERD_b_Fp2", "lateral_b",
    ]
    coef = clf_all.coef_[0]
    print("\n  特征权重 (LDA coef):")
    for name, c in zip(feature_names, coef):
        bar = "█" * int(abs(c) * 50) if abs(c) < 1 else "█" * 50
        sign = "+" if c > 0 else "-"
        print(f"    {name:20s} {c:+8.4f} {sign}{bar}")

# ═══════════════════════════════════════════════════════════
# Method 3: Power Ratio (阈值法)
# ═══════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("Method 3: Power Ratio (频带功率比)")
print("=" * 60)

def classify_power_ratio(bl_data, tk_data, left_idx, right_idx, fs,
                          band="alpha", threshold=1.0):
    """基于 Fp1/Fp2 功率比分类。

    ERD/ERS 逻辑:
      - 左手运动想象 → 右侧脑区激活 → Fp2 功率下降 (ERD) → Fp1/Fp2 比值 > 1
      - 右手运动想象 → 左侧脑区激活 → Fp1 功率下降 (ERD) → Fp1/Fp2 比值 < 1

    使用 task vs baseline 的功率变化比。
    """
    if band == "alpha":
        lo, hi = ALPHA
    elif band == "beta":
        lo, hi = BETA
    elif band == "broadband":
        lo, hi = BROADBAND
    else:
        raise ValueError(f"Unknown band: {band}")

    # Task 窗口功率
    tk_l = tk_data[left_idx] - tk_data[left_idx].mean()
    tk_r = tk_data[right_idx] - tk_data[right_idx].mean()
    p_tk_l = band_power(tk_l, fs, lo, hi)
    p_tk_r = band_power(tk_r, fs, lo, hi)

    # Baseline 功率
    bl_l = bl_data[left_idx] - bl_data[left_idx].mean()
    bl_r = bl_data[right_idx] - bl_data[right_idx].mean()
    p_bl_l = band_power(bl_l, fs, lo, hi)
    p_bl_r = band_power(bl_r, fs, lo, hi)

    # ERD 比值: (task_power_left / baseline_power_left) / (task_power_right / baseline_power_right)
    # > 1 表示左边 ERD 更强 (right hand MI)
    erd_l = (p_tk_l + 1e-15) / (p_bl_l + 1e-15)
    erd_r = (p_tk_r + 1e-15) / (p_bl_r + 1e-15)
    ratio = erd_l / (erd_r + 1e-15)

    if ratio > threshold:
        return 2  # right (Fp2 相对 ERD 更强 → 左手 MI → label=right)
    elif ratio < 1.0 / threshold:
        return 1  # left  (Fp1 相对 ERD 更强 → 右手 MI → label=left)
    else:
        return 0  # rest

# 搜索最佳阈值和频带
print("  扫描最佳参数 (频带 × 阈值)...")
best_acc = 0
best_params = None
results = []

for band_name, (lo, hi), band_key in [
    ("alpha (8-13Hz)", ALPHA, "alpha"),
    ("beta (13-30Hz)", BETA, "beta"),
    ("broadband (0.5-30Hz)", BROADBAND, "broadband"),
]:
    for th in [1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.8, 2.0]:
        correct = 0
        total = 0
        for i, (bl, tk) in enumerate(zip(windows_bl, windows_tk)):
            bl_filt = notch_filter_2d(bl, FS, freq=50, q=30)
            tk_filt = notch_filter_2d(tk, FS, freq=50, q=30)
            pred = classify_power_ratio(
                bl_filt, tk_filt, FP1_IDX, FP2_IDX, FS,
                band=band_key, threshold=th
            )
            if pred == 0:  # rest — 算错误
                pass  # don't count rest
            if pred == y[i]:
                correct += 1
            total += 1

        acc = correct / total if total > 0 else 0
        results.append((band_key, th, correct, total, acc))
        if acc > best_acc:
            best_acc = acc
            best_params = (band_key, th, correct, total)

print(f"\n  {'Band':<22s} {'Thr':>6s} {'Acc':>8s} {'N':>6s}")
print(f"  {'-'*42}")
for band_key, th, correct, total, acc in sorted(results, key=lambda x: -x[4]):
    marker = " ← best" if (band_key, th) == (best_params[0], best_params[1]) else ""
    print(f"  {band_key:<22s} {th:>5.1f}  {acc:>6.1%}  {correct:>3d}/{total}{marker}")

# ── 纯 task 功率比（不用 baseline） ──
print("\n  --- 纯 Task 功率比 (不用 baseline 归一化) ---")
best_acc2 = 0
for band_name, band_key in [("alpha", "alpha"), ("beta", "beta"), ("broadband", "broadband")]:
    if band_key == "alpha":
        lo, hi = ALPHA
    elif band_key == "beta":
        lo, hi = BETA
    else:
        lo, hi = BROADBAND

    for th in [1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6]:
        correct = 0
        total = 0
        for i, tk in enumerate(windows_tk):
            tk_filt = notch_filter_2d(tk, FS, freq=50, q=30)
            tk_l = tk_filt[FP1_IDX] - tk_filt[FP1_IDX].mean()
            tk_r = tk_filt[FP2_IDX] - tk_filt[FP2_IDX].mean()
            p_l = band_power(tk_l, FS, lo, hi)
            p_r = band_power(tk_r, FS, lo, hi)
            ratio = p_l / (p_r + 1e-15)

            if ratio > th:
                pred = 2
            elif ratio < 1.0 / th:
                pred = 1
            else:
                pred = 0

            if pred == y[i]:
                correct += 1
            total += 1

        acc = correct / total if total > 0 else 0
        print(f"  {band_key:>12s} task-only  thr={th:.1f}  acc={acc:.1%}  ({correct}/{total})")
        if acc > best_acc2:
            best_acc2 = acc

# ═══════════════════════════════════════════════════════════
# 总结
# ═══════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("总结对比")
print("=" * 60)

csp_best = max(csp_acc_lo, csp_acc_full)
print(f"  CSP + LDA      : {csp_best:.1%}  (task={csp_acc_lo:.1%}, full={csp_acc_full:.1%})")
print(f"  ERD(9feat)+LDA : {erd_acc:.1%}  (LOO CV)")
print(f"  Power Ratio    : {best_acc:.1%}  (band={best_params[0]}, thr={best_params[1]})")

print("\n  特征数: CSP=4, ERD=9, PowerRatio=1")
print(f"  试次: {valid} (left={np.sum(y==1)}, right={np.sum(y==2)})")

# 混淆矩阵 (ERD)
if erd_accs:
    from collections import Counter
    cm = Counter()
    for t, p in zip(erd_trues, erd_preds):
        cm[(t, p)] += 1
    print(f"\n  ERD+LDA 混淆矩阵:")
    print(f"           pred_left pred_right")
    print(f"  true_left    {cm.get((1,1),0):>5}      {cm.get((1,2),0):>5}")
    print(f"  true_right   {cm.get((2,1),0):>5}      {cm.get((2,2),0):>5}")
