import unittest
from unittest.mock import AsyncMock, Mock

from pylabrobot.heating_shaking.inheco.thermoshake_backend import InhecoThermoshakeBackend


class InhecoThermoshakeBackendTests(unittest.IsolatedAsyncioTestCase):
  def setUp(self):
    self.control_box = Mock()
    self.control_box.send_command = AsyncMock()
    self.backend = InhecoThermoshakeBackend(control_box=self.control_box, index=2)

  async def test_set_shaker_speed_uses_device_index(self):
    await self.backend.set_shaker_speed(500)

    self.control_box.send_command.assert_awaited_once_with("2SSR500")

  async def test_set_shaker_shape_uses_device_index(self):
    await self.backend.set_shaker_shape(3)

    self.control_box.send_command.assert_awaited_once_with("2SSS3")
