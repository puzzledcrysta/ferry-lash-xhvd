from decimal import Decimal
from app.errors import DataError
from .values import number, whole, parts


def evaluate(row):
    origin = number(row['首轴距中线'], -100, 100)
    pitch = number(row['轴距'], 0, 20)
    loads = [number(item, Decimal('.001'), 100) for item in parts(row['轴载序列'])]
    cap = number(row['局部限载'], 0, 100)
    limit = number(row['总矩上限'], 0, 100000)
    lashing = whole(row['系固条数'], 0, 24)
    if not 2 <= len(loads) <= 8 or pitch == 0:
        raise DataError('BUSINESS', '轴列须含两至八轴且轴距为正')
    if lashing < 4+max(0,len(loads)-3):
        raise DataError('BUSINESS', '系固条数不足')
    moments = [(origin+pitch*i)*load for i,load in enumerate(loads)]
    net = abs(sum(moments))
    if max(loads) > cap or net > limit:
        raise DataError('BUSINESS', f'峰值轴载 {max(loads)} 吨，净弯矩 {net} 吨米')
    return net, [('负侧弯矩', sum(v for v in moments if v<0), '吨米'), ('正侧弯矩', sum(v for v in moments if v>0), '吨米'), ('峰值轴载',max(loads),'吨')]
