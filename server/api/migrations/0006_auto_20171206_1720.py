# -*- coding: utf-8 -*-
# Generated by Django 1.11.5 on 2017-12-06 17:20
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0005_auto_20171206_1545'),
    ]

    operations = [
        migrations.AlterField(
            model_name='attend',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.GoogleUser'),
        ),
    ]
