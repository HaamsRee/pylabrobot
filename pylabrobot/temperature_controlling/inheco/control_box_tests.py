import unittest
from unittest.mock import AsyncMock, Mock, patch

from pylabrobot.temperature_controlling.inheco.control_box import InhecoTECControlBox


class InhecoTECControlBoxTests(unittest.IsolatedAsyncioTestCase):
  def setUp(self):
    self.control_box = InhecoTECControlBox()
    self.control_box.io = Mock()
    self.control_box.io.read = AsyncMock()
    self.control_box.io.write = AsyncMock()

  async def test_read_until_end_converts_seconds_to_milliseconds(self):
    self.control_box.io.read.return_value = b"0rfv0OK\xa4\x00"

    with patch(
      "pylabrobot.temperature_controlling.inheco.control_box.time.monotonic",
      side_effect=[100.0, 100.0],
    ):
      response = await self.control_box._read_until_end(timeout=3)

    self.assertEqual(response, b"0rfv0OK\xa4")
    self.control_box.io.read.assert_awaited_once_with(8, timeout=3000)

  async def test_read_until_end_assembles_multiple_packets(self):
    self.control_box.io.read.side_effect = [
      b"0rfv0MT#",
      b"C_MB_V2#",
      b".53_06/#",
      b"16\xa4\x00\x00\x00\x00\x00",
    ]

    response = await self.control_box._read_until_end(timeout=3)

    self.assertEqual(response, b"0rfv0MTC_MB_V2.53_06/16\xa4")

  async def test_read_until_end_raises_timeout(self):
    self.control_box.io.read.return_value = b""

    with patch(
      "pylabrobot.temperature_controlling.inheco.control_box.time.monotonic",
      side_effect=[100.0, 100.0, 101.0],
    ):
      with self.assertRaisesRegex(TimeoutError, "Timeout while waiting for response"):
        await self.control_box._read_until_end(timeout=1)

  async def test_read_response_uses_modified_echo_to_find_matching_response(self):
    self.control_box._read_until_end = AsyncMock(
      side_effect=[b"1rat0+250\xa4", b"0rfv0MTC_MB_V2.53_06/16\xa4"]
    )

    response = await self.control_box._read_response("0RFV0", timeout=3)

    self.assertEqual(response, b"0rfv0MTC_MB_V2.53_06/16\xa4")
    self.assertEqual(self.control_box._read_until_end.await_count, 2)

  async def test_send_command_decodes_payload_without_binary_crc(self):
    self.control_box._read_response = AsyncMock(return_value=b"0rfv0MTC_MB_V2.53_06/16\xa4")

    response = await self.control_box.send_command("0RFV0")

    self.assertEqual(response, "MTC_MB_V2.53_06/16")
    packet = self.control_box._generate_packets("0RFV0")[0]
    self.control_box.io.write.assert_awaited_once_with(bytes(packet[1:]), report_id=b"\x00")

  async def test_send_command_raises_for_nonzero_status(self):
    self.control_box._read_response = AsyncMock(return_value=b"2ssr5\xa4")

    with self.assertRaisesRegex(RuntimeError, "Error response from device"):
      await self.control_box.send_command("2SSR300")

  async def test_send_command_retries_reset_status_once(self):
    self.control_box._read_response = AsyncMock(side_effect=[b"2ssr6\x96", b"2ssr0\xa4"])

    response = await self.control_box.send_command("2SSR300")

    self.assertEqual(response, "")
    self.assertEqual(self.control_box._read_response.await_count, 2)
    self.assertEqual(self.control_box.io.write.await_count, 2)

  async def test_send_command_raises_if_reset_status_repeats(self):
    self.control_box._read_response = AsyncMock(side_effect=[b"2ssr6\x96", b"2ssr6\x96"])

    with self.assertRaisesRegex(RuntimeError, "Error response from device"):
      await self.control_box.send_command("2SSR300")

    self.assertEqual(self.control_box._read_response.await_count, 2)
