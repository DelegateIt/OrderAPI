""" Migrates items in the db to newer versions """

from boto.dynamodb2.exceptions import ConditionalCheckFailedException
from gator import models

# maps dynamodb tables to list of migration handler functions
# The handler in the n'th index migrates items from version n to n+1
# All handlers should accept one argument of type boto.dynamodb.item.Item, and
# shoud never call `item.save()` as the calling function will handle saving
_migraters = {
    models.transactions: [] # Handlers are added after their definition at the bottom
}

""" Runs the migration on the entire db.

Warning: this will scan all the tables that have a migration handler, so this will result
in a large amount of reads/writes.
"""
def migrate():
    for table, handlers in _migraters.items():
        for item in table.scan():
            _migrate_item(table, item, handlers)


def _migrate_item(table, item, handlers):
    version = int(item.get(models.SCHEMA_VERSION_KEY, 0))
    while version < len(handlers):
        try:
            handlers[version](item)
            item[models.SCHEMA_VERSION_KEY] = version + 1
            item.save()
        except ConditionalCheckFailedException:
            item = table.get_item(item["uuid"])
        version = int(item.get(models.SCHEMA_VERSION_KEY, 0))

################################
# BEGIN transaction migrations #
################################

# Adds a 'customer_platform_type' field to all transaction objects with default value 'sms'
def _migrate_transaction_to_1(item):
    if models.TFields.CUSTOMER_PLATFORM_TYPE not in item:
        item[models.TFields.CUSTOMER_PLATFORM_TYPE] = "sms"
_migraters[models.transactions].append(_migrate_transaction_to_1)

# Removes the 'platform_type' field from all message
# Adds the 'type' field to all messages with default value 'text'
def _migrate_transaction_to_2(item):
    if "messages" not in item:
        return
    for msg in item["messages"]:
        if "platform_type" in msg:
            del msg["platform_type"]
        if "type" not in msg:
            msg["type"] = "text"
_migraters[models.transactions].append(_migrate_transaction_to_2)

##############################
# END transaction migrations #
##############################
