class Data:
    __slots__ = ("parent",)

    def __getattr__(self, name: str):
        if not name.startswith("_"):
            getter_name = f"_get_{name}"
            getter = getattr(self, getter_name, None)

            if getter is not None:
                setattr(self, name, None)
                value = getter()
                setattr(self, name, value)
                return value

        try:
            return super().__getattr__(name)
        except AttributeError:
            raise AttributeError(
                f"'{self.__class__.__name__}' has no attribute '{name}'. "
            ) from None


class Node(Data):
    __slots__ = (
        "name",
        "data",
        "parent",
        "next",
        "first",
    )  # type: tuple[str, Any, Optional[Node], Optional[Node], Optional[Node]]

    @property
    def root(self):
        c = self
        while c.parent:
            c = c.parent
        return c
        # c, p = self, c.parent
        # while p:
        #     c, p = p, c.parent
        # return c

    @property
    def prior(self):
        cur = self.parent
        if cur:
            cur = cur.first
            if cur is not self:
                while cur:
                    _ = cur.next
                    if _ is self:
                        return cur
                    cur = _

    def detach(self):
        p = self.parent
        p and p.remove(self)
        self.parent = None
        self.next = None
        return self

    # tree

    def _get_parent(self):
        return None

    def _get_next(self):
        return None

    def _get_first(self):
        first = cur = None
        data = self.data  # type: Data
        if data:
            for x in data.items(self):
                assert x.parent is self
                if cur is None:
                    cur = first = x
                else:
                    cur.next = cur = x
        return first

    def __iter__(self):
        cur = self.first
        while cur:
            assert cur.parent is not cur
            assert (
                cur.parent is self
            ), f"{cur.get_path()} {cur.parent.get_path()} [{(cur.parent.name)}, {(cur.name)}, {(self.name)}]"
            _ = cur.next
            yield cur
            cur = _

    def replace(self, new, old):
        cur = self.first
        prev = None
        while cur:
            if old is cur:
                if prev:
                    prev.next = new
                new.detach()
                new.next = old.next
                new.parent = self
                self.remove(old)
                break
            assert cur.parent is self
            prev = cur
            cur = cur.next

    @property
    def last(self):
        cur = self.first
        if cur:
            while cur.next:
                assert cur.parent is self, f"{cur.parent} {self}"
                cur = cur.next
        return cur

    def extend(self, itr):
        cur = self.last
        for x in itr:
            if x.parent:
                x.parent.remove(x)
            if cur is None:
                cur = self.first = x
                cur.next = None
            else:
                assert cur.parent is self
                cur.next = x
                cur = x
            x.parent = self

    def append(self, x):
        cur = self.last
        if cur:
            cur.next = x
        else:
            self.first = x
        x.parent = self
        x.next = None

    def remove(self, x):
        assert x.parent is self
        cur = self.first
        prev = None
        while cur:
            if cur is x:
                if prev is None:
                    self.first = cur.next
                else:
                    prev.next = cur.next
                cur.parent = None
                cur.next = None
                return cur
            assert cur.parent is self
            prev = cur
            cur = cur.next
        # raise ValueError(x)

    def clear(self):
        for x in self:
            x.parent = None
            x.next = None
        self.first = None

    # name

    def get_name(self, name):
        if not name:
            raise RuntimeError(f"Invalid: {name!r}")
        for x in self:
            if x.name == name:
                return x

    def intern(self, name):
        child = self.get_name(name)
        if not child:
            child = self.__class__(name, self)
            self.append(child)
        return child

    def get_sub(self, names):
        sub = self.get_name(names[0])
        if sub:
            return sub.get_sub(names[1:]) if len(names) > 1 else sub

    # extra

    def set_data(self, data):
        self.data = None
        self.clear()
        del self.first
        self.data = data
        return self

    def enum_parents(self):
        top = self.parent
        while top:
            yield top
            top = top.parent

    def enum_self_and_parents(self):
        top = self
        while top:
            yield top
            top = top.parent

    def get_path(self, sep="/"):
        a = []
        while self.parent:
            a.append(self.name)
            self = self.parent
        return sep + sep.join(reversed(a))

    def enum_names(self):
        # while self.parent:
        #     yield self.name
        #     self = self.parent
        p = self.parent
        n = self.name
        while p:
            yield n
            n = p.name
            p = p.parent

    def enum_rel_names(self, top):
        p = self.parent
        n = self.name
        while p:
            yield n
            if p == top:
                return
            n = p.name
            p = p.parent
        assert 0, "Unexpected"

    def enum_descend(self):
        p = self.parent
        if p:
            yield from p.enum_descend()
        yield self

    def enum_ascend(self):
        top = self
        while top:
            yield top
            top = top.parent

    def enum_depth_first(self):
        for sub in self:
            yield sub
            yield from sub
