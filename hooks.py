# -*- coding: utf-8 -*-


def post_init_hook(env):
    """Assign Odoo system admins to the Construction Administrator group on install."""
    admin_group = env.ref('aos_construction_management.group_construction_admin', raise_if_not_found=False)
    if not admin_group:
        return
    system_group = env.ref('base.group_system', raise_if_not_found=False)
    if not system_group:
        return
    # Odoo 19 no longer exposes the legacy res.users.groups_id field.
    # Use the relation table directly to keep this post-init hook version-safe.
    env.cr.execute(
        """
        INSERT INTO res_groups_users_rel (gid, uid)
        SELECT %s, system_members.uid
          FROM res_groups_users_rel AS system_members
         WHERE system_members.gid = %s
           AND NOT EXISTS (
               SELECT 1
                 FROM res_groups_users_rel AS admin_members
                WHERE admin_members.gid = %s
                  AND admin_members.uid = system_members.uid
           )
        ON CONFLICT DO NOTHING
        """,
        (admin_group.id, system_group.id, admin_group.id),
    )
