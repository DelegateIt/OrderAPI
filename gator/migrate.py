""" Migrates items in the db to newer versions """

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
    version = item.get(config.SCHEMA_VERSION, 0)
    while version < len(handlers):
        try:
            handlers[version](item)
            item[config.SCHEMA_VERSION] = version + 1
            item.save()
        except ConditionalCheckFailedException:
            item = table.get(item["uuid"])
        version = item.get(config.SCHEMA_VERSION, 0)

################################
# BEGIN transaction migrations #
################################

def _migrate_transaction_to_1(item):
    if models.TFields.CUSTOMER_PLATFORM_TYPE not in item:
        item[models.TFields.CUSTOMER_PLATFORM_TYPE] = "sms"
_migraters[models.transactions].append(_migrate_transaction_to_1)

##############################
# END transaction migrations #
##############################
