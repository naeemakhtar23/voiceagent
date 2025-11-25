"""
WebSocket bridge between Twilio Media Streams and ElevenLabs WebSocket
This bridges audio between Twilio and ElevenLabs
"""
import asyncio
import websockets
import json
import logging
import base64
from flask import request

logger = logging.getLogger(__name__)

async def bridge_twilio_to_elevenlabs(twilio_ws, elevenlabs_ws_url, context):
    """
    Bridge audio between Twilio Media Stream and ElevenLabs WebSocket
    
    Args:
        twilio_ws: WebSocket connection from Twilio
        elevenlabs_ws_url: ElevenLabs WebSocket URL
        context: Conversation context (questions) to send to ElevenLabs
    """
    try:
        # Connect to ElevenLabs WebSocket
        async with websockets.connect(elevenlabs_ws_url) as elevenlabs_ws:
            logger.info("Connected to ElevenLabs WebSocket")
            
            # Send initial context to ElevenLabs if available
            if context:
                try:
                    # Format context for ElevenLabs
                    initial_message = {
                        'type': 'conversation_init',
                        'context': context
                    }
                    await elevenlabs_ws.send(json.dumps(initial_message))
                    logger.info(f"Sent context to ElevenLabs: {context[:100]}...")
                except Exception as e:
                    logger.warning(f"Could not send context to ElevenLabs: {str(e)}")
            
            # Bridge messages in both directions
            async def forward_to_elevenlabs():
                """Forward Twilio audio to ElevenLabs"""
                try:
                    async for message in twilio_ws:
                        try:
                            data = json.loads(message)
                            event_type = data.get('event')
                            
                            if event_type == 'media':
                                # Extract audio from Twilio Media Stream
                                payload = data.get('media', {}).get('payload')
                                if payload:
                                    # Decode base64 audio and forward to ElevenLabs
                                    audio_data = base64.b64decode(payload)
                                    # Send audio to ElevenLabs (format depends on their API)
                                    await elevenlabs_ws.send(audio_data)
                        except json.JSONDecodeError:
                            # Not JSON, might be binary audio
                            await elevenlabs_ws.send(message)
                        except Exception as e:
                            logger.error(f"Error forwarding to ElevenLabs: {str(e)}")
                            break
                except Exception as e:
                    logger.error(f"Error in forward_to_elevenlabs: {str(e)}")
            
            async def forward_to_twilio():
                """Forward ElevenLabs audio to Twilio"""
                try:
                    async for message in elevenlabs_ws:
                        # Forward audio from ElevenLabs to Twilio
                        # Format depends on Twilio Media Stream format
                        audio_payload = base64.b64encode(message).decode('utf-8')
                        twilio_message = {
                            'event': 'media',
                            'media': {
                                'payload': audio_payload
                            }
                        }
                        await twilio_ws.send(json.dumps(twilio_message))
                except Exception as e:
                    logger.error(f"Error forwarding to Twilio: {str(e)}")
            
            # Run both forwarding tasks concurrently
            await asyncio.gather(
                forward_to_elevenlabs(),
                forward_to_twilio()
            )
            
    except Exception as e:
        logger.error(f"Error in WebSocket bridge: {str(e)}", exc_info=True)
        raise

