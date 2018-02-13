# ------------------------------------------------------------------------------
# Masks over (some of) the differences between Wagtail 1.x and 2.x
# ------------------------------------------------------------------------------
import sys
from wagtail import VERSION as _wt_version

class _WagtailImporter(object):
    wt_modules = [("wagtailadmin",     "admin"),
                  ("wagtailcore",      "core"),
                  ("wagtaildocs",      "documents"),
                  ("wagtailembeds",    "embeds"),
                  ("wagtailforms",     "forms"),
                  ("wagtailimages",    "images"),
                  ("wagtailredirects", "redirects"),
                  ("wagtailsearch",    "search"),
                  ("wagtailsites",     "sites"),
                  ("wagtailsnippets",  "snippets"),
                  ("wagtailusers",     "users")]
    if _wt_version[0] < 2:
        wt_map = {new_name:old_name for old_name, new_name in wt_modules}
    else:
        wt_map = {old_name:new_name for old_name, new_name in wt_modules}

    def find_module(self, fullname, path=None):
        names = fullname.split('.')
        if (len(names) >= 2 and
            names[0] == "wagtail" and
            names[1] in self.wt_map):
            return self
        return None

    def load_module(self, fullname):
        try:
            # module already loaded
            return sys.modules[fullname]
        except KeyError:
            pass

        names = fullname.split('.')
        names[1] = self.wt_map[names[1]]
        wt_fullname = ".".join(names)

        try:
            # module already loaded as its new name
            module = sys.modules[fullname] = sys.modules[wt_fullname]
            return module
        except KeyError:
            pass

        __import__(wt_fullname)
        module = sys.modules[fullname] = sys.modules[wt_fullname]
        return module

if not any(type(m) is _WagtailImporter for m in sys.meta_path):
    sys.meta_path.insert(0, _WagtailImporter())
