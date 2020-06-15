# Generated by Django 3.0.6 on 2020-06-15 02:14

from django.db import migrations, models
import django.db.models.deletion
import modelcluster.fields
import wagtail.core.fields


class Migration(migrations.Migration):

    dependencies = [
        ('wagtailcore', '0045_assign_unlock_grouppagepermission'),
        ('joyous', '0015_auto_20190409_0645'),
    ]

    operations = [
        migrations.CreateModel(
            name='ClosedForHolidaysPage',
            fields=[
                ('page_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='wagtailcore.Page')),
                ('all_holidays', models.BooleanField(default=True)),
                ('cancellation_title', models.CharField(blank=True, help_text='Show in place of cancelled event (Leave empty to show nothing)', max_length=255, verbose_name='title')),
                ('cancellation_details', wagtail.core.fields.RichTextField(blank=True, help_text='Why was the event cancelled?', verbose_name='details')),
                ('overrides', models.ForeignKey(help_text='The recurring event that we are updating.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='joyous.RecurringEventPage', verbose_name='overrides')),
            ],
            options={
                'verbose_name': 'closed for holidays',
                'verbose_name_plural': 'closed for holidays',
                'default_manager_name': 'objects',
            },
            bases=('wagtailcore.page', models.Model),
        ),
        migrations.CreateModel(
            name='ClosedFor',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='name')),
                ('page', modelcluster.fields.ParentalKey(on_delete=django.db.models.deletion.CASCADE, related_name='closed_for', to='joyous.ClosedForHolidaysPage')),
            ],
            options={
                'unique_together': {('page', 'name')},
            },
        ),
    ]
