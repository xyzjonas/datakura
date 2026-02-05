from django.conf import settings


def vite_assets(request):
    manifest = settings.VITE_MANIFEST
    assets = {"vite_js": "", "vite_css": ""}

    if "index.html" in manifest:
        entry = manifest["index.html"]
        assets["vite_js"] = entry.get("file", "")
        if "css" in entry:
            assets["vite_css"] = entry["css"][0] if entry["css"] else ""

    return assets
