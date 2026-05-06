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
        return " - ".join(titles)
    
    

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
                'extid': 'Kurskod',
                'value': [
                    'AH003A'
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
            }
        ]
    },
    'virtual': False}
    id_fields=['Kurskod']
    title_fields=['Namn', 'BenamnS', 'BenamnE']
    _unpack_object(object, id_fields=id_fields, title_fields=title_fields)