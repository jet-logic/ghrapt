from .ignore import FilterRel, GitIgnore


from logging import debug


def hook_ignore(node: "LocalNode"):
    _ignore = getattr(node, "_ignore", None)
    if _ignore is None:
        _ignore = node._ignore = None
        igno = node._path / ".gitignore"
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
        gitd = node._path / ".git"
        if gitd.is_dir():
            (neg, re, dirOnly, pattern) = gi.parse_line("/.git/")
            excludes = FilterRel(re, dirOnly, excludes, pattern)

        if excludes or includes:
            _ignore = node._ignore = (excludes, includes)
            debug("IGF %r %s", igno, _ignore)

    (*ignores,) = filter(
        lambda v: bool(v[0]),
        map(
            (lambda n: (n._ignore, n)),
            node.iter_self_and_parents(),
        ),
    )
    debug("hook_ignore %r %r", node, ignores)

    if ignores:

        def fun(sub: "LocalNode"):
            debug("hook_ignore fun %r", sub)

            suffix = sub.is_dir() and "/" or ""
            for (x, _), top in ignores:
                debug("X %r", (top, sub, node))
                rel = "/".join(reversed(list(sub.iter_relative_names(top))))

                # debug("X %r %r", rel, n)
                while x:  # each excludes unit in the filter
                    if x.matches(sub, rel):
                        for (_, y), top in ignores:
                            rel2 = "/".join(
                                reversed(list(sub.iter_relative_names(top)))
                            )
                            # rel = "/".join(sub.enum_rel_names(n))
                            while y:  # each includes unit in the filter
                                if y.matches(sub, rel2):
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


# from .local_node import LocalNode
