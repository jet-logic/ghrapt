from .util.tree.local_node import local_data
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

        aux = Aux()
        root = local_data(Path(self.dirs[0])).new_node("ROOT")
        print("token", aux.auth_file)
        aux.set_auth_params(self.auth)
        # self.
        for x in root:
            print(x.name)

        # print("token", aux.__dict__.items())
        # print("token", getattr(aux, "token"))


(__name__ == "__main__") and App().main()
