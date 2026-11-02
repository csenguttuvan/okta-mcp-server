import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from difflib import get_close_matches
from typing import Optional

from loguru import logger
from mcp.server.fastmcp import Context

from okta_mcp_server.context import get_caller_email
from okta_mcp_server.mcp_instance import mcp
from okta_mcp_server.oauth_jwt_client import get_client

# ---------------------------
# Helpers
# ---------------------------


def _normalize_group(g: dict) -> dict:
    """Return a compact, clean group representation — no _links, no logo bloat."""
    p = g.get("profile") or {}
    return {
        "id": g.get("id"),
        "name": (p.get("name") or "").strip(),  # strip leading \n
        "description": (p.get("description") or "").strip(),
        "type": g.get("type"),
    }


def _normalize_user_compact(u: dict) -> dict:
    p = u.get("profile") or {}
    return {
        "id": u.get("id"),
        "email": p.get("email"),
        "first_name": p.get("firstName"),
        "last_name": p.get("lastName"),
        "status": u.get("status"),
    }


def _format_groups(groups: list) -> str:
    if not groups:
        return "No groups found."
    lines = [f"Found {len(groups)} group(s):\n"]
    for g in groups:
        n = _normalize_group(g) if "_links" in g else g
        desc = f"\n  Description: {n['description']}" if n.get("description") else ""
        lines.append(f"• {n['name']} (ID: {n['id']}, Type: {n.get('type', 'N/A')}){desc}")
    return "\n".join(lines)


# ---------------------------
# Tools (read-only — okta.groups.read)
# ---------------------------


@mcp.tool()
def list_groups(limit: int = 100, query: Optional[str] = None, ctx: Context | None = None) -> str:
    """List Okta groups. Use query for name prefix search."""
    caller = get_caller_email()

    if query in ("null", "", None):
        query = None

    try:
        limit_int = max(1, min(int(limit), 200))
    except (TypeError, ValueError):
        limit_int = 100

    logger.info(f"[caller={caller}] listing groups query={query!r}, limit={limit_int}")

    try:
        client = get_client()
        params = {"limit": limit_int}
        if query:
            params["q"] = query

        groups = client.get("/api/v1/groups", params=params)
        logger.info(f"[caller={caller}] Found {len(groups)} groups")
        return _format_groups(groups)

    except PermissionError as e:
        return f"❌ Permission denied: {e!s}"
    except Exception as e:
        return f"❌ Error listing groups: {e!s}"


