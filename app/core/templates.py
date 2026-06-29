from fastapi.templating import Jinja2Templates


def asset_url(path):
    """Return a browser-safe URL for uploaded/static assets stored in older DB formats."""
    if not path:
        return ""

    value = str(path).strip().replace("\\", "/")
    lower = value.lower()

    if lower.startswith(("http://", "https://", "data:")):
        return value
    if value.startswith("/static/"):
        return value
    if value.startswith("static/"):
        return "/" + value

    marker = "app/static/"
    marker_index = lower.find(marker)
    if marker_index >= 0:
        return "/static/" + value[marker_index + len(marker):].lstrip("/")

    filename = value.rsplit("/", 1)[-1]
    if filename and "." in filename:
        return f"/static/uploads/customers/{filename}"

    return "/" + value.lstrip("/")


templates = Jinja2Templates(directory="app/templates")
templates.env.globals["asset_url"] = asset_url
