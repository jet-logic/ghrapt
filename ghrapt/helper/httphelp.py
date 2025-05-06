class HttpHelp:
    # def post_gql(self, json):
    #     d, h = None, {}
    #     x = getattr(self, "token", None)
    #     if x:
    #         h["authorization"] = "bearer " + x
    #     x = getattr(self, "user", None)
    #     if x:
    #         h["user-agent"] = x
    #     with self.http.post(
    #         "https://api.github.com/graphql", json=json, headers=h
    #     ) as r:
    #         s = r.status_code
    #         d = r.json()
    #         return d

    def post_gql(self, json, **rkw):
        rkw = self.req_params(**rkw)
        with self.http.post("https://api.github.com/graphql", json=json, **rkw) as r:
            s = r.status_code
            d = r.json()
            return d

    # def req_params(self, token=None, owner=None, **rkw):
    #     headers = rkw.setdefault("headers", {})
    #     x = token or getattr(self, "token", None)
    #     if x:
    #         headers["Authorization"] = "bearer " + x
    #     headers["User-Agent"] = owner or getattr(self, "owner", "cody")
    #     return rkw

    def req_params(self, token=None, owner=None, **rkw):
        headers = rkw.setdefault("headers", {})
        headers["User-Agent"] = owner or getattr(self, "owner", "cody")
        x = token or getattr(self, "token", None)
        if x:
            headers["Authorization"] = "bearer " + x
        return rkw

    def download_request(self, cur, **kwargs):
        rkw = self.req_params()
        rkw["headers"]["accept"] = "application/vnd.github.v3.raw"
        rkw["url"] = "https://api.github.com/repos/%s/%s/git/blobs/%s" % (
            self.owner,
            self.repo,
            cur.hash,
        )
        rkw["method"] = "get"
        return rkw

    def _get_http(self):
        from requests import session

        return session()
