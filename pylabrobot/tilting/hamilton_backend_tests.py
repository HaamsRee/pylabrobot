import unittest
from unittest.mock import AsyncMock

from pylabrobot.tilting.hamilton_backend import HAS_SERIAL, HamiltonTiltModuleBackend


@unittest.skipUnless(HAS_SERIAL, "pyserial is not installed")
class HamiltonTiltModuleBackendTests(unittest.IsolatedAsyncioTestCase):
  def setUp(self):
    self.backend = HamiltonTiltModuleBackend(com_port="COM1")
    self.backend.io.write = AsyncMock()  # type: ignore[method-assign]
    self.backend.io.read = AsyncMock()  # type: ignore[method-assign]

  async def test_accepts_t1_module_name(self):
    self.backend.io.read.return_value = b"T1REer00\r\n"  # type: ignore[union-attr]

    response = await self.backend.tilt_request_error()

    self.assertEqual(response, "T1REer00\r\n")
    self.backend.io.write.assert_awaited_once_with(b"99RE\r\n")  # type: ignore[union-attr]

  async def test_accepts_numeric_module_name(self):
    self.backend.io.read.return_value = b"00REer00\r\n"  # type: ignore[union-attr]

    response = await self.backend.tilt_request_error()

    self.assertEqual(response, "00REer00\r\n")

  async def test_waits_for_matching_command_from_numeric_module(self):
    self.backend.io.read.side_effect = [  # type: ignore[union-attr]
      b"00RXer00 1\r\n",
      b"00REer00\r\n",
    ]

    response = await self.backend.tilt_request_error()

    self.assertEqual(response, "00REer00\r\n")
    self.assertEqual(self.backend.io.read.await_count, 2)  # type: ignore[union-attr]

  async def test_parses_offset_from_numeric_module(self):
    self.backend.io.read.return_value = b"00ROer00 -00026\r\n"  # type: ignore[union-attr]

    offset = await self.backend.tilt_request_offset_between_light_barrier_and_init_position()

    self.assertEqual(offset, -26)


if __name__ == "__main__":
  unittest.main()
