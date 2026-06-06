from django.contrib import admin
from tick_consumer.models import Broker, Script, Tick


admin.site.register(Broker)
admin.site.register(Script)
admin.site.register(Tick)