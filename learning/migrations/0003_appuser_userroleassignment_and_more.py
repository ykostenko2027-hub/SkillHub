import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0002_course_cover_image_path'),
    ]

    operations = [
        migrations.CreateModel(
            name='AppUser',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('email', models.EmailField(max_length=320, unique=True)),
                ('first_name', models.CharField(max_length=100)),
                ('last_name', models.CharField(max_length=100)),
                ('display_name', models.CharField(blank=True, max_length=80, null=True)),
                ('password_hash', models.CharField(max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'Users',
            },
        ),
        migrations.CreateModel(
            name='UserRoleAssignment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('Attendee', 'Attendee'), ('Organizer', 'Organizer'), ('Admin', 'Admin')], max_length=20)),
            ],
            options={
                'db_table': 'UserRoles',
            },
        ),
        migrations.AddIndex(
            model_name='course',
            index=models.Index(fields=['created_at', 'id'], name='ix_course_created_at_id'),
        ),
        migrations.AddField(
            model_name='userroleassignment',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='roles', to='learning.appuser'),
        ),
        migrations.AddConstraint(
            model_name='userroleassignment',
            constraint=models.UniqueConstraint(fields=('user', 'role'), name='pk_user_roles'),
        ),
    ]
