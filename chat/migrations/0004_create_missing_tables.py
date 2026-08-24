from django.db import migrations

def create_missing_tables(apps, schema_editor):
    tables = schema_editor.connection.introspection.table_names()

    models_to_check = [
        apps.get_model('chat', 'Group'),
        apps.get_model('chat', 'GroupMessage'),
        apps.get_model('chat', 'GroupInvite'),
        apps.get_model('chat', 'Block'),
        apps.get_model('chat', 'Friendship'),
        apps.get_model('chat', 'PrivateMessage'),
    ]

    for model in models_to_check:
        if model._meta.db_table not in tables:
            schema_editor.create_model(model)

    Group = apps.get_model('chat', 'Group')
    m2m_table = Group.members.through._meta.db_table
    if m2m_table not in tables:
        schema_editor.create_model(Group.members.through)

class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0003_group_color_alter_group_private'),
    ]

    operations = [
        migrations.RunPython(create_missing_tables, reverse_code=migrations.RunPython.noop),
    ]
