#!/usr/bin/env python3
"""
FP1/FP2 特征 × 分类器 全量对比 (50 试次)
=========================================
特征组:
  1. FAA     — alpha不对称 (FP2-FP1)/(FP2+FP1), 1维
  2. FAA_6   — 6频带FAA, 6维
  3. Power   — task窗口绝对功率 log, 12维
  4. ERD     — ERD (task vs baseline), 6维
  5. FAA+Power — 6 FAA + 12 logP = 18维
  6. FAA+ERD  — 6 FAA + 6 ERD = 12维
  7. FULL_30  — 30维 (6频带×4 + 2频带×3 ERD)

分类器: LDA / SVM-linear / SVM-RBF / RF / KNN / XGBoost
"""

import json, time, sys
from pathlib import Path
from datetime import timedelta
import numpy as np
import mne
from scipy import signal as sig
from scipy.integrate import trapezoid
from sklearn.model_selection import LeaveOneOut, StratifiedKFold
from sklearn.preprocessing import StandardScaler
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.neighbors import KNeighborsClassifier

FS = 250.0
BANDS = {"theta":(4,8),"alpha":(8,13),"low_beta":(13,20),"high_beta":(20,30),"beta":(13,30),"broadband":(0.5,30)}
ERD_BANDS = {"alpha":(8,13),"beta":(13,30)}

BDF_SESSION_MAP = {
    "session_11.jsonl": "试次11.bdf",
    "session_12.jsonl": "试次12.bdf",
    "session_13.jsonl": "试次13.bdf",
    "session_14.jsonl": "试次14.bdf",
    "session_15.jsonl": "试次15.bdf",
}

def band_power(x, fs, lo, hi):
    nperseg = min(128, len(x)//2)
    if nperseg < 32: nperseg = len(x)//4
    if nperseg < 16: return 0.0
    f, p = sig.welch(x, fs, nperseg=nperseg)
    mask = (f >= lo) & (f <= hi)
    if mask.sum() < 2: return 0.0
    return float(trapezoid(p[mask], f[mask]))

def bp_filter(x, lo, hi, fs, order=4):
    nyq=0.5*fs; b,a=sig.butter(order,[lo/nyq,hi/nyq],btype="band"); return sig.filtfilt(b,a,x)

def notch(x, fs, f=50, q=30):
    b,a=sig.iirnotch(f,q,fs); return sig.filtfilt(b,a,x)

def clean(ch, fs):
    return notch(bp_filter(ch, 0.5, 45, fs), fs)

# ── Load all data ──
SES_DIR = Path("/Users/sssd/Desktop/跳一跳/试次数据")
BDF_DIR = Path("/Users/sssd/Downloads/实验数据")

all_features = {}  # feature_name -> X
y_all = None

for ses_name, bdf_name in BDF_SESSION_MAP.items():
    # Load BDF
    bdf_path = BDF_DIR / bdf_name
    raw = mne.io.read_raw_bdf(str(bdf_path), preload=True, verbose=False)
    data = raw.get_data()
    ch_names = raw.ch_names
    meas = raw.info.get("meas_date")
    if hasattr(meas, "timestamp"):
        bdf_start_ms = int((meas.timestamp() - 8*3600) * 1000)

    # Detect Fp1/Fp2 indices (BDF 11-15 have Fp2 at idx4, Fp1 at idx5)
    fp1_idx = ch_names.index("Fp1") if "Fp1" in ch_names else 5
    fp2_idx = ch_names.index("Fp2") if "Fp2" in ch_names else 4
    print(f"{bdf_name}: Fp1=idx{fp1_idx}, Fp2=idx{fp2_idx}")

    fp1 = clean(data[fp1_idx].astype(np.float64), FS)
    fp2 = clean(data[fp2_idx].astype(np.float64), FS)

    # Load session
    ses_path = SES_DIR / ses_name
    with open(ses_path) as f:
        trials = [json.loads(l) for l in f if l.strip() and json.loads(l).get("type")=="trial"]

    for t in trials:
        ts_ms = t["timestamp_trial_start_ms"]
        offset_s = (ts_ms - bdf_start_ms) / 1000.0
        bl_s = int(offset_s * FS)
        bl_e = int((offset_s + 2.0) * FS)
        tk_e = int((offset_s + 4.0) * FS)
        if bl_s < 0 or tk_e > len(fp1): continue
        fp1_bl = fp1[bl_s:bl_e][:500]; fp1_tk = fp1[bl_e:tk_e][:500]
        fp2_bl = fp2[bl_s:bl_e][:500]; fp2_tk = fp2[bl_e:tk_e][:500]
        if len(fp1_bl) < 400: continue

        # De-mean
        fp1_bl_c = fp1_bl - fp1_bl.mean(); fp1_tk_c = fp1_tk - fp1_tk.mean()
        fp2_bl_c = fp2_bl - fp2_bl.mean(); fp2_tk_c = fp2_tk - fp2_tk.mean()

        # Z-score normalize per window
        s1 = np.std(np.concatenate([fp1_bl_c, fp1_tk_c]))
        s2 = np.std(np.concatenate([fp2_bl_c, fp2_tk_c]))
        if s1 > 1e-10: fp1_bl_c/=s1; fp1_tk_c/=s1
        if s2 > 1e-10: fp2_bl_c/=s2; fp2_tk_c/=s2

        label = 1 if t["ground_truth"]=="left" else 2

        # --- Extract all feature groups ---
        feat = {}

        # 1. FAA: single alpha asymmetry from task window
        p1 = band_power(fp1_tk_c, FS, 8, 13); p2 = band_power(fp2_tk_c, FS, 8, 13)
        feat["FAA"] = [(p2-p1)/(p2+p1+1e-15)]

        # 2. FAA_6: 6-band FAA
        faa6 = []
        for bn, (lo,hi) in BANDS.items():
            p1b=band_power(fp1_tk_c,FS,lo,hi); p2b=band_power(fp2_tk_c,FS,lo,hi)
            faa6.append((p2b-p1b)/(p2b+p1b+1e-15))
        feat["FAA_6"] = faa6

        # 3. Power: log absolute power from task (6 bands × 2 ch = 12)
        pw = []
        for bn, (lo,hi) in BANDS.items():
            pw.append(np.log(band_power(fp1_tk_c,FS,lo,hi)+1e-15))
            pw.append(np.log(band_power(fp2_tk_c,FS,lo,hi)+1e-15))
        feat["Power"] = pw

        # 4. ERD: (task-baseline)/baseline for alpha+beta (2 bands × 3 = 6)
        erd = []
        for bn, (lo,hi) in ERD_BANDS.items():
            bl1=band_power(fp1_bl_c,FS,lo,hi); tk1=band_power(fp1_tk_c,FS,lo,hi)
            bl2=band_power(fp2_bl_c,FS,lo,hi); tk2=band_power(fp2_tk_c,FS,lo,hi)
            erd.append((tk1-bl1)/(bl1+1e-15))
            erd.append((tk2-bl2)/(bl2+1e-15))
            erd.append((tk1-bl1)/(bl1+1e-15) - (tk2-bl2)/(bl2+1e-15))
        feat["ERD"] = erd

        # 5. FAA+Power
        feat["FAA+Power"] = faa6 + pw

        # 6. FAA+ERD
        feat["FAA+ERD"] = faa6 + erd

        # 7. FULL_30
        full = []
        for bn,(lo,hi) in BANDS.items():
            p1b=band_power(fp1_tk_c,FS,lo,hi); p2b=band_power(fp2_tk_c,FS,lo,hi)
            full.extend([np.log(p1b+1e-15), np.log(p2b+1e-15),
                         (p2b-p1b)/(p2b+p1b+1e-15), np.log(p1b+p2b+1e-15)])
        for bn,(lo,hi) in ERD_BANDS.items():
            bl1=band_power(fp1_bl_c,FS,lo,hi); tk1=band_power(fp1_tk_c,FS,lo,hi)
            bl2=band_power(fp2_bl_c,FS,lo,hi); tk2=band_power(fp2_tk_c,FS,lo,hi)
            full.extend([(tk1-bl1)/(bl1+1e-15), (tk2-bl2)/(bl2+1e-15),
                         (tk1-bl1)/(bl1+1e-15)-(tk2-bl2)/(bl2+1e-15)])
        feat["FULL_30"] = full

        for k, v in feat.items():
            if k not in all_features: all_features[k] = []
            all_features[k].append(np.array(v))

        if y_all is None: y_all = []
        y_all.append(label)

y_all = np.array(y_all)
n = len(y_all)
print(f"\nTotal: {n} trials (left={np.sum(y_all==1)}, right={np.sum(y_all==2)})\n")

# ── Classifiers ──
classifiers = {
    "LDA": LinearDiscriminantAnalysis(),
    "SVM-lin": SVC(kernel="linear", C=1.0, random_state=42),
    "SVM-rbf": SVC(kernel="rbf", C=1.0, gamma="scale", random_state=42),
    "RF": RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42),
    "KNN": KNeighborsClassifier(n_neighbors=5),
}

