from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("warehouse", "0068_printer_userappsettings"),
    ]

    operations = [
        migrations.AddField(
            model_name="stockproduct",
            name="no_discount",
            field=models.BooleanField(default=False),
        ),
    ]
