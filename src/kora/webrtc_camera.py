import asyncio
import json
import os
import sys
import threading
from fractions import Fraction
from pathlib import Path

# The `av` wheel bundles its own ALSA, which looks for alsa.conf in a build-time
# path that doesn't exist here. Point it at the system config before any ALSA use.
os.environ.setdefault("ALSA_CONFIG_PATH", "/usr/share/alsa/alsa.conf")

import av
import websockets
from aiortc import RTCConfiguration, RTCIceServer, RTCPeerConnection, RTCSessionDescription
from aiortc.mediastreams import MediaStreamTrack, VideoStreamTrack
from av import VideoFrame
from libcamera import Transform
from picamera2 import Picamera2

SIGNALING_URL = "ws://151.145.95.142:8080"
MY_ID = "pi-1"
SECRET = Path.home().joinpath(".kora_secret").read_text().strip()

MIC_DEVICE = "plughw:0,0"
MIC_RATE = 48000


def rtc_config(ice_servers):
    """Build an aiortc config from the server's iceServers list (STUN + TURN)."""
    servers = []
    for entry in ice_servers or []:
        urls = entry["urls"] if isinstance(entry["urls"], list) else [entry["urls"]]
        urls = [u for u in urls if "transport=tcp" not in u]  # UDP only on the Pi side
        if urls:
            servers.append(RTCIceServer(urls=urls, username=entry.get("username"),
                                        credential=entry.get("credential")))
    return RTCConfiguration(iceServers=servers)


def open_camera():
    picam2 = Picamera2()
    config = picam2.create_video_configuration(
        main={"size": (1536, 864), "format": "RGB888"},
        transform=Transform(hflip=True, vflip=True),
        controls={"FrameRate": 30},
    )
    picam2.configure(config)
    picam2.start()
    return picam2


class CameraVideoTrack(VideoStreamTrack):
    def __init__(self, picam2):
        super().__init__()
        self.picam2 = picam2

    async def recv(self):
        pts, time_base = await self.next_timestamp()
        array = await asyncio.to_thread(self.picam2.capture_array)
        frame = VideoFrame.from_ndarray(array, format="bgr24")
        frame.pts = pts
        frame.time_base = time_base
        return frame


class MicAudioTrack(MediaStreamTrack):
    """Live microphone audio from ALSA, as a WebRTC audio track (mono, 48 kHz).

    The sound card produces samples at its own steady pace, so unlike the video
    track we don't need to pace anything: a background thread blocks on the
    card, and recv() just hands out whatever the thread has collected.
    """

    kind = "audio"

    def __init__(self, device=MIC_DEVICE):
        super().__init__()
        self._container = av.open(
            device,
            format="alsa",
            options={"sample_rate": str(MIC_RATE), "channels": "1"},
        )
        self._loop = asyncio.get_running_loop()
        self._queue = asyncio.Queue(maxsize=100)
        self._stop_event = threading.Event()
        self._next_pts = 0
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()

    def _read_loop(self):
        # Runs in its own thread: decoding blocks until the card has data.
        try:
            for frame in self._container.decode(audio=0):
                if self._stop_event.is_set():
                    break
                self._loop.call_soon_threadsafe(self._push, frame)
        except Exception as exc:
            print("mic read loop stopped:", exc, flush=True)
        finally:
            # Close the device from the same thread that was reading from it.
            self._container.close()

    def _push(self, frame):
        if self._queue.full():
            self._queue.get_nowait()  # fall behind -> drop the oldest, stay live
        self._queue.put_nowait(frame)

    async def recv(self):
        raw = await self._queue.get()
        # ALSA hands us a layout literally named "1 channels"; aiortc's Opus
        # encoder only accepts "mono" or "stereo", so rebuild the frame.
        frame = av.AudioFrame.from_ndarray(raw.to_ndarray(), format="s16", layout="mono")
        frame.sample_rate = MIC_RATE
        frame.pts = self._next_pts
        frame.time_base = Fraction(1, MIC_RATE)
        self._next_pts += frame.samples
        return frame

    def stop(self):
        super().stop()
        self._stop_event.set()
        # The thread notices within a few ms; wait so the next connection can
        # reopen the (exclusive) sound card without a "device busy" error.
        self._thread.join(timeout=1)


async def main():
    sys.stdout.reconfigure(line_buffering=True)  # so systemd/journalctl shows logs live
    picam2 = open_camera()
    current_pc = None
    current_mic = None

    async def close_current():
        nonlocal current_pc, current_mic
        if current_mic is not None:
            current_mic.stop()
            current_mic = None
        if current_pc is not None:
            await current_pc.close()
            current_pc = None

    try:
        async with websockets.connect(SIGNALING_URL) as ws:
            await ws.send(json.dumps({"type": "register", "id": MY_ID, "secret": SECRET}))
            print(f"Registered as {MY_ID}, waiting for offers...")

            async for message in ws:
                msg = json.loads(message)
                if msg.get("type") != "relay":
                    continue

                payload = msg["payload"]
                if payload.get("type") != "offer":
                    continue

                print("Got an offer, creating answer...")
                await close_current()

                pc = RTCPeerConnection(rtc_config(msg.get("iceServers")))
                current_pc = pc
                pc.addTrack(CameraVideoTrack(picam2))

                mic = None
                try:
                    mic = MicAudioTrack()
                    current_mic = mic
                    pc.addTrack(mic)
                except Exception as exc:
                    print("mic unavailable, video only:", exc)

                @pc.on("connectionstatechange")
                async def on_state_change(pc=pc, mic=mic):
                    print("connection state:", pc.connectionState)
                    # Viewer left: free the sound card instead of streaming to nobody.
                    if mic is not None and pc.connectionState in ("failed", "closed"):
                        mic.stop()

                offer = RTCSessionDescription(sdp=payload["sdp"], type="offer")
                await pc.setRemoteDescription(offer)
                answer = await pc.createAnswer()
                await pc.setLocalDescription(answer)

                await ws.send(json.dumps({
                    "type": "relay",
                    "to": msg["from"],
                    "payload": {"type": "answer", "sdp": pc.localDescription.sdp},
                }))
                print("Sent answer")
    finally:
        await close_current()
        picam2.stop()
        picam2.close()


if __name__ == "__main__":
    asyncio.run(main())
