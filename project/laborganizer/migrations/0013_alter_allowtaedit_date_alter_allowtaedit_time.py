# Generated by Django 4.0.1 on 2022-03-04 08:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('laborganizer', '0012_alter_allowtaedit_date_alter_allowtaedit_time'),
    ]

    operations = [
        migrations.AlterField(
            model_name='allowtaedit',
            name='date',
            field=models.DateField(auto_now_add=True, null=True),
        ),
        migrations.AlterField(
            model_name='allowtaedit',
            name='time',
            field=models.TimeField(auto_now_add=True, null=True),
        ),
    ]
