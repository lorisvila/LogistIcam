# Generated by Django 4.2.20 on 2025-06-24 09:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0003_alter_transaction_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='client',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
    ]
