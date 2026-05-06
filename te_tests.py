def _unpack_object(o, id_fields=None, title_fields=None):
    """Unpack a SOAP object into a dict.

    When `id_fields` / `title_fields` are provided, the dict gains normalized
    top-level "id" and "title" strings derived from those candidate lists in
    priority order. The raw per-field keys remain on the dict.
    """
    res = {"extid": o["extid"]}
    for f in o["fields"]["field"]:
        res[f["extid"]] = f["value"][0]
        
    print("res after unpacking fields:", res)

    def _pick(candidates, type):
        if not candidates:
            return ""
        titles = []
        for k in candidates:
            v = res.get(k)
            if type == "title":
                titles.append(v)
            else:
                if v not in (None, ""):
                    return v
        return " - ".join(filter(lambda t: t not in (None, ""), titles)) if titles else ""
    
    

    res["id"] = _pick(id_fields, "id")
    res["title"] = _pick(title_fields, "title")
    print("res after picking id/title:", _pick(id_fields, "id"), _pick(title_fields, "title"))
    print((id_fields, title_fields), " id:", res["id"], "title=", res["title"])
    return res


if __name__ == "__main__":
    object = {
    'extid': 'HT2026:O7541',
    'fields': {
        'field': [
            {
                'extid': 'Namn',
                'value': [
                    'AH003A O7541 HT2026 Flexibel  Sundsvall/Östersund DST'
                ]
            },
            {
                'extid': 'kurs-programtillfälle.termin-aktiv',
                'value': [
                    'HT2026'
                ]
            },
            {
                'extid': 'kurs-programtillfälle.ort',
                'value': [
                    'Annan ort'
                ]
            },
            {
                'extid': 'Undervisningsform',
                'value': [
                    'DST'
                ]
            },
            {
                'extid': 'Poäng',
                'value': [
                    '7.5'
                ]
            },
            {
                'extid': 'Institution',
                'value': [
                    'HOV'
                ]
            },
            {
                'extid': 'Startvecka',
                'value': [
                    '202646'
                ]
            },
            {
                'extid': 'Slutvecka',
                'value': [
                    '202702'
                ]
            },
            {
                'extid': 'Kurstid',
                'value': [
                    'DAG'
                ]
            },
            {
                'extid': 'BenamnS',
                'value': [
                    'Arbetshälsovetenskap AV, Hållbara organisationer'
                ]
            },
            {
                'extid': 'BenamnE',
                'value': [
                    'Occupational Health Science MA, Sustainable Organizations'
                ]
            },
            {
                'extid': 'Ämne',
                'value': [
                    'AHV'
                ]
            },
            {
                'extid': 'Kurskod',
                'value': [
                    'AH003A'
                ]
            },
            {
                'extid': 'Anmälningskod',
                'value': [
                    'O7541'
                ]
            },
            {
                'extid': 'Kurstakt',
                'value': [
                    '50'
                ]
            },
            {
                'extid': 'kurs-programtillfälle.campus-ort',
                'value': [
                    'Annan ort'
                ]
            }
        ]
    },
    'created': '20250208T045949',
    'modified': '20260506T044814',
    'createdBy': {
        'loginname': 'Miunweb',
        'authserver': '68c16a8c68257d321ffe9040'
    },
    'modifiedBy': {
        'loginname': 'Miunweb',
        'authserver': '68c16a8c68257d321ffe9040'
    },
    'virtual': False
    }
    id_fields=['Kurskod', 'general.id', 'general.id_ref']
    title_fields=['Namn', 'general.title', 'general.title_ref']
    _unpack_object(object, id_fields=id_fields, title_fields=title_fields)