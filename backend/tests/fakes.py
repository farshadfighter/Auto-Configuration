"""In-memory fake Driver for tests that exercise the "online" (connect/deploy/verify/backup/
rollback) driver methods without a real or mocked-over-the-wire device. Matches spec section 95's
expectation that drivers ship with a mock/fixture-based test path."""

from app.drivers.base import DeployResult, Driver, VerifyResult


class FakeDriver(Driver):
    manifest = None  # not needed for these tests

    def __init__(self, *, deploy_succeeds: bool = True, verify_matches: bool = True):
        self.deploy_succeeds = deploy_succeeds
        self.verify_matches = verify_matches
        self.connected = False
        self.backup_content = "! fake running-config\nhostname fake-device\n"

    def validate_intent(self, object_type, parameters):
        return []

    def generate_operations(self, object_type, change_type, parameters, current_state):
        return []

    def connect(self, *, host, port, username, password=None, **kwargs):
        self.connected = True

    def disconnect(self):
        self.connected = False

    def get_current_state(self, object_type, parameters):
        return None

    def backup(self):
        return self.backup_content

    def deploy(self, operations):
        if self.deploy_succeeds:
            return DeployResult(success=True, output="applied ok")
        return DeployResult(success=False, output="", error="simulated deploy failure")

    def verify(self, object_type, parameters):
        return VerifyResult(matches_expected=self.verify_matches, actual_state=parameters)

    def rollback(self, backup_content):
        return DeployResult(success=True, output="rolled back")
