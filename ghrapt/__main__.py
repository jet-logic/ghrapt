from .util.tree.ignore import FilterMaxSize, collect_ignore
from .util.extra import mode_name
from .util.extra import filesizef
from .util.tree.local_node import LocalAux, LocalNode
from .helper.httphelp import HttpHelp
from .helper.ghauth import AuthParams
from .main import Main, arg, flag


class Aux(AuthParams, HttpHelp):
    pass


class App(Main):
    dirs: list[str] = arg("Directory to upload", nargs="+")
    ##
    follow_links: int = flag("links", "Follow links", choices=["keep", "follow"])
    follow_dir_links: int = flag(
        "dir-links", "Follow dirtory links", choices=["keep", "follow"]
    )
    use_gitignore: int = flag("gitignore", "Use .gitignore")
    max_size: int = flag("max-size", "Include only size below")
    ##
    auth: str = flag("A", "auth", "Authorization")

    def start(self) -> None:
        from pathlib import Path

        gitignore_ancestors = True
        max_size = self.max_size
        import logging

        # logging.basicConfig(**dict(format="%(levelname)s: %(message)s", level="DEBUG"))

        def walk(pn: LocalNode, first=None):
            if pn.is_dir():
                if first:
                    pd = pn.data
                    excludes = includes = None
                    if max_size > 0:
                        excludes = FilterMaxSize(max_size, excludes)
                    if gitignore_ancestors:
                        v = collect_ignore(pd._path)
                        if v:
                            (exc, inc) = v
                            if exc:
                                if excludes:
                                    excludes.append(exc)
                                else:
                                    excludes = exc
                            if inc:
                                if includes:
                                    includes.append(inc)
                                else:
                                    includes = inc
                    if excludes or includes:
                        pd.filter_dir(pn)
                        _ignore = getattr(pd, "_ignore", None)
                        if _ignore:
                            excludes and excludes.append(_ignore[0])
                            _ignore = (
                                excludes or _ignore[0],
                                includes or _ignore[1],
                            )
                        else:
                            _ignore = (excludes, includes)
                        # print(excludes, _ignore)
                        pd._ignore = _ignore
                for cur in pn:
                    walk(cur)
            return pn

        aux = LocalAux()
        aux.symlink_strategy("keep", "keep")
        # no = aux.node_from(Path("/mnt/META/wrx/web/flask-render/home/.local"))
        no = aux.node_from(Path(self.dirs[0]).absolute(), "ROOT")
        # print(no, hex(no.mode), hex(no.type), no.is_dir())
        self.walk(no)
        # root = local_data(Path(self.dirs[0])).new_node("ROOT")
        # print("token", aux.auth_file)
        # aux.set_auth_params(self.auth)
        # # self.
        # for x in root:
        #     print(x.name)

        # # print("token", aux.__dict__.items())
        # # print("token", getattr(aux, "token"))

    def line(self, cur):
        print(
            cur.hash,
            mode_name(cur.mode),
            filesizef(cur.size).rjust(6),
            cur.get_path(),
        )

    def walk(self, cur):
        for s in cur:
            self.line(s)
            (s.is_dir() and self.walk(s))
        cur.parent or self.line(cur)


(__name__ == "__main__") and App().main()
