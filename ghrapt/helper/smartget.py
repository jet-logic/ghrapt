class SmartGet:
    """Handles dynamic attribute computation and caching using '_get_*' methods.

    This enables lazy evaluation where attributes are:
    1. Computed only when first accessed (via specially named '_get_attr' methods)
    2. Automatically cached for subsequent accesses
    3. Transparent to the caller (used like normal attributes)

    Typical usage:
        class DataLoader(LazyAttributes):
            def _get_users(self):  # Will power the 'users' attribute
                return expensive_database_query()

        loader = DataLoader()
        print(loader.users)  # First call computes and caches
        print(loader.users)  # Subsequent calls use cached value
    """

    def __getattr__(self, name: str):
        """Intercept attribute access for dynamic computation.

        Args:
            name: Requested attribute name

        Returns:
            The computed or cached attribute value

        Raises:
            AttributeError: If no matching _get_* method exists
        """
        # Skip magic/private names and our own _get_* methods
        if not name.startswith("_"):
            # Check for corresponding _get_* method
            getter_name = f"_get_{name}"
            getter = getattr(self, getter_name, None)

            if getter is not None:
                # Prevent infinite recursion during computation:
                # 1. Temporarily set the attribute to None
                setattr(self, name, None)
                # 2. Compute the real value
                value = getter()
                # 3. Permanently cache the result
                setattr(self, name, value)
                return value

        # Fallback to standard attribute lookup if no _get_* method exists
        try:
            return super().__getattr__(name)
        except AttributeError:
            # Provide clear error including available _get_* methods
            raise AttributeError(
                f"'{self.__class__.__name__}' has no attribute '{name}'. "
                f"Available dynamic attributes: {[
                m[5:]
                for m in dir(self)
                if m.startswith("_get_") and not m.startswith("_get__")
            ]}"
            ) from None
