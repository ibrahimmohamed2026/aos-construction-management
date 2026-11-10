# -*- coding: utf-8 -*-


def post_init_hook(env):
    """Assign Odoo system admins to the Construction Administrator group on install."""
    admin_group = env.ref('aos_construction_management.group_construction_admin', raise_if_not_found=False)
    if not admin_group:
        return
    system_group = env.ref('base.group_system', raise_if_not_found=False)
    if not system_group:
        return
    admin_users = env['res.users'].search([
        ('groups_id', 'in', [system_group.id]),
        ('groups_id', 'not in', [admin_group.id]),
    ])
    if admin_users:
        env.cr.execute(
            "INSERT INTO res_groups_users_rel (gid, uid) "
            "SELECT %s, uid FROM unnest(%s::int[]) AS uid "
            "ON CONFLICT DO NOTHING",
            (admin_group.id, admin_users.ids),
        )
