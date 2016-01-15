import gator.config as config

from gator.common import GatorException, Errors

########################
# Handler Helper Class #
########################

class MigrationHandlers():
    def __init__(self, cur_version):
        self.handlers = {}
        self.cur_version = cur_version

    def add_handler(self, version, handler_cls):
        if self.handlers.get(version) is not None:
            raise ValueError("Handler for version %s already exists" % version)

        self.handlers[version] = handler_cls

    def migrate_forward_item(self, item):
        # Short circuit if we are at the correct version
        if item["version"] == self.cur_version:
            return

        # Assumes that handlers continuous and up to date
        # i.e. 2 -> 3 -> 4 -> 5
        if self.handlers.get(int(item["version"])) is None:
            raise GatorException(Errors.UNSUPORTED_VERSION)

        for version in range(int(item["version"]), self.cur_version):
            self.handlers[version].forward(item)

        item["version"] = self.cur_version

    def migrate_backward_item(self, item, target_version):
        if item["version"] == target_version:
            return

        if target_version > item["version"]:
            raise ValueError("target_version must be less than item version")
        elif self.handlers.get(target_version) is None:
            raise GatorException(Errors.UNSUPORTED_VERSION)

        for version in range(item["version"] - 1, target_version - 1, -1):
            self.handlers[version].backward(item)

        item["version"] = target_version

####################
# General Handlers #
####################

# NOTE: this is only necessary to migrate the db to use the versions system
class VersionHandler():
    @staticmethod
    def forward(item):
        item["version"] = 1

    @staticmethod
    def backward(item):
        pass

# Deletes platform type attributes from all messages in a transaction
class MigratePlatformType():
    @staticmethod
    def forward(item):
        if item.get("messages") is None:
            return

        for msg in item["messages"]:
            if msg.get("platform_type") is not None:
                del msg["platform_type"]

    # NOTE: data may be lost for the delegator platform type; however, this
    #       isn't an issue now b/c there is only one delegator platform type
    @staticmethod
    def backward(item):
        if item.get("messages") is None:
            return

        for msg in item["messages"]:
            if msg["from_customer"]:
                msg["platform_type"] = item["customer_platform_type"]
            else:
                msg["platform_type"] = "web_client"

# Adds "text" message type to all non-typed messages
class AddMessageType():
    @staticmethod
    def forward(item):
        if item.get("messages") is None:
            return

        for msg in item["messages"]:
            print (msg)
            if msg.get("type") is None:
                msg["type"] = "text"

    @staticmethod
    def backward(item):
        pass
