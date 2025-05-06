from pathlib import Path

from .hook_ignore import hook_ignore
from .repo_node import RepoAux, RepoNode
from .ignore import FilterBase
from stat import S_IFMT, S_IMODE

SEPARATOR = "/"


def reserve_symlink(p):
    return False


_reserve_symlink = [reserve_symlink, reserve_symlink]


class LocalNode(RepoNode):
    __slots__ = (
        "mode",
        "_path",
        "_ignore",
    )  # type: tuple[int,Path, None|tuple[None|FilterBase,None|FilterBase]]

    def stat(self):
        return self._path.lstat()

    def _get_mode(self):
        return self.stat().st_mode

    def _get_perm(self):
        return S_IMODE(self.mode)

    def _get_type(self):
        return S_IFMT(self.mode)

    def _get_mtime(self):
        return self.stat().st_mtime

    def _get_size(self):
        return self.stat().st_size

    def _get_hash(self):
        if self.is_symlink():
            from os import readlink

            return self.calc_hash_symlink_target(readlink(str(self._path)))
        elif self.is_file():
            return get_hash_reg(self)
        elif self.is_dir():
            return self.calc_hash_tree()
        raise NotImplementedError(f"{self!r}")

    def _get__ignore(self):
        return None

    def __repr__(self):
        return f"{self.__class__.__name__}({self.aux!r}, {self._path!r})"


def get_hash_reg(self: LocalNode, bufsiz=64 * 1024):
    # debug("calc_hash_blob %r", self)
    size = self.size
    path = self._path
    m = sha1()
    m.update(b"blob ")
    m.update(str(size).encode())
    m.update(b"\x00")
    with path.open("rb") as h:
        b = h.read(bufsiz)
        while b:
            m.update(b)
            b = h.read(bufsiz)
    return m.hexdigest()


# class PathDataOverlay(LocalData):
#     __slots__ = "dirs"

#     def __init__(self, *dirs):
#         self.dirs = dirs
#         self.type = 0x4000
#         self.size = None
#         self.perm = 0
#         # self.hash = None
#         self.mode = 0x4000

#     def items(self, node):
#         seen = {}
#         key_name = lambda p: p.name.lower()  # noqa: E731
#         for p in self.dirs:
#             print(p)
#             for s in LocalData(p).items(node):
#                 k = key_name(s.data.path)
#                 x = seen.get(k)
#                 # print('SOverlay.items', k, s, x)
#                 if x:
#                     info("Skipped %r | %r", (s.data.path), x.data.path)
#                 else:
#                     seen[k] = s
#                     yield s


class LocalAux(RepoAux):

    def reserve_symlink_reg(self, x: LocalNode):
        return False

    def reserve_symlink_dir(self, x: LocalNode):
        return False

    def open(self, mode="r", buffering=-1, encoding=None, errors=None, newline=None):
        # print("open", mode, self.path)
        return self._path.open(
            mode, buffering=buffering, encoding=encoding, errors=errors, newline=newline
        )

    def stat(self):
        return self._path.lstat()

    def __repr__(self):
        return "%s()" % (self.__class__.__name__)

    def __str__(self):
        return "%s()" % (self.__class__.__name__)

    def filter_dir(self, node):
        return hook_ignore(node)

    def items(self, node: LocalNode):
        # print(f"LIST {node!r}", node.is_dir(), node.mode, node.type)
        if not node.is_dir():
            return
        path = node._path
        ignore = self.filter_dir(node)
        # info("ITEMS %r", path)
        for child in path.iterdir():
            # print(f"CHLD {child!r}")
            v = self.node_from(child, child.name, node)
            assert v.parent is node
            assert v.aux is self
            if not (ignore and ignore(v)):
                # info("\titem %r", child)
                yield v

    def symlink_strategy(self, *args):
        from logging import error

        def rel_path(pto, pfrom, sep="/"):
            tp = pto.parts
            fp = pfrom.parts
            for i, v in enumerate(fp):
                if len(tp) > i:
                    if v != tp[i]:
                        return (len(fp) - i - 1) * (".." + sep) + sep.join(tp[i:])
                else:
                    return None
                    assert 0, f"{(pto, pfrom, sep)}"

        def safe(cur: LocalNode):
            if not cur:
                return False
            try:
                ptop = cur.root._path
            except AttributeError:
                return False
            try:
                pcur = cur.root._path
            except AttributeError:
                return False
            target = pcur.resolve()
            try:
                rel1 = target.relative_to(ptop)
            except ValueError:
                info("SLF %r => %r", pcur, target)
                return False
            except Exception:
                error(
                    "symlink_strategy:safe %r", ((cur, pcur), (cur.root, pcur), target)
                )
                raise
            else:
                rel1 = rel_path(target, pcur)
                rel2 = cur.readlink()
                if rel1 is None or rel2 == rel1:
                    info("SYM Keep %r => %r => %r", pcur, rel2, target)
                    return True
                info("SYM Alter %r => %r | %r => %r", pcur, target, rel1, rel2)
                return rel1

        for v, n in zip(args, ("reserve_symlink_reg", "reserve_symlink_dir")):
            if v == "keep":
                setattr(self, n, lambda syml: True)
            elif v == "follow":
                setattr(self, n, lambda syml: False)
            elif v == "safe":
                setattr(self, n, safe)
            else:
                raise RuntimeError(f"Invalid follow_links {v!r}")

    def node_from(self, path: Path, name="?", parent: "LocalNode|None" = None):
        n = LocalNode(name, parent)
        n.aux = self
        if path.is_symlink():
            n._path = path
            r = (
                self.reserve_symlink_dir(n)
                if path.is_dir()
                else self.reserve_symlink_reg(n)
            )
            info("SYM %r %r", path, r)
            if r is True:
                # n._path = path.resolve()
                pass
            elif r:
                n._target = r  # retain symlink supply target
            else:
                assert r is False
                try:
                    return self.node_from(path.resolve(), name, parent)
                except FileNotFoundError:
                    n._path = path
        elif path.is_dir():
            n._path = path
        else:
            n._path = path
        return n


from logging import debug, info
from hashlib import sha1
