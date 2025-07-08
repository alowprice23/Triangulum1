import json
import unittest
import time
from unittest.mock import MagicMock, patch

from triangulum_lx.agents.message import AgentMessage, MessageType
from triangulum_lx.agents.response_handling import (
    ResponseChunker,
    ResponseCompressor,
    ResponseValidator,
    AsyncResponseCoordinator,
    LargeResponseHandler,
    ResponseValidationError
)

class MockMessageBus:
    """Mock MessageBus for testing."""
    
    def __init__(self):
        self.published_messages = []
    
    def publish(self, message):
        self.published_messages.append(message)
        return message.message_id
    
    def clear(self):
        self.published_messages = []


class TestResponseHandling(unittest.TestCase):
    """Test the response handling components."""
    
    def setUp(self):
        self.chunker = ResponseChunker(max_chunk_size=1024)  # Smaller for testing
        self.compressor = ResponseCompressor(compression_threshold=512)
        self.validator = ResponseValidator()
        self.message_bus = MockMessageBus()
        self.handler = LargeResponseHandler(message_bus=self.message_bus)
    
    def test_chunking_and_reassembly(self):
        """Test chunking and reassembling messages."""
        # Create a message with large content
        large_content = {"data": ["item" * 50 for _ in range(50)]}
        original_message = AgentMessage(
            message_id="test_chunking",
            message_type=MessageType.TASK_RESULT,
            content=large_content,
            sender="sender",
            receiver="receiver",
            timestamp=time.time()
        )
        
        # Chunk the message
        chunks = self.chunker.chunk_message(original_message)
        self.assertGreater(len(chunks), 1)
        
        # Reassemble the chunks
        reassembled = self.chunker.reassemble_chunks(chunks)
        
        # Verify the reassembled message
        self.assertEqual(reassembled.message_id, original_message.message_id)
        self.assertEqual(reassembled.message_type, original_message.message_type)
        self.assertEqual(len(reassembled.content["data"]), len(original_message.content["data"]))
    
    def test_compression_and_decompression(self):
        """Test compressing and decompressing messages."""
        # Create a message with compressible content
        compressible_content = {"data": "repeat" * 1000}
        original_message = AgentMessage(
            message_id="test_compression",
            message_type=MessageType.TASK_RESULT,
            content=compressible_content,
            sender="sender",
            receiver="receiver",
            timestamp=time.time()
        )
        
        # Compress the message
        compressed = self.compressor.compress_message(original_message)
        
        # Verify compression happened
        self.assertIn("_compression", compressed.content)
        self.assertTrue(compressed.content["_compression"]["compressed"])
        
        # Decompress the message
        decompressed = self.compressor.decompress_message(compressed)
        
        # Verify the decompressed message
        self.assertEqual(decompressed.message_id, original_message.message_id)
        self.assertEqual(decompressed.content, original_message.content)
    
    def test_validation(self):
        """Test message validation."""
        # Valid message
        valid_message = AgentMessage(
            message_id="test_valid",
            message_type=MessageType.TASK_RESULT,
            content={"result": "valid"},
            sender="sender",
            receiver="receiver",
            timestamp=time.time()
        )
        
        is_valid, error = self.validator.validate_response(valid_message)
        self.assertTrue(is_valid)
        self.assertIsNone(error)
        
        # Invalid message (missing sender)
        invalid_message = AgentMessage(
            message_id="test_invalid",
            message_type=MessageType.TASK_RESULT,
            content={"result": "invalid"},
            sender=None,
            receiver="receiver",
            timestamp=time.time()
        )
        
        is_valid, error = self.validator.validate_response(invalid_message)
        self.assertFalse(is_valid)
        self.assertIsNotNone(error)
    
    def test_async_coordination(self):
        """Test async response coordination."""
        coordinator = AsyncResponseCoordinator(default_timeout=1.0)
        
        # Register a request
        coordinator.register_request("test_request")
        
        # Check it's pending
        self.assertEqual(
            coordinator.pending_responses["test_request"]["status"], 
            "pending"
        )
        
        # Handle a response
        coordinator.handle_response("test_request", {"data": "response"})
        
        # Check it's completed
        self.assertEqual(
            coordinator.pending_responses["test_request"]["status"], 
            "completed"
        )
        
        # Test waiting for response
        success, response, error = coordinator.wait_for_response("test_request")
        self.assertTrue(success)
        self.assertEqual(response, {"data": "response"})
        self.assertIsNone(error)
    
    def test_large_response_handler(self):
        """Test the complete large response handler."""
        # Create a message with large content
        large_content = {"data": ["item" * 100 for _ in range(100)]}
        original_message = AgentMessage(
            message_id="test_large_handler",
            message_type=MessageType.TASK_RESULT,
            content=large_content,
            sender="sender",
            receiver="receiver",
            timestamp=time.time()
        )
        
        # Process outgoing message with chunking
        message_ids = self.handler.process_outgoing_message(
            original_message, 
            large_content_handling="chunked"
        )
        
        # Verify multiple chunks were published
        self.assertGreater(len(message_ids), 1)
        self.assertEqual(len(self.message_bus.published_messages), len(message_ids))
        
        # Process incoming chunks
        reassembled = None
        for chunk in self.message_bus.published_messages:
            result = self.handler.process_incoming_message(chunk)
            if result is not None:
                reassembled = result
                break
        
        # Verify reassembly
        self.assertIsNotNone(reassembled)
        self.assertEqual(reassembled.message_id, original_message.message_id)
        self.assertEqual(reassembled.message_type, original_message.message_type)


if __name__ == "__main__":
    unittest.main()
