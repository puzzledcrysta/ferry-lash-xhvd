import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_ROOT = ROOT / 'sample_data'
DB = Path(os.getenv('WORKBENCH_DB', str(ROOT/'state/ledger.sqlite3')))
TITLE = '滚装配载台'
SLUG = 'ferry-lash'
KEY = '配载单'
FIELDS = ('首轴距中线', '轴距', '轴载序列', '局部限载', '总矩上限', '系固条数')
ROLE = '滚装船配载审核员'
UNIT = '吨米'
SIGNATURE = '横向力矩'
RULE_VERSION = 'ferry-lash-1.0'
TABS = {'intake': '来源采信', 'contract': '字段解释', 'quality': '隔离裁决', 'domain': '甲板复核', 'reconcile': '独立对账', 'runs': '批次复算', 'review': '交付复核'}
