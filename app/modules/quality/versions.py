from collections import defaultdict
from app.evidence import finding
from app.settings import FIELDS


def split_versions(records):
    groups = defaultdict(list)
    for record in records:
        groups[record['key']].append(record)
    ready, duplicates, conflicts, disputes = [], [], [], []
    for key, group in sorted(groups.items()):
        latest = max(row['revision'] for row in group)
        candidates = sorted((row for row in group if row['revision']==latest),key=lambda row:row['line'])
        older = [row for row in group if row['revision']!=latest]
        duplicates.extend(finding(row,'SUPERSEDED',f'修订 {latest} 取代旧版本') for row in older)
        signatures = {tuple(row['fields'].items()) for row in candidates}
        if len(signatures)>1:
            conflicts.extend(finding(row,'REV_CONFLICT',f'最高修订 {latest} 的来源字段互相冲突') for row in candidates)
            disputed = [field for field in FIELDS if len({row['fields'][field] for row in candidates})>1]
            disputes.append({'key':key,'revision':latest,'disputed':disputed,'released':False,
                             'candidates':[{'line':row['line'],'time':row['time'],'note':row['note'],
                                            'fields':row['fields'],'raw':row['raw']} for row in candidates]})
        else:
            ready.append(candidates[0])
            duplicates.extend(finding(row,'EXACT_DUP',f'同为修订 {latest}，保留第 {candidates[0]["line"]} 行')
                              for row in candidates[1:])
    return ready,duplicates,conflicts,disputes
