def decorate(keyword):
    def wrapper(f):
        def _(*args, **kwargs):
            res = f(*args, **kwargs)
            if res:
                res = "\n".join(("-" * (len(keyword) + 2), "|{}|".format(keyword), "-" * (len(keyword) + 2), res))
            return res

        return _

    return wrapper
