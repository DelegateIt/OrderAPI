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
        pass

    @staticmethod
    def backward(item):
        pass
