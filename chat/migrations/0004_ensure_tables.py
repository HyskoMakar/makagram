from django.db import migrations

def create_tables_if_missing(apps, schema_editor):
    connection = schema_editor.connection
    tables = connection.introspection.table_names()

    Group = apps.get_model('chat', 'Group')
    GroupMessage = apps.get_model('chat', 'GroupMessage')
    GroupInvite = apps.get_model('chat', 'GroupInvite')

    # Create Group table if missing
    if Group._meta.db_table not in tables:
        schema_editor.create_model(Group)
    
    # Check M2M table for group members
    m2m_table = Group.members.through._meta.db_table
    if m2m_table not in tables:
        schema_editor.create_model(Group.members.through)

    # Check GroupMessage table if missing
    if GroupMessage._meta.db_table not in tables:
        schema_editor.create_model(GroupMessage)

    # Check GroupInvite table if missing
    if GroupInvite._meta.db_table not in tables:
        schema_editor.create_model(GroupInvite)

class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0003_group_color_alter_group_private'),
    ]

    operations = [
        migrations.RunPython(create_tables_if_missing, reverse_code=migrations.RunPython.noop),
    ]
