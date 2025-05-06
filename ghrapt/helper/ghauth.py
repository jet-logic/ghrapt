from .smartget import SmartGet


class AuthParams(SmartGet):
    token: str
    owner: str
    repo: str

    def set_auth_params(self, s=None):
        if not s or s.isupper():
            from os import environ

            s = environ.get(s or "AUTH")

        if s:
            token, sep, info = s.rpartition("@")
            owner, sep, repo = info.rpartition("/")
            if token:
                self.token = token
            if owner:
                self.user = self.owner = owner
            if repo:
                self.repo = repo

    def _get_auth_file(self):
        from pathlib import Path

        return Path.home().joinpath(".config", "ghdevapi.auth")

    def _get_token(self):
        from pathlib import Path

        self.set_auth_params()
        owner = getattr(self, "owner", None)
        repo = getattr(self, "repo", None)
        if self.auth_file.exists() and (owner or repo):
            from configparser import ConfigParser

            config = ConfigParser()
            config.read(str(self.auth_file))
            token = (
                config.get(f"{owner}/{repo}", "token", fallback=0)
                or config.get(f"{owner}/", "token", fallback=0)
                or config.get(f"/{repo}", "token", fallback=0)
            )
            # if not token:
            #     for sec in config.sections():
            #         v = config.get(sec, "token", fallback=0)
            #         if v:
            #             token = v
            #             break
            if not token:
                from os import environ

                s = environ.get("GH_TOKEN")
                if s:
                    token = s
            if token:
                return token
        raise AttributeError(f"No token {dict(owner=owner,repo=repo)}")
