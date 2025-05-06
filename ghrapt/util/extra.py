def mode_name(m):
    t = m >> 12
    if 0o10 == t:
        return (m & 0b001001001) != 0 and "exec" or "blob"
    if 0o04 == t:
        return "tree"
    if 0o12 == t:
        return "syml"
    if 0o16 == t:
        return "comm"
    return "%04x" % m


def filesizef(s):
    if not s and s != 0:
        return "-"
    for x in "bkMGTPEZY":
        if s < 1000:
            break
        s /= 1024.0
    return ("%.1f" % s).rstrip("0").rstrip(".") + x


def filesizep(s):
    for i, v in enumerate("bkmgtpezy"):
        if s[-1].lower().endswith(v):
            return int(s[0:-1]) * (2 ** (10 * i))
    return int(s)


def base_encode(number, alphabet):
    # Special case for zero
    if number == 0:
        return alphabet[0]
    base, sign, size = "", "", len(alphabet)
    if number < 0:
        sign, number = "-", -number
    while number != 0:
        number, i = divmod(number, size)
        base = alphabet[i] + base
    return sign + base

def as_sink(path, mode="wb"):
    if path and path != "-":
        return open(path, mode)
    from sys import stdout

    return stdout.buffer if "b" in mode else stdout
