from __future__ import annotations


def build_collection_lookup(collections: dict) -> dict:
    """Build parent-resolved path cache from a Zotero collection tree.

    Returns a dict with:
      path_by_key: {collection_key: "Parent/Sub/Name", ...}
      paths_by_item_id: {item_id: [collection_path, ...], ...}
    """
    path_cache: dict[str, str] = {}
    item_paths: dict[str, list[str]] = {}

    def path_for(key: str) -> str:
        if key in path_cache:
            return path_cache[key]
        node = collections.get(key, {})
        parent = node.get("parent") or ""
        name = node.get("name", "")
        parent_path = path_for(parent) if parent else ""
        full_path = f"{parent_path}/{name}" if parent_path else name
        path_cache[key] = full_path
        return full_path

    for key, node in collections.items():
        full_path = path_for(key)
        for item_id in node.get("items", []):
            item_paths.setdefault(item_id, []).append(full_path)

    return {"path_by_key": path_cache, "paths_by_item_id": item_paths}
