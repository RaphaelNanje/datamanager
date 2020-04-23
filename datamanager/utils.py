def smart_hash(obj):
    if isinstance(obj, (str, int)):
        return obj
    return hash(obj)