# ── Compare ──
print(f"{'Feature':<16s} {'Dim':>4s}", end="")
for cn in classifiers: print(f" {cn:>10s}", end="")
print(f" {'Best':>12s}")
print("-" * (18 + 11*len(classifiers) + 12))

results = {}
for feat_name, X_list in sorted(all_features.items()):
    X = np.nan_to_num(np.array(X_list), nan=0, posinf=0, neginf=0)
    dim = X.shape[1]
    loo = LeaveOneOut()
    best_acc, best_clf = 0, ""

    print(f"{feat_name:<16s} {dim:>4d}", end="")
    for clf_name, clf in classifiers.items():
        accs = []
        for tr, te in loo.split(X):
            if len(np.unique(y_all[tr])) < 2: continue
            try:
                scaler = StandardScaler()
                X_tr = scaler.fit_transform(X[tr])
                X_te = scaler.transform(X[te])
                clf.fit(X_tr, y_all[tr])
                pred = clf.predict(X_te)[0]
                accs.append(1 if pred == y_all[te[0]] else 0)
            except: continue
        acc = np.mean(accs) if accs else 0
        print(f" {acc:>9.1%}", end="")
        results[(feat_name, clf_name)] = acc
        if acc > best_acc: best_acc, best_clf = acc, clf_name
    print(f" {best_acc:>8.1%} ({best_clf})")

# ── Top combinations ──
print(f"\n{'='*60}")
print("Top 10 组合")
print(f"{'='*60}")
sorted_results = sorted(results.items(), key=lambda x: -x[1])
for i, ((feat, clf), acc) in enumerate(sorted_results[:10]):
    dim = np.array(all_features[feat]).shape[1]
    print(f"  {i+1}. {feat:<14s} × {clf:<10s}  {acc:.1%}  ({dim}d)")

# ── Best per feature group ──
print(f"\n{'='*60}")
print("每组特征最高准确率")
print(f"{'='*60}")
for feat_name in sorted(all_features.keys()):
    best = max((acc, clf) for (f, clf), acc in results.items() if f == feat_name)
    dim = np.array(all_features[feat_name]).shape[1]
    print(f"  {feat_name:<16s} {dim:>3d}d → {best[0]:.1%} ({best[1]})")
