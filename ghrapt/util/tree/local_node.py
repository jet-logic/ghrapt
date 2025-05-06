from pathlib import Path
from .repo_node import RepoData
from .ignore import hook_ignore
from stat import S_IFMT, S_IMODE

SEPARATOR = "/"


def reserve_symlink(p):
    return False


_reserve_symlink = [reserve_symlink, reserve_symlink]


def local_data(path, node=None):
    if path.is_symlink():
        r = _reserve_symlink[1 if path.is_dir() else 0](node)
        info("SYM %r %r", path, r)
        if r is True:
            return SymlData(path)  # retain symlink
        elif r:
            data = SymlData(path)
            data._target = r  # retain symlink supply target
            return data
        else:
            assert r is False
            try:
                return local_data(path.resolve(), node)
            except FileNotFoundError:
                return SymlData(path)  # retain symlink
    elif path.is_dir():
        return DirData(path)
    else:
        return BlobData(path)


class LocalData(RepoData):
    # __slots__ = ("_path", "_target")
    __slots__ = ("_path", "mode", "aux")

    def __init__(self, path):
        self._path = path

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
        return self.get_hash()

    def open(self, mode="r", buffering=-1, encoding=None, errors=None, newline=None):
        # print("open", mode, self.path)
        return self._path.open(
            mode, buffering=buffering, encoding=encoding, errors=errors, newline=newline
        )

    def stat(self):
        return self._path.lstat()

    def __repr__(self):
        return "%s(%r, %04X)" % (self.__class__.__name__, self._path, self.type)


def symlink_strategy(*args):
    from logging import error

    global reserve_symlink, reserve_dir_symlink

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

    def safe(cur):
        if not cur:
            return False
        try:
            ptop = cur.root.data._path
        except AttributeError:
            return False
        try:
            pcur = cur.data._path
        except AttributeError:
            return False
        target = pcur.resolve()
        try:
            rel1 = target.relative_to(ptop)
        except ValueError:
            info("SLF %r => %r", pcur, target)
            return False
        except Exception:
            error("symlink_strategy:safe %r", ((cur, pcur), (cur.root, pcur), target))
            raise
        else:
            rel1 = rel_path(target, pcur)
            rel2 = cur.readlink()
            if rel1 is None or rel2 == rel1:
                info("SYM Keep %r => %r => %r", pcur, rel2, target)
                return True
            info("SYM Alter %r => %r | %r => %r", pcur, target, rel1, rel2)
            return rel1

    for i, v in enumerate(args):
        if v == "keep":
            _reserve_symlink[i] = lambda syml: True
        elif v == "follow":
            _reserve_symlink[i] = lambda syml: False
        elif v == "safe":
            _reserve_symlink[i] = safe
        elif not v:
            pass
        else:
            raise RuntimeError("Invalid follow_links %r" % (v,))


class SymlData(LocalData):
    __slots__ = "_target"

    # def __init__(self, path):
    #     super().__init__(path)
    #     self.type = self.mode = 0xA000

    # @property
    # def mtime(self):
    #     return self.stat().st_mtime

    def readlink(self):
        try:
            t = self._target
        except AttributeError:
            p = self._path
            r = getattr(p, "readlink", None)
            if r:
                self._target = t = r()
            else:
                from os import readlink

                self._target = t = readlink(str(p))
        return t

    def get_hash(self):
        content = self.readlink().encode("UTF-8")
        info("calc_hash_syml %r %r", self, content)
        size = len(content)
        m = sha1()
        m.update(b"blob ")
        m.update(str(size).encode())
        m.update(b"\x00")
        m.update(content)
        self.size = size
        return m.hexdigest()

    def _get__target(self):
        return self.read_link()

    def _get_size(self):
        return len(self._target.encode("UTF-8"))


class BlobData(LocalData):
    def get_hash(self, bufsiz=64 * 1024):
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


class DirData(LocalData):
    __slots__ = ("_ignore",)

    def _get_size(self):
        raise AttributeError("size", self.__class__, "Not implemented")

    def _get_hash(self):
        raise AttributeError("hash", self.__class__, "Not implemented")

    def filter_dir(self, node):
        # return hook_filter(node)
        return hook_ignore(node, self)

    def items(self, node):
        path = self._path
        ignore = self.filter_dir(node)
        NClass = node.__class__
        # info("ITEMS %r", path)
        for child in path.iterdir():
            v = NClass(child.name, node)
            v.data = local_data(child, v)
            if not (ignore and ignore(v)):
                # info("\titem %r", child)
                yield v


class PartData(LocalData):
    pass


class PathDataOverlay(LocalData):
    __slots__ = "dirs"

    def __init__(self, *dirs):
        self.dirs = dirs
        self.type = 0x4000
        self.size = None
        self.perm = 0
        # self.hash = None
        self.mode = 0x4000

    def items(self, node):
        seen = {}
        key_name = lambda p: p.name.lower()  # noqa: E731
        for p in self.dirs:
            print(p)
            for s in LocalData(p).items(node):
                k = key_name(s.data.path)
                x = seen.get(k)
                # print('SOverlay.items', k, s, x)
                if x:
                    info("Skipped %r | %r", (s.data.path), x.data.path)
                else:
                    seen[k] = s
                    yield s


from logging import debug, info
from hashlib import sha1
