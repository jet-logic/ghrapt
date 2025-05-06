from .node import Node, Aux


class RepoNode(Node):
    __slots__ = (
        "type",
        "size",
        "perm",
        "mtime",
        "hash",
    )  # type: tuple[int, int, int, int, str]

    def is_dir(self):
        return self.aux.is_dir(self)

    def is_file(self):
        return self.aux.is_file(self)

    def is_symlink(self):
        return self.aux.is_symlink(self)

    def iter_sort(self, file_mode=False, emptyDir=None):
        # print("iter_sort e", self.get_path())
        for node in self:
            name = node.name
            kind = node.type
            perm = node.perm
            yield name + "/" if 0x4000 == kind else name, name, kind, perm, node

    def calc_hash_tree(self, file_mode=False, skip_empty=True):
        # debug("calc_hash_tree %r", self)
        content = []
        for _, name, kind, perm, sub in sorted(self.iter_sort()):
            if 0x4000 == kind:
                mode = b"40000 "
                # checksum = sub.calc_hash_tree()
                checksum = sub.get_hash()
                if skip_empty:
                    if checksum == "4b825dc642cb6eb9a060e54bf8d69288fbee4904":
                        info("EMD %r", sub)
                        # self.remove(sub)
                        continue
                checksum = unhexlify(checksum)
            elif 0xE000 == kind:
                mode = b"160000 "
                checksum = unhexlify(sub.hash)
            elif 0xA000 == kind:
                mode = b"120000 "
                checksum = unhexlify(sub.hash)
            elif file_mode and (perm & 0b001001001) != 0:
                mode = b"100755 "
                checksum = unhexlify(sub.hash)
            else:
                mode = b"100644 "
                checksum = unhexlify(sub.hash)
            content.append(mode + name.encode("UTF-8") + b"\x00" + checksum)
        content = b"".join(content)
        content = b"tree " + str(len(content)).encode() + b"\x00" + content
        self.size = len(content)
        m = sha1()
        m.update(content)
        return m.hexdigest()

    def calc_hash_symlink_target(self, content: str):
        content = content.encode("UTF-8")
        self.size = size = len(content)
        m = sha1()
        m.update(b"blob ")
        m.update(str(size).encode())
        m.update(b"\x00")
        m.update(content)
        return m.hexdigest()

    def get_hash(self):
        aux = self.aux
        if aux.is_dir(self):
            try:
                h = self.hash
            except AttributeError:
                h = None
            except NotImplementedError:
                h = None
            if not h:
                self.hash = h = self.calc_hash_tree()
            return h
        else:
            return aux.get_hash(self)

    def get_sub_dir(self, name, *names):
        sub = self.get_name(name)
        if not sub:
            raise RuntimeError(f"Not found: {name!r}")
        elif not sub.is_dir():
            raise RuntimeError(f"Not a directory: {name!r}")
        elif names:
            return sub.get_sub_dir(*names)
        return sub

    def get_sub_dir_or_intern(self, name, *names):
        sub = self.get_name(name)
        if not sub:
            sub = self.intern(name)
        elif not sub.is_dir():
            raise RuntimeError(f"Not a directory: {name!r}")
        elif names:
            return sub.get_sub_dir_or_intern(*names)
        return sub

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self.aux)


class RepoAux(Aux):

    def is_dir(self, node: RepoNode):
        return node.type == 0x4000

    def is_file(self, node: RepoNode):
        return node.type & 0x8000 != 0

    def is_symlink(self, node: RepoNode):
        return node.type == 0xA000


from binascii import unhexlify
from hashlib import sha1
from logging import info
