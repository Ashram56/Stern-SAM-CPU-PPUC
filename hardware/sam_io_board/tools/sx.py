import re
def spans(text, start=None, end=None):
    """Yield (start,end) spans of direct child lists inside the list starting at `start`."""
    if start is None:
        start = text.index('(')
    i = start + 1; depth = 0; out = []; s = None
    n = len(text)
    while i < n:
        c = text[i]
        if c == '"':
            i += 1
            while text[i] != '"':
                if text[i] == '\\': i += 1
                i += 1
        elif c == '(':
            if depth == 0: s = i
            depth += 1
        elif c == ')':
            if depth == 0: return out
            depth -= 1
            if depth == 0: out.append((s, i + 1))
        i += 1
    return out
def head(t): 
    m = re.match(r'\((\S+)', t); return m.group(1)
def items(text):
    return [(head(text[a:b]), a, b) for a, b in spans(text)]
def at(t):
    m = re.search(r'\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)', t)
    return (float(m.group(1)), float(m.group(2)), float(m.group(3) or 0)) if m else None
def name(t):
    m = re.match(r'\(\S+ "([^"]*)"', t); return m.group(1) if m else None
def prop(t, key):
    m = re.search(r'\(property "%s" "([^"]*)"' % re.escape(key), t); return m.group(1) if m else None
def pts(t):
    return [(float(a), float(b)) for a, b in re.findall(r'\(xy ([-\d.]+) ([-\d.]+)\)', t)]
