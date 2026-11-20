# 滚装配载台深度登记

- 规模：中型
- 核心规则：按有效车位、轴距和轴载计算参考点两侧净弯矩，超局部轴载或超总矩时隔离。
- 使用者与工作流：滚装船配载审核员按配载单复算来源批次，对照外部记录后提交复核。

## 功能模块

| 模块 | 使用者动作 | 入口 | 核心文件 | 测试 |
|---|---|---|---|---|
| M1 来源采信 | 接收分段记录、定位坏行 | `POST /api/intake` | `app/modules/intake/service.py` | `tests/test_intake.py` |
| M2 字段解释 | 归一主键、版本、时间和原字段 | `POST /api/contract` | `app/modules/contract/service.py` | `tests/test_contract.py` |
| M3 隔离裁决 | 归并重复、隔离争议版本、复核员逐项采信争议字段 | `POST /api/quality`、`POST /api/quality/resolve/{run_id}` | `app/modules/quality/versions.py`、`app/modules/quality/resolutions.py` | `tests/test_quality.py`、`tests/test_resolution.py` |
| M4 甲板复核 | 复算业务明细与边界证据 | `POST /api/domain` | `app/modules/domain/rule.py` | `tests/test_domain.py` |
| M5 独立对账 | 核对外部记录并分别计量 | `POST /api/reconcile` | `app/modules/reconcile/service.py` | `tests/test_reconcile.py` |
| M6 批次复算 | 保存运行、查询历史、复算原输入 | `POST /api/runs` | `app/modules/runs/service.py` | `tests/test_runs.py` |
| M7 交付复核 | 复核差异、阻止陈旧提交、导出证据 | `GET /api/export` | `app/modules/review/decisions.py` | `tests/test_review.py` |

## 陷阱登记

| TRAP | 现象 | 样例 | 处理位置 | 测试 |
|---|---|---|---|---|
| TRAP-02 | BOM | shift.csv | `app/modules/intake/service.py` | `tests/test_intake.py::test_bom` |
| TRAP-03 | 引号内换行 | shift.csv | `app/modules/intake/service.py` | `tests/test_intake.py::test_multiline` |
| TRAP-04 | 重复表头 | shift.csv | `app/modules/intake/service.py` | `tests/test_intake.py::test_repeated` |
| TRAP-05 | 列数不齐 | shift.csv | `app/modules/intake/service.py` | `tests/test_intake.py::test_width` |
| TRAP-07 | 空值哨兵 | shift.csv | `app/modules/contract/service.py` | `tests/test_contract.py::test_missing` |
| TRAP-08 | 主键前导零 | shift.csv | `app/modules/contract/service.py` | `tests/test_contract.py::test_leading_zero` |
| TRAP-11 | 偏移时间归一 | shift.csv | `app/modules/contract/service.py` | `tests/test_contract.py::test_offsets` |
| TRAP-14 | 等版本冲突 | shift.csv | `app/modules/quality/versions.py` | `tests/test_quality.py::test_conflicting` |
| TRAP-31 | 等修订补正各自更新不同字段 | shift.csv 00899 | `app/modules/quality/resolutions.py` | `tests/test_resolution.py::test_merge_releases_vehicle` |
| TRAP-18 | 三种空态 | 测试构造输入 | `app/modules/intake/service.py` | `tests/test_intake.py::test_empty_states` |
| TRAP-26 | 陈旧复核 | 测试构造输入 | `app/modules/review/decisions.py` | `tests/test_review.py::test_stale` |
| TRAP-10 | 轴荷与位置乘积按十进制精确合计 | cases.csv | `app/modules/domain/rule.py` | `tests/test_domain.py::test_opposing` |

## 对账规则

输入记录数 = 计入 + 隔离 + 去重和替换 + 空白记录 + 重复表头。
业务账按配载单全外连接。差异分别标记漏记、外部单边和数值不符，以吨米对差。

## 采信规则

同修订冲突按争议字段逐项选择来源行，未核清不得放行。采信结果以贡献字段最多的来源行为基（并列取最早行），
其余来源行列入未采信。争议组出隔离时守恒：1 条计入 + 剩余候选入未采信。采信按版本追加，切换须先通过
字段与业务校验，失败保留旧版。工作台与导出共用同一采信结论，复算原输入不新增也不丢失记录。

## 范围

本地文件与单机复核。单次来源文本限 128 KiB。复合字段单项最多 240 段。
