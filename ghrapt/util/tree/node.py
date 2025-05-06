from typing import Iterable


class Aux:
    def items(self):
        yield Node()
        raise NotImplementedError()


class Node:
    """
    Represents a node in a tree-like data structure.
    """

    __slots__ = (
        "name",
        "aux",
        "parent",
        "next_sibling",
        "first_child",
    )  # type: tuple[str, Aux | None, "Node|None", "Node|None", "Node|None"]

    def __init__(
        self,
        name: str,
        # aux: "Aux | None" = None,
        parent: "Node|None" = None,
    ) -> None:
        """
        Initializes a new Node.

        Args:
            name: The name of the node.
            aux: Auxiliary data associated with the node (optional).
            parent: The parent node (optional).
        """
        if not isinstance(name, str) or not name:
            raise ValueError("Node name must be a non-empty string.")

        self.name = name
        # self.aux = aux
        self.parent = parent
        if parent:
            self.aux = parent.aux
        # self.next_sibling = None
        # self.first_child = None

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

    @property
    def root(self) -> "Node":
        """
        Gets the root node of the tree.
        """
        current = self
        while current.parent:
            current = current.parent
        return current

    @property
    def prior(self):
        cur = self.parent
        if cur:
            cur = cur.first_child
            if cur is not self:
                while cur:
                    _ = cur.next
                    if _ is self:
                        return cur
                    cur = _

    @property
    def previous_sibling(self) -> "Node|None":
        """
        Gets the previous sibling of the node.
        """
        if self.parent:
            current = self.parent.first_child
            if current is not self:
                while current and current.next_sibling is not self:
                    current = current.next_sibling
                return current
        return None

    def detach(self) -> "Node":
        """
        Removes the node from its parent.
        """
        if self.parent:
            self.parent.remove_child(self)
        self.parent = None
        self.next_sibling = None
        return self

    # tree

    def _get_parent(self) -> "Node|None":
        """
        Getter for the parent attribute (lazy-loaded).
        """
        return None

    def _get_next_sibling(self) -> "Node|None":
        """
        Getter for the next_sibling attribute (lazy-loaded).
        """
        return None

    def _get_first_child(self) -> "Node|None":
        """
        Getter for the first_child attribute (lazy-loaded).
        """
        first_child: "Node|None" = None
        cur: "Node|None" = None
        if self.aux:
            for child in self.aux.items(self):
                if child.parent is not self:
                    raise ValueError(f"Child node '{child.name}' has incorrect parent.")
                if cur is None:
                    cur = first_child = child
                else:
                    cur.next_sibling = child
                    cur = child
        return first_child

    def __iter__(self) -> Iterable["Node"]:
        """
        Iterates over the child nodes.
        """
        current_child = self.first_child
        while current_child:
            if current_child.parent is not self:
                raise ValueError(
                    f"Child node '{current_child.name}' has incorrect parent "
                    f"(expected: {self.name}, actual: {current_child.parent.name})."
                )
            yield current_child
            current_child = current_child.next_sibling

    def replace_child(self, new_child: "Node", old_child: "Node") -> None:
        """
        Replaces a child node with a new node.

        Args:
            new_child: The new node to replace the old node.
            old_child: The node to be replaced.
        """
        if new_child is old_child:
            return  # Nothing to do

        previous_child: "Node|None" = None
        current_child = self.first_child

        while current_child:
            if old_child is current_child:
                if previous_child:
                    previous_child.next_sibling = new_child
                else:
                    self.first_child = new_child

                new_child.detach()  # Ensure new_child is detached
                new_child.next_sibling = old_child.next_sibling
                new_child.parent = self
                self.remove_child(old_child)
                return

            if current_child.parent is not self:
                raise ValueError(
                    f"Child node '{current_child.name}' has incorrect parent "
                    f"(expected: {self.name}, actual: {current_child.parent.name})."
                )
            previous_child = current_child
            current_child = current_child.next_sibling

        raise ValueError(f"Node '{old_child.name}' is not a child of '{self.name}'.")

    @property
    def last_child(self) -> "Node|None":
        """
        Gets the last child node.
        """
        current_child = self.first_child
        if current_child:
            while current_child.next_sibling:
                if current_child.parent is not self:
                    raise ValueError(
                        f"Child node '{current_child.name}' has incorrect parent "
                        f"(expected: {self.name}, actual: {current_child.parent.name})."
                    )
                current_child = current_child.next_sibling
        return current_child

    def extend_children(self, children: Iterable["Node"]) -> None:
        """
        Adds multiple nodes as children.

        Args:
            children: An iterable of Node objects to add as children.
        """
        last_child = self.last_child
        for child in children:
            if child.parent:
                child.parent.remove_child(child)
            if last_child is None:
                self.first_child = child
            else:
                if last_child.parent is not self:
                    raise ValueError(
                        f"Child node '{last_child.name}' has incorrect parent "
                        f"(expected: {self.name}, actual: {last_child.parent.name})."
                    )
                last_child.next_sibling = child
            child.parent = self
            child.next_sibling = None
            last_child = child

    def append_child(self, child: "Node") -> None:
        """
        Appends a node as the last child.

        Args:
            child: The Node object to append.
        """
        if child.parent:
            child.parent.remove_child(child)  # Detach from previous parent

        last_child = self.last_child
        if last_child:
            if last_child.parent is not self:
                raise ValueError(
                    f"Child node '{last_child.name}' has incorrect parent "
                    f"(expected: {self.name}, actual: {last_child.parent.name})."
                )
            last_child.next_sibling = child
        else:
            self.first_child = child
        child.parent = self
        child.next_sibling = None

    def remove_child(self, child: "Node") -> "Node":
        """
        Removes a child node.

        Args:
            child: The Node object to remove.

        Returns:
            The removed Node object.

        Raises:
            ValueError: If the node is not a child of this node.
        """
        if child.parent is not self:
            raise ValueError(f"Node '{child.name}' is not a child of '{self.name}'.")

        previous_child: "Node|None" = None
        current_child = self.first_child

        while current_child:
            if current_child is child:
                if previous_child is None:
                    self.first_child = current_child.next_sibling
                else:
                    previous_child.next_sibling = current_child.next_sibling
                child.parent = None
                child.next_sibling = None
                return child
            if current_child.parent is not self:
                raise ValueError(
                    f"Child node '{current_child.name}' has incorrect parent "
                    f"(expected: {self.name}, actual: {current_child.parent.name})."
                )
            previous_child = current_child
            current_child = current_child.next_sibling

        raise ValueError(f"Node '{child.name}' is not a child of '{self.name}'.")

    def clear_children(self) -> None:
        """
        Removes all child nodes.
        """
        for child in self:
            child.parent = None
            child.next_sibling = None
        self.first_child = None

    # name

    def get_child_by_name(self, name: str) -> "Node|None":
        """
        Gets a child node by its name.

        Args:
            name: The name of the child node to retrieve.

        Returns:
            The child Node object, or None if not found.

        Raises:
            ValueError: If the name is empty.
        """
        if not name:
            raise ValueError("Child name cannot be empty.")
        for child in self:
            if child.name == name:
                return child
        return None

    def ensure_child(self, name: str) -> "Node":
        """
        Retrieves a child node with the given name. If no such child exists,
        a new child node is created, added to this node, and returned.

        Args:
            name: The name of the child node to retrieve or create.

        Returns:
            The existing child node with the given name, or the newly created
            child node.

        Raises:
            ValueError: If the provided name is empty.
        """
        if not name:
            raise ValueError("Child node name cannot be empty.")

        child = self.get_child_by_name(name)  # Assuming you've renamed get_name
        if not child:
            child = self.__class__(name, self)
            self.append_child(child)  # Assuming you've renamed append
        return child

    def get_sub(self, names):
        sub = self.get_name(names[0])
        if sub:
            return sub.get_sub(names[1:]) if len(names) > 1 else sub

    # extra

    # def set_data(self, data):
    #     self.data = None
    #     self.clear()
    #     del self.first_child
    #     self.data = data
    #     return self
    def iter_parents(self) -> Iterable["Node"]:
        """
        Iterates over the parent nodes.
        """
        current = self.parent
        while current:
            yield current
            current = current.parent

    def iter_self_and_parents(self) -> Iterable["Node"]:
        """
        Iterates over the node and its parent nodes.
        """
        current = self
        while current:
            yield current
            current = current.parent

    def get_path(self, separator: str = "/") -> str:
        """
        Gets the path from the root to this node.

        Args:
            separator: The separator to use in the path string.

        Returns:
            The path string.
        """
        names: list[str] = []
        current = self
        while current.parent:
            names.append(current.name)
            current = current.parent
        return separator + separator.join(reversed(names))

    def iter_names_to_root(self) -> Iterable[str]:
        """
        Iterates over the names of the nodes from this node up to the root.
        """
        current = self.parent
        while current:
            yield current.name
            current = current.parent

    def iter_relative_names(self, top: "Node") -> Iterable[str]:

        p = self.parent
        n = self.name
        while p:
            yield n
            if p == top:
                return
            n = p.name
            p = p.parent
        assert 0, "Unexpected"

    def enum_descend(self) -> Iterable["Node"]:
        """
        Iterates over all descendant nodes of this node using a depth-first traversal.

        Yields:
            Node: A descendant node.
        """
        child = self.first_child
        while child:
            assert child.parent is self, f"Child '{child.name}' has incorrect parent."
            yield child
            yield from child.enum_descend()
            child = child.next_sibling

    def enum_ascend(self) -> Iterable["Node"]:
        """
        Iterates over all ancestor nodes of this node, starting from the
        immediate parent and going up to the root (exclusive of the current node).

        Yields:
            Node: An ancestor node.
        """
        current = self.parent
        while current:
            yield current
            current = current.parent

    def enum_ascend_with_self(self) -> Iterable["Node"]:
        """
        Iterates over this node and all its ancestor nodes, starting from
        this node and going up to the root.

        Yields:
            Node: This node or one of its ancestor nodes.
        """
        current = self
        while current:
            yield current
            current = current.parent

    def enum_depth_first(self):
        for sub in self:
            yield sub
            yield from sub

    def enum_depth_first(self) -> Iterable["Node"]:
        """
        Iterates over all nodes in the subtree rooted at this node using a
        depth-first traversal.

        Yields:
            Node: A node in the subtree.
        """
        for child in self:
            assert child.parent is self, f"Child '{child.name}' has incorrect parent."
            yield child
            yield from child