@mcp.tool()
def search_groups_fuzzy(search_term: str, limit: int = 200, ctx: Context | None = None) -> dict:
    """Fuzzy search Okta groups by name (handles typos, partial names, case differences).

    Examples:
    - "outreach users"  → matches "Outreach - Users"
    - "disciplew dev"   → matches "Disciples-dev"
    - "sso admin"       → matches "Outreach - SSO - Admin"
    """
    caller = get_caller_email()

    if search_term in ("null", None):
        search_term = ""

    logger.info(f"[caller={caller}] Fuzzy searching groups: {search_term!r}")

    client = get_client()
    en_dash = "\u2013"  # some group names use an en dash instead of a hyphen

    # Strategy 1: Fast q= search using first meaningful word
    if search_term:
        try:
            # Use the longest word before any dash/hyphen as the q= seed
            first_word = search_term.replace("-", " ").replace(en_dash, " ").strip().split()[0]
            if len(first_word) >= 3:
                quick = client.get("/api/v1/groups", params={"q": first_word, "limit": 50})
                if quick:
                    # Client-side filter: normalize both sides for comparison
                    term_norm = search_term.lower().replace("-", " ").replace("_", " ").replace(en_dash, " ")
                    # Remove common filler words for matching
                    term_parts = [p for p in term_norm.split() if len(p) > 2]

                    filtered = []
                    for g in quick:
                        name = (g.get("profile") or {}).get("name", "").strip()
                        name_norm = name.lower().replace("-", " ").replace("_", " ")
                        # Match if all meaningful parts of search_term appear in name
                        if all(part in name_norm for part in term_parts):
                            filtered.append(_normalize_group(g))

                    if filtered:
                        logger.info(f"[caller={caller}] q= search found {len(filtered)} matches")
                        return {
                            "groups": filtered,
                            "count": len(filtered),
                            "search_term": search_term,
                            "matched_names": [g["name"] for g in filtered],
                            "search_type": "q_filtered",
                        }

                    # If all-parts filter too strict, return all q= results
                    normalized_quick = [_normalize_group(g) for g in quick]
                    logger.info(f"[caller={caller}] q= prefix returned {len(normalized_quick)}")
                    return {
                        "groups": normalized_quick,
                        "count": len(normalized_quick),
                        "search_term": search_term,
                        "matched_names": [g["name"] for g in normalized_quick],
                        "search_type": "q_prefix",
                    }
        except Exception as e:
            logger.warning(f"[caller={caller}] q= search failed, falling back: {e}")

    # Strategy 2: Full fuzzy scan
    try:
        all_groups = client.get("/api/v1/groups", params={"limit": limit})
    except Exception as e:
        return {"groups": [], "count": 0, "error": str(e)}

    if not search_term:
        normalized = [_normalize_group(g) for g in all_groups]
        return {
            "groups": normalized,
            "count": len(normalized),
            "search_term": "",
            "matched_names": [g["name"] for g in normalized],
            "search_type": "all",
        }

    # Normalize names for comparison (strip \n, lower, dashes→spaces)
    names_raw = [(g, (g.get("profile") or {}).get("name", "").strip()) for g in all_groups]
    names_norm = [(g, raw, raw.lower().replace("-", " ").replace("_", " ")) for g, raw in names_raw]

    term_norm = search_term.lower().replace("-", " ").replace("_", " ")
    term_parts = [p for p in term_norm.split() if len(p) > 2]

    matched = []
    for g, raw, norm in names_norm:
        # Substring check
        if term_norm in norm or any(part in norm for part in term_parts):
            matched.append(_normalize_group(g))
            continue
        # Fuzzy check
        close = get_close_matches(term_norm, [norm], n=1, cutoff=0.35)
        if close:
            matched.append(_normalize_group(g))

    matched = matched[:20]
    logger.info(f"[caller={caller}] Fuzzy scan found {len(matched)} matches")

    return {
        "groups": matched,
        "count": len(matched),
        "search_term": search_term,
        "matched_names": [g["name"] for g in matched],
        "search_type": "fuzzy",
    }


@mcp.tool()
def get_group(group_id: str, ctx: Context | None = None) -> dict:
    """Get details for a specific group by ID."""
    caller = get_caller_email()
    logger.info(f"[caller={caller}] Getting group: {group_id}")

    try:
        client = get_client()
        group = client.get(f"/api/v1/groups/{group_id}")
        return _normalize_group(group)
    except PermissionError:
        raise
    except Exception as e:
        logger.error(f"[caller={caller}] Error getting group: {e}")
        raise


@mcp.tool()
def list_group_users(group_id: str, limit: int = 100, ctx: Context | None = None) -> dict:
    """List members of a group."""
    caller = get_caller_email()
    logger.info(f"[caller={caller}] Listing users in group: {group_id}")

    try:
        client = get_client()
        users = client.get(f"/api/v1/groups/{group_id}/users", params={"limit": limit})
        normalized = [_normalize_user_compact(u) for u in users]
        logger.info(f"[caller={caller}] Found {len(normalized)} users in group")
        return {"users": normalized, "count": len(normalized), "group_id": group_id}
    except PermissionError:
        raise
    except Exception as e:
        logger.error(f"[caller={caller}] Error listing group users: {e}")
        raise


