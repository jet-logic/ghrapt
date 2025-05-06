from logging import info, debug
import re


def rel(node):
    return "/".join(node.enum_names())


class FilterBase:
    __slots__ = ("next",)

    def walk(self):
        cur = self
        while cur:
            yield cur
            cur = cur.next

    def last(self):
        cur = self
        while 1:
            n = cur.next
            if n:
                cur = n
            else:
                return cur

    def append(self, that):
        self.last().next = that


class FilterRel(FilterBase):
    __slots__ = ("re", "dir_only", "glob")

    def __init__(self, re, dir_only, next_item, glob=None):
        self.re = re
        self.dir_only = dir_only
        self.next = next_item
        self.glob = glob

    # def matches(self, path):
    #     return self.re.match(path)
    def matches(self, data, rel):
        # debug("matches %s %s %r", data, rel, (self))

        return ((not self.dir_only) or (data.is_dir())) and self.re.match(rel)

    def __str__(self):
        # return "%s(<%s>, %s)" % (self.dir_only and "Dir" or "Path",  self.re.pattern, self.next and str(self.next))
        return "%s<%s>" % (
            self.dir_only and "Dir" or "Path",
            self.glob or self.re.pattern,
        )

    def __repr__(self):
        return str(self)


class FilterPath(FilterBase):
    __slots__ = ("re", "dir_only", "glob")

    def __init__(self, re, dir_only, next_item, glob=None):
        self.re = re
        self.dir_only = dir_only
        self.next = next_item
        self.glob = glob

    def matches(self, data, rel):
        return ((not self.dir_only) or (data.is_dir())) and self.re.match(
            str(data._path)
        )

    def __str__(self):
        # return "%s(<%s>, %s)" % (self.dir_only and "Dir" or "Path",  self.re.pattern, self.next and str(self.next))
        return "%s%s(%r))" % (
            self.__class__.__name__,
            self.dir_only and "Dir" or "Reg",
            self.re.pattern,
        )

    def __repr__(self):
        return str(self)


class FilterMaxSize(FilterBase):
    __slots__ = "max_size"

    def __init__(self, max_size, next_item):
        self.max_size = max_size
        self.next = next_item

    def matches(self, data, rel):
        return data.is_file() and data.size > self.max_size
        # debug("matches %s %s %r", data, rel, (self))

    def __str__(self):
        return "%s<%s>" % (
            self.__class__.__name__,
            self.max_size,
        )

    def __repr__(self):
        return str(self)


class GitIgnore:
    def parse_line(
        self, line: str, base_path: "Optional[str]" = None
    ) -> "Tuple[bool, Pattern[str], bool, str]":
        """
        Convert a .gitignore pattern to a regex with proper gitignore semantics.

        Args:
            line: A line from .gitignore file
            base_path: The directory containing this .gitignore (for absolute patterns)

        Returns:
            Tuple of (is_negation, compiled_regex, is_dir_only, original_pattern)

        Raises:
            ValueError: For invalid patterns or empty lines
        """
        # --- Input Validation ---
        line = line.strip()
        if not line or line.startswith("#"):
            raise ValueError("Empty or comment line")

        # --- Parse Special Markers ---
        is_negated = line.startswith("!")
        if is_negated:
            line = line[1:].strip()
            if not line:  # "!" with no pattern is invalid
                raise ValueError("Negation with empty pattern")

        # Handle directory marker (trailing /)
        is_dir_only = line.endswith("/")
        if is_dir_only:
            line = line[:-1]

        # Handle gitignore's special trailing space behavior
        has_trailing_space = line.endswith(" ")
        if has_trailing_space:
            line = line.rstrip() + " "  # Preserve exactly one space

        # --- Pattern Conversion ---
        regex_parts = []
        i, n = 0, len(line)

        while i < n:
            c = line[i]
            i += 1

            if c == "*":
                # Handle ** (multi-directory wildcard)
                if i < n and line[i] == "*":
                    i += 1
                    # /**/ → match zero or more directories
                    # **/ → match in any subdirectory
                    if i < n and line[i] == "/":
                        i += 1
                        regex_parts.append("(?:/[^/]+)*")
                    else:
                        regex_parts.append(".*")
                else:
                    regex_parts.append("[^/]*")  # Single * matches non-slashes

            elif c == "?":
                regex_parts.append("[^/]")  # Match any single non-slash character

            elif c == "[":
                # Handle character classes with proper escaping
                j = i
                if j < n and line[j] == "!":
                    j += 1
                if j < n and line[j] == "]":
                    j += 1

                while j < n and line[j] != "]":
                    j += 1

                if j >= n:
                    regex_parts.append("\\[")  # Unclosed bracket → literal [
                else:
                    class_contents = line[i:j]
                    # Escape special regex chars except ^ and -
                    class_contents = re.sub(r"([\].^$-])", r"\\\1", class_contents)
                    if class_contents.startswith("!"):
                        class_contents = "^" + class_contents[1:]
                    regex_parts.append(f"[{class_contents}]")
                    i = j + 1

            else:
                regex_parts.append(re.escape(c))  # Escape all other special chars

        full_pattern = "".join(regex_parts)

        # --- Anchoring Rules ---
        is_absolute = line.startswith("/")
        if is_absolute:
            # Pattern is relative to .gitignore location
            if base_path:
                anchor = re.escape(base_path) + "/"
                full_pattern = f"^{anchor}{full_pattern[1:]}"
            else:
                full_pattern = f"^{full_pattern[1:]}"
        else:
            # Pattern can match at any directory level
            full_pattern = f"(?:^|/){full_pattern}"

        # # Directory matching requires trailing slash
        # if is_dir_only:
        #     full_pattern += "/"

        full_pattern += "$"  # Ensure full match

        try:
            compiled = re.compile(full_pattern)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern for {line!r}: {str(e)}")

        return (is_negated, compiled, is_dir_only, line)

    def parse(self, rh, base=None):
        # type: (BinaryIO, str)
        for line in rh:
            line = line.strip()
            if line and not line.startswith("#"):
                yield self.parse_line(line, base)


