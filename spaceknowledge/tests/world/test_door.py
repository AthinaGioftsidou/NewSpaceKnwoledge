"""Unit tests for world/door.py."""

import unittest

from spaceknowledge.world.door import Door, UnlockedState


class TestDoor(unittest.TestCase):

    def setUp(self):
        self.gate = Door("mars_gate", "launch gate", "mission:ship_upgrade")

    def test_a_new_door_is_locked(self):
        self.assertEqual("locked", self.gate.state_name())
        self.assertFalse(self.gate.is_passable())

    def test_the_wrong_key_changes_nothing(self):
        self.assertEqual("That key does not fit.", self.gate.unlock("brass-key"))
        self.assertEqual("locked", self.gate.state_name())

    def test_the_right_key_unlocks_and_locks(self):
        self.assertEqual("The launch gate unlocks.", self.gate.unlock("mission:ship_upgrade"))
        self.assertTrue(self.gate.is_passable())
        self.assertEqual("The launch gate locks.", self.gate.lock("mission:ship_upgrade"))
        self.assertFalse(self.gate.is_passable())

    def test_a_move_the_state_does_not_allow_is_refused(self):
        self.gate.unlock("mission:ship_upgrade")
        # Already unlocked: UnlockedState does not define unlock, so the default refuses.
        self.assertEqual("The launch gate is unlocked.", self.gate.unlock("mission:ship_upgrade"))
        self.assertEqual("unlocked", self.gate.state_name())

    #Useful for future implementation
    def test_a_broken_door_can_never_be_opened(self):
        self.gate.force()
        self.assertEqual("broken", self.gate.state_name())
        message = self.gate.unlock("mission:ship_upgrade")   # even the right key
        self.assertEqual("The launch gate is ruined. Nothing will move it now.", message)
        self.assertFalse(self.gate.is_passable())

    def test_a_door_can_start_in_another_state(self):
        open_gate = Door("gate", "gate", "key", UnlockedState())
        self.assertTrue(open_gate.is_passable())


if __name__ == "__main__":
    unittest.main()