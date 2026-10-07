# test3: 粘土エッジの電荷ラベルをVASP(PBE + Bader)で作る

目的は、パイロフィライト(粘土)のエッジ構造について、局所環境ごとの原子電荷をDFTで求め、
SOAP→電荷(のちにSOAP→χ→QEq)モデルの教師データにすること。
ローカルではCP2K(Hirshfeld)で一部を試したが、時間がかかるためスパコンでVASPを使う。

## まず `cp2k/` を使う(VASPが使えない場合)
VASPが使えない環境向けに、同じ構造をCP2K(PBE、GTH、MOLOPT)で計算する版を `cp2k/` に置いた。
電荷はHirshfeld。VASP版(Bader)とは電荷のスケールが違うので、混ぜずに別々に扱うこと。
```bash
git clone https://github.com/haru2225/VASP.git && cd VASP/cp2k
qsub -q <キュー名> run_cp2k.pbs      # 全7構造: 構造最適化 → 電荷計算 → runs/<name>/charges.dat
python3 analyze_charges.py           # 完了後(要 numpy, ase, dscribe, scikit-learn)
```
- `run_cp2k.pbs` は `PATH`(なければ `/home/center/app` 以下)から `cp2k.psmp` / `cp2k.popt` と、`BASIS_MOLOPT` のあるデータディレクトリを探す。
  見つからなければ `qsub -v CP2K_EXE=...,CP2K_DATA_DIR=... run_cp2k.pbs`。MPIのmoduleが必要なら `run_cp2k.pbs` に `module load` を追記。
- 再実行すれば続きから(完了した段階は `opt.out` / `sp.out` の `PROGRAM ENDED` で判定)。1構造だけ: `-v NAME=rib_x_o00_si`。
- `make_cp2k.py` で入力を再生成、`hirshfeld_to_charges.py` で `sp.out` → `charges.dat`。入力は生成済みでコミット済み。
- 動作確認: 生成した `sp.inp` をローカルのCP2K 2026.2で実際に実行(バルク40原子、約1分、Hirshfeld出力・変換とも正常)。
  PBSの流れは偽のCP2K/mpirunでのみ確認(実機のスパコンでは未実行)。構造最適化(LBFGS、最大200ステップ)は
  ローカルでは30〜80ステップで打ち切った構造しか得ていないので、スパコンで収束まで回す想定。

## 中身
| ファイル | 役割 |
|---|---|
| `C2000.gro`, `ClayCode.LICENSE.txt` | ClayCode(MIT)のパイロフィライト単位格子(Si8Al4O20(OH)4、40原子) |
| `build_edges.py` | 単位格子を切ってエッジ付きリボンを作る(切れた結合をバルク位置のO/Hで補修、形式電荷で中性化) |
| `structures/` | 構造7つ(`bulk`、y法線リボン4、x法線リボン2)。`.xyz`と`.json`(セル・周期性) |
| `make_vasp.py` | `vasp/<name>/{relax,static}/` に POSCAR/INCAR/KPOINTS を生成(生成済みをコミット済み) |
| `make_potcar.sh` | POTCARを連結(ライセンスの都合で同梱しない) |
| `run_vasp.pbs`, `submit_all.sh` | `qsub run_vasp.pbs` で全構造を relax → static → Bader(再開可)。`submit_all.sh` は構造ごとの並列投入 |
| `bader_to_charges.py` | Bader `ACF.dat` → `vasp/<name>/static/charges.dat`(`structures/*.xyz`の原子順) |
| `analyze_charges.py` | SOAP+カーネルリッジで学習し、学習に使わない向きのエッジで検証 |

## 構造
- `bulk`: 3D周期のバルク(参照用)。
- `rib_y_o00_{si,al}`, `rib_y_o37_{si,al}`: y方向に垂直なエッジ(x方向に周期)。`o00`/`o37`は切る位置、`si`/`al`はプロトンの配分(Si–OH優先/Al–OH2優先)。**学習用**。
- `rib_x_o00_{si,al}`: x方向に垂直なエッジ(y方向に周期)。**学習に使わない検証用**。
- 全て3D周期セル+真空(リボンの法線方向14 Å、z方向 約8 Å)。形式電荷(Si+4, Al+3, O−2, H+1)で中性。
- 切断直後の幾何は粗いので、必ず `relax` から始める。

## 手順(スパコン)
```bash
git clone https://github.com/haru2225/VASP.git && cd VASP
qsub run_vasp.pbs          # これだけ。全7構造を順に relax → static → Bader
```
`run_vasp.pbs` は次を自動で行う:
- VASP実行ファイル(`PATH`、なければ `/home/center/app/VASP` 以下の `vasp_std*`)とPAW_PBEのPOTCARディレクトリを探す。
  見つからなければ、環境変数 `VASP_EXE` / `VASP_POTCAR_DIR` を指定する(`qsub -v VASP_EXE=...,VASP_POTCAR_DIR=... run_vasp.pbs`)。
- POTCARを作る(`make_potcar.sh`、順序 Si Al O H)。
- 構造ごとに、収束した `relax` の構造で `static` を実行し、`bader` と `chgsum.pl` があれば Bader 電荷を `vasp/<name>/static/charges.dat` に書く。
- 途中で止まっても、同じ `qsub run_vasp.pbs` で続きから再開(完了した段階はスキップ)。
- 1構造だけ: `qsub -v NAME=rib_x_o00_si run_vasp.pbs`、構造ごとに並列ジョブ: `bash submit_all.sh`。

キュー指定(`#PBS -q`)は入れていない(既定キュー)。必要なら `run_vasp.pbs` に追記。リソース(`ncpus=32`、`walltime=24:00:00`)は仮置き。
全構造が終わったら:
```bash
python3 analyze_charges.py   # 要 ase, dscribe, scikit-learn
```
Baderが無い環境では `charges.dat` ができないので、`static` の CHGCAR/AECCAR を使って別途Bader(またはDDEC6)を計算し、同形式の `charges.dat` を作る。

## 計算条件
PBE、PAW、ENCUT 520 eV、Γ中心k点(約20 Å/L、真空方向は1)、Gaussian smearing 0.05 eV、
EDIFF 1e−6、`relax`はセル固定でEDIFFG −0.02、`static`で`LAECHG=.TRUE.`。
リボンは法線方向の双極子補正(`IDIPOL`)付き。スピン分極なし。
walltimeは24 h(32コア)を仮置き。リボン約95原子なら通常は足りるはずだが、実測で調整。

## 注意
- 学習できる環境はクレイ原子のみ(水・イオン・基底面は未対応)。
- BaderのSi/Alは+3前後、Oは−1.6前後で、ClayFF(+2.1, +1.575, −1.05)とスケールが違う。
  MDに使う場合はスケール換算が必要(`analyze_charges.py`はバルクのクラス別比を出力する)。
- 電荷ラベルがClayFFそのものではなくDFT由来になる点が本来の目的。これを教師に、
  最終的には SOAP→χ→QEq(水は固定電荷)で可変電荷MDを作る計画(test4)。
- `run_vasp.pbs` の流れは、偽の VASP/mpirun/bader を使ったモックでのみ確認した(実VASPでは未実行)。`analyze_charges.py` もダミーの電荷で通しただけ。
- CP2K(Hirshfeld)での暫定結果: バルクはClayFFの約1/3.8のスケール。リボン2本は
  leave-one-out で固定タイプ電荷よりSOAPの平均誤差が約半分だったが、検証向き(x法線)は未計算。
