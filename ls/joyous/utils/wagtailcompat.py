# ------------------------------------------------------------------------------
# Masks over (some of) the differences between Wagtail 1.x and 2.x
# ------------------------------------------------------------------------------
import sys
from wagtail import VERSION as _wt_version

class _WagtailImporter(object):
    wt_modules = [("wagtailcore",                  "core"),
                  ("wagtailadmin",                 "admin"),
                  ("wagtaildocs",                  "documents"),
                  ("wagtailembeds",                "embeds"),
                  ("wagtailimages",                "images"),
                  ("wagtailsearch",                "search"),
                  ("wagtailsites",                 "sites"),
                  ("wagtailsnippets",              "snippets"),
                  ("wagtailusers",                 "users"),
                  ("wagtailforms",                 "contrib.forms"),
                  ("wagtailredirects",             "contrib.redirects"),
                  ("contrib.wagtailfrontendcache", "contrib.frontend_cache"),
                  ("contrib.wagtailroutablepage",  "contrib.routable_page"),
                  ("contrib.wagtailsearchpromotions",
                                                   "contrib.search_promotions"),
                  ("contrib.wagtailsitemaps",      "contrib.sitemaps"),
                  ("contrib.wagtailstyleguide",    "contrib.styleguide"),
                 ]
    if _wt_version[0] < 2:
        wt_map = {new_name:old_name for old_name, new_name in wt_modules}
    else:
        wt_map = {old_name:new_name for old_name, new_name in wt_modules}

    def find_module(self, fullname, path=None):
        names = fullname.split('.')
        if (len(names) >= 2 and names[0] == "wagtail"):
            if names[1] in self.wt_map or ".".join(names[1:3]) in self.wt_map:
                return self
        return None

    def load_module(self, fullname):
        try:
            # module already loaded
            return sys.modules[fullname]
        except KeyError:
            pass

        wt_fullname = self._get_wt_fullname(fullname)

        try:
            # module already loaded as its new name
            module = sys.modules[fullname] = sys.modules[wt_fullname]
            return module
        except KeyError:
            pass

        __import__(wt_fullname)
        module = sys.modules[fullname] = sys.modules[wt_fullname]
        return module

    def _get_wt_fullname(self, fullname):
        names = fullname.split('.')
        wt_name = None
        if len(names) > 2:
            wt_name = self.wt_map.get(".".join(names[1:3]))
            if wt_name is not None:
                names[1:3] = wt_name.split(".")
        if wt_name is None:
            wt_name = self.wt_map.get(names[1])
            if wt_name is not None:
                names[1:2] = wt_name.split(".")
        return ".".join(names)

if not any(type(m) is _WagtailImporter for m in sys.meta_path):
    sys.meta_path.insert(0, _WagtailImporter())
