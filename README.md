# test3: 粘土エッジの電荷ラベルをVASP(PBE + Bader)で作る

目的は、パイロフィライト(粘土)のエッジ構造について、局所環境ごとの原子電荷をDFTで求め、
SOAP→電荷(のちにSOAP→χ→QEq)モデルの教師データにすること。
ローカルではCP2K(Hirshfeld)で一部を試したが、時間がかかるためスパコンでVASPを使う。

## 中身
| ファイル | 役割 |
|---|---|
| `C2000.gro`, `ClayCode.LICENSE.txt` | ClayCode(MIT)のパイロフィライト単位格子(Si8Al4O20(OH)4、40原子) |
| `build_edges.py` | 単位格子を切ってエッジ付きリボンを作る(切れた結合をバルク位置のO/Hで補修、形式電荷で中性化) |
| `structures/` | 構造7つ(`bulk`、y法線リボン4、x法線リボン2)。`.xyz`と`.json`(セル・周期性) |
| `make_vasp.py` | `vasp/<name>/{relax,static}/` に POSCAR/INCAR/KPOINTS を生成(生成済みをコミット済み) |
| `make_potcar.sh` | POTCARを連結(ライセンスの都合で同梱しない) |
| `run_vasp.pbs`, `submit_all.sh` | 1構造あたり relax → static → Bader のPBSジョブ |
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
export VASP_POTCAR_DIR=/path/to/potpaw_PBE     # Si, Al, O, H のPAW_PBE
bash make_potcar.sh                            # 順序は Si Al O H(POSCARと同じ)
# run_vasp.pbs の queue/select/module を編集
bash submit_all.sh                             # 7構造を独立ジョブで投入
# 完了後
python3 analyze_charges.py                     # vasp/*/static/charges.dat が全部揃っていること
```
`run_vasp.pbs` は `bader`(Henkelman)と `chgsum.pl` がPATHにあること、`ase`(解析のみ)が必要。
Baderは全電子密度(AECCAR0+AECCAR2)に対して実行する。DDEC6を使う場合は、
`static` の出力(CHGCAR, AECCAR*)から chargemol で別途計算し、同じ形式の `charges.dat` を作ればよい。

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
- `analyze_charges.py` の動作確認は、ダミーの電荷で通しただけ(実VASP結果での検証は未実施)。
- CP2K(Hirshfeld)での暫定結果: バルクはClayFFの約1/3.8のスケール。リボン2本は
  leave-one-out で固定タイプ電荷よりSOAPの平均誤差が約半分だったが、検証向き(x法線)は未計算。