@mcp.tool()
def bulk_get_groups(target_type: str, target_id: str, limit: int = 200, ctx: Context | None = None) -> dict:
    """Get all groups for a user or an application in a single bulk call.

    Accepts an Okta ID, email, display name, or app label — resolves automatically.

    target_type: 'user' or 'app'
    target_id:
      - Okta ID       → '00u1abc...', '0oa4xyz...'
      - Email         → 'jane.doe@company.com'
      - Display name  → 'Jane Doe'
      - App label     → 'Salesforce', 'GitHub'

    Examples:
        - target_type='user', target_id='Jane Doe'        → all groups Jane belongs to
        - target_type='user', target_id='jane@company.com'→ all groups jane belongs to
        - target_type='app',  target_id='Salesforce'      → all groups assigned to Salesforce
        - target_type='app',  target_id='0oa4gh5ij6kl'    → all groups assigned to that app ID
    """
    caller = get_caller_email()
    target_type = (target_type or "").strip().lower()

    if target_type not in ("user", "app"):
        return {"error": f"Invalid target_type '{target_type}'. Must be 'user' or 'app'."}

    if not target_id or not target_id.strip():
        return {"error": "target_id cannot be empty."}

    client = get_client()

    # ---------------------------
    # Step 1: Resolve to Okta ID
    # ---------------------------
    resolved_id = target_id.strip()
    resolved_label = target_id

    OKTA_ID_PATTERN = re.compile(r"^[A-Za-z0-9]{20}$")

    if not OKTA_ID_PATTERN.match(resolved_id):
        if target_type == "user":
            logger.info(f"[caller={caller}] Resolving user '{target_id}' via Okta search")
            try:
                results = client.get("/api/v1/users", params={"q": resolved_id, "limit": 5})
            except Exception as e:
                return {"error": f"Failed to search for user '{target_id}': {e!s}"}

            if not results:
                return {"error": f"No user found matching '{target_id}'"}

            if len(results) > 1:
                return {
                    "error": (
                        f"Ambiguous name '{target_id}' matched {len(results)} users. "
                        f"Please be more specific or use an email address."
                    ),
                    "matches": [
                        {
                            "id": u.get("id"),
                            "email": (u.get("profile") or {}).get("email"),
                            "name": (
                                f"{(u.get('profile') or {}).get('firstName', '')} "
                                f"{(u.get('profile') or {}).get('lastName', '')}".strip()
                            ),
                        }
                        for u in results
                    ],
                }

            resolved_id = results[0].get("id")
            resolved_label = (results[0].get("profile") or {}).get("email", target_id)

        elif target_type == "app":
            logger.info(f"[caller={caller}] Resolving app '{target_id}' via Okta search")
            try:
                results = client.get("/api/v1/apps", params={"q": resolved_id, "limit": 5})
            except Exception as e:
                return {"error": f"Failed to search for app '{target_id}': {e!s}"}

            if not results:
                return {"error": f"No app found matching '{target_id}'"}

            if len(results) > 1:
                return {
                    "error": (
                        f"Ambiguous app name '{target_id}' matched {len(results)} apps. "
                        f"Please be more specific or use the app ID."
                    ),
                    "matches": [
                        {"id": a.get("id"), "label": a.get("label"), "status": a.get("status")} for a in results
                    ],
                }

            resolved_id = results[0].get("id")
            resolved_label = results[0].get("label", target_id)

    logger.info(
        f"[caller={caller}] Bulk fetching groups for {target_type}={resolved_id} (resolved from '{target_id}')"
    )

    # ---------------------------
    # Step 2: Fetch groups
    # ---------------------------
    try:
        if target_type == "user":
            endpoint = f"/api/v1/users/{resolved_id}/groups"
        else:
            endpoint = f"/api/v1/apps/{resolved_id}/groups"

        raw_groups = client.get(endpoint, params={"limit": limit})

    except PermissionError:
        raise
    except Exception as e:
        logger.error(f"[caller={caller}] Error fetching groups: {e}")
        return {"error": f"Failed to fetch groups: {e!s}", "target_id": resolved_id}

    # ---------------------------
    # Step 3: Enrich stubs in parallel
    # (App group assignments may only carry an ID with no profile)
    # ---------------------------
    group_ids_needing_enrichment = [
        g.get("id") for g in raw_groups if g.get("id") and not (g.get("profile") or {}).get("name")
    ]

    enriched = {}
    if group_ids_needing_enrichment:
        logger.info(f"[caller={caller}] Enriching {len(group_ids_needing_enrichment)} group stubs in parallel")

        def fetch_group(gid):
            return gid, client.get(f"/api/v1/groups/{gid}")

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(fetch_group, gid): gid for gid in group_ids_needing_enrichment}
            for future in as_completed(futures):
                try:
                    gid, g = future.result()
                    enriched[gid] = g
                except Exception as e:
                    gid = futures[future]
                    logger.warning(f"[caller={caller}] Failed to enrich group {gid}: {e}")

    # ---------------------------
    # Step 4: Normalize and return
    # ---------------------------
    groups = []
    for g in raw_groups:
        gid = g.get("id")
        full = enriched.get(gid, g)
        groups.append(_normalize_group(full))

    logger.info(f"[caller={caller}] Found {len(groups)} groups for {target_type} '{resolved_label}' ({resolved_id})")

    return {
        "groups": groups,
        "count": len(groups),
        "target_type": target_type,
        "target_id": resolved_id,
        "resolved_from": target_id if target_id != resolved_id else None,
        "label": resolved_label,
    }