def hook_ignore(node, data=None):
    if data is None:
        data = node.data
    _ignore = getattr(data, "_ignore", None)
    if _ignore is None:
        _ignore = data._ignore = False
        igno = data._path / ".gitignore"
        excludes = includes = None
        gi = GitIgnore()
        if igno.is_file():
            # debug(".gitignore %r", igno)
            # base = "/".join(node.enum_names())
            with igno.open("r") as h:
                for neg, re, dirOnly, pattern in gi.parse(h):
                    # debug(
                    #     "%s%s <%s>",
                    #     neg and "in" or "ex",
                    #     dirOnly and "d" or "p",
                    #     re.pattern,
                    # )
                    if neg:
                        includes = FilterRel(re, dirOnly, includes, pattern)
                    else:
                        excludes = FilterRel(re, dirOnly, excludes, pattern)
        gitd = data._path / ".git"
        if gitd.is_dir():
            (neg, re, dirOnly, pattern) = gi.parse_line("/.git/")
            excludes = FilterRel(re, dirOnly, excludes, pattern)

        if excludes or includes:
            _ignore = data._ignore = (excludes, includes)
            debug("IGF %r %s", igno, _ignore)

    (*ignores,) = filter(
        lambda v: bool(v[0]),
        map(
            (lambda n: (getattr(n.data, "_ignore", None), n)),
            node.enum_self_and_parents(),
        ),
    )
    # debug("ignores %r", ignores)

    if ignores:

        def fun(sub):

            # path = sub.data._path
            data = sub.data
            suffix = data.is_dir() and "/" or ""
            for (x, _), n in ignores:
                rel = "/".join(reversed(list(sub.enum_rel_names(n))))

                debug("X %r %r", rel, n)
                while x:  # each excludes unit in the filter
                    if x.matches(data, rel):
                        for (_, y), n in ignores:
                            rel2 = "/".join(reversed(list(sub.enum_rel_names(n))))
                            # rel = "/".join(sub.enum_rel_names(n))
                            while y:  # each includes unit in the filter
                                if y.matches(data, rel2):
                                    # debug(
                                    #     "INC %s%s %s",
                                    #     data,
                                    #     suffix,
                                    #     y,
                                    # )
                                    return False
                                y = y.next
                        debug("EXC %r %s%s", x, rel, suffix)
                        return True
                    x = x.next
            # debug("PAS %r %r", sub, ignores)

        return fun


def collect_ignore(path):
    excludes = includes = None

    while path and path.name:
        cur = path
        path = path.parent
        base = str(cur)
        igno = cur / ".gitignore"
        gi = GitIgnore()
        if igno.is_file():
            # debug(".gitignore %r", igno)
            # base = "/".join(node.enum_names())
            with igno.open("r") as h:
                for neg, re, dirOnly, pattern in gi.parse(h, base):
                    debug(
                        "%s%s <%s>",
                        neg and "in" or "ex",
                        dirOnly and "d" or "p",
                        re.pattern,
                    )
                    if neg:
                        includes = FilterPath(re, dirOnly, includes, pattern)
                    else:
                        excludes = FilterPath(re, dirOnly, excludes, pattern)
        gitd = cur / ".git"
        if gitd.is_dir():
            (neg, re, dirOnly, pattern) = gi.parse_line("/.git/", base)
            excludes = FilterPath(re, dirOnly, excludes, pattern)
    if excludes or includes:
        return (excludes, includes)


from re import Pattern
from typing import TYPE_CHECKING, Optional, Tuple

if TYPE_CHECKING:
    from typing import BinaryIO
