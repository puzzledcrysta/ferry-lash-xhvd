import json
from datetime import datetime, timezone
from app.errors import DataError
from app.evidence import distribution
from app.settings import FIELDS, UNIT
from app.store import connection
from app.modules.domain.rule import evaluate
from app.modules.reconcile.service import compare
from app.modules.runs.repository import lookup


def merged_fields(group, picks):
    disputed = group['disputed']
    if set(picks) != set(disputed):
        raise DataError('RESOLUTION_PICKS', f'争议字段须逐项核清：{"、".join(disputed)}')
    by_line = {candidate['line']: candidate for candidate in group['candidates']}
    unknown = sorted({line for line in picks.values() if line not in by_line})
    if unknown:
        raise DataError('RESOLUTION_SOURCE', f'第 {unknown[0]} 行不是该争议的来源')
    fields = dict(group['candidates'][0]['fields'])
    for field in disputed:
        fields[field] = by_line[picks[field]]['fields'][field]
    return fields


def base_line(picks):
    counts = {}
    for line in picks.values():
        counts[line] = counts.get(line, 0) + 1
    return min(counts, key=lambda line: (-counts[line], line))


def adopt(group, picks, version):
    fields = merged_fields(group, picks)
    amount, proof = evaluate(fields)
    return {'key': group['key'], 'line': base_line(picks), 'revision': group['revision'],
            'amount': format(amount, 'f'), 'unit': UNIT,
            'raw': [f'{field} · {fields[field]}' for field in FIELDS],
            'proof': [{'metric': label, 'value': str(value), 'unit': unit} for label, value, unit in proof],
            'adopted': {'picks': picks, 'sources': sorted(set(picks.values())), 'version': version}}


def latest(db, run_id):
    rows = db.execute('''SELECT r.key, r.version, r.picks, r.note, r.changed FROM resolutions r
                         JOIN (SELECT key, MAX(version) AS version FROM resolutions
                               WHERE run_id=? GROUP BY key) top
                         ON r.run_id=? AND r.key=top.key AND r.version=top.version
                         ORDER BY r.key''', (run_id, run_id))
    return [dict(row) for row in rows]


def apply_view(result, book, resolutions):
    groups = result.get('conflicts', [])
    by_key = {item['key']: item for item in resolutions}
    result['resolutions'] = [{'key': item['key'], 'version': item['version'], 'picks': json.loads(item['picks']),
                              'note': item['note'], 'changed': item['changed']} for item in resolutions]
    changed = False
    for group in groups:
        resolution = by_key.get(group['key'])
        if resolution is None:
            continue
        changed = True
        picks = json.loads(resolution['picks'])
        adopted = adopt(group, picks, resolution['version'])
        result['accepted'].append(adopted)
        lines = {candidate['line'] for candidate in group['candidates']}
        result['quarantine'] = [item for item in result['quarantine']
                                if not (item['key'] == group['key'] and item['code'] == 'REV_CONFLICT'
                                        and item['line'] in lines)]
        for candidate in group['candidates']:
            if candidate['line'] == adopted['line']:
                continue
            borrowed = [field for field in group['disputed'] if picks[field] == candidate['line']]
            detail = '未采信的来源记录' if not borrowed else f'未采信该来源；字段 {"、".join(borrowed)} 并入采信结果'
            result['suppressed'].append({'line': candidate['line'], 'key': group['key'], 'raw': candidate['raw'],
                                         'code': 'NOT_ADOPTED', 'detail': detail})
        group['released'] = True
        group['adopted'] = {'line': adopted['line'], 'version': resolution['version'],
                            'picks': picks, 'note': resolution['note']}
    if changed:
        result['accepted'].sort(key=lambda row: row['key'])
        result['suppressed'].sort(key=lambda row: row['line'])
        result['book'] = compare(result['accepted'], book)
        counts = result['counts']
        counts.update(accepted=len(result['accepted']), rejected=len(result['quarantine']),
                      suppressed=len(result['suppressed']))
        result['balanced'] = counts['input'] == sum(value for key, value in counts.items() if key != 'input')
        result['reasons'] = distribution(result['quarantine'])
    return result


def resolve(run_id, key, version, picks, note):
    note = note.strip()
    with connection() as db:
        db.execute('BEGIN IMMEDIATE')
        record = lookup(db, run_id)
        result = json.loads(record['result'])
        group = next((item for item in result.get('conflicts', []) if item['key'] == key), None)
        if group is None:
            raise DataError('CONFLICT_UNKNOWN', '该业务键没有待裁决的争议', 404)
        current = db.execute('SELECT COALESCE(MAX(version),0) FROM resolutions WHERE run_id=? AND key=?',
                             (run_id, key)).fetchone()[0]
        if current != version:
            raise DataError('STALE', '采信版本已过期，请刷新', 409)
        if not note:
            raise DataError('RESOLUTION_NOTE', '采信结论须填写复核意见')
        adopt(group, picks, current + 1)
        changed = datetime.now(timezone.utc).isoformat()
        db.execute('INSERT INTO resolutions VALUES (?,?,?,?,?,?)',
                   (run_id, key, current + 1, json.dumps(picks, sort_keys=True), note, changed))
        return {'key': key, 'version': current + 1, 'picks': picks, 'note': note, 'changed': changed}
