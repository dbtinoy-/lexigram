from __future__ import annotations


class AdminSettings:
    """Settings helper."""

    _RESOURCE_MAPPINGS = {
        "UserResource": "users",
        "AuditLogResource": "audit_logs",
        "PermissionResource": "permissions",
        "RoleResource": "roles",
        "SettingResource": "settings",
        "GroupResource": "groups",
        "OrganizationResource": "organizations",
        "ApiKeyResource": "api_keys",
        "WebhookResource": "webhooks",
        "NotificationResource": "notifications",
        "ReportResource": "reports",
        "DashboardResource": "dashboards",
        "LogResource": "logs",
        "EventResource": "events",
        "TaskResource": "tasks",
        "JobResource": "jobs",
        "QueueResource": "queues",
        "MetricResource": "metrics",
        "HealthResource": "health",
        "StatusResource": "status",
        "ConfigResource": "config",
        "ProfileResource": "profiles",
        "SessionResource": "sessions",
        "TokenResource": "tokens",
        "AuthResource": "auth",
        "LoginResource": "login",
        "LogoutResource": "logout",
    }

    def build_htmx_path(self, resource_name: str, action: str | None = None) -> str:
        if resource_name in self._RESOURCE_MAPPINGS:
            name = self._RESOURCE_MAPPINGS[resource_name]
        else:
            name = self._pluralize_resource_name(resource_name)

        path = f"/admin/{name}"
        if action:
            path = f"{path}/{action}"
        return path

    def _pluralize_resource_name(self, resource_name: str) -> str:
        if resource_name.endswith("Resource"):
            base_name = resource_name[:-8]
        else:
            base_name = resource_name

        name = base_name.lower()

        irregular_plurals = {
            "child": "children",
            "person": "people",
            "man": "men",
            "woman": "women",
            "tooth": "teeth",
            "foot": "feet",
            "mouse": "mice",
            "goose": "geese",
            "ox": "oxen",
            "leaf": "leaves",
            "knife": "knives",
            "wife": "wives",
            "life": "lives",
            "elf": "elves",
            "loaf": "loaves",
            "potato": "potatoes",
            "tomato": "tomatoes",
            "hero": "heroes",
            "memo": "memos",
            "photo": "photos",
            "piano": "pianos",
            "halo": "halos",
            "studio": "studios",
            "video": "videos",
            "zoo": "zoos",
        }

        if name in irregular_plurals:
            return irregular_plurals[name]

        if name.endswith("ies"):
            return name
        if name.endswith("es"):
            return name
        if name.endswith("s"):
            return name
        if name.endswith("y") and len(name) > 1 and name[-2] not in "aeiou":
            return name[:-1] + "ies"
        if name.endswith(("ch", "sh", "x", "z", "s")):
            return name + "es"
        if name.endswith("f") and len(name) > 1:
            return name[:-1] + "ves"
        if name.endswith("fe") and len(name) > 2:
            return name[:-2] + "ves"
        return name + "s"


def get_admin_settings() -> AdminSettings:
    return AdminSettings()
