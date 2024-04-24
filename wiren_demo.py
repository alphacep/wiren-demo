#!/usr/bin/env python3

import sys
import sounddevice as sd
import asyncio
import aiomqtt
import queue
import json
import re

from vosk import Model, KaldiRecognizer

q = queue.Queue()

def callback(indata, frames, time, status):
    """This is called (from a separate thread) for each audio block."""
    if status:
        print(status, file=sys.stderr)
    q.put(bytes(indata))

model = Model("vosk-model-small-ru-0.22-wiren")
device_info = sd.query_devices(0, "input")
samplerate = int(device_info["default_samplerate"])
rec = KaldiRecognizer(model, samplerate)


async def confirm(client):
    await client.publish("/devices/buzzer/controls/frequency/on", payload=2000)
    await client.publish("/devices/buzzer/controls/enabled/on", payload=1)
    await asyncio.sleep(0.1)
    await client.publish("/devices/buzzer/controls/enabled/on", payload=0)

async def deny(client):
    await client.publish("/devices/buzzer/controls/frequency/on", payload=500)
    await client.publish("/devices/buzzer/controls/enabled/on", payload=1)
    await asyncio.sleep(0.1)
    await client.publish("/devices/buzzer/controls/enabled/on", payload=0)


cmap = {
 "синий": "0;0;255",
 "жёлтый": "255;255;0",
 "зелёный": "0;255;0",
 "белый": "255;255;255",
 "красный": "255;0;0"
}
async def set_rgb(client, color):
    await client.publish("/devices/wb-led_39/controls/RGB Strip/on", payload=1)
    await client.publish("/devices/wb-led_39/controls/RGB Palette/on", payload=cmap[color])

async def process(client, command):
    if command == "":
        return

    if command == "варя" or command == "привет варя":
        await confirm(client)
        return

    if command == "до свидания" or command == "пока-пока" or command == "пока":
        await confirm(client)
        return

    if command == "включи подсветку" or command == "включи свет":
        await client.publish("/devices/wb-led_39/controls/RGB Strip/on", payload=1)
        await confirm(client)
        return

    if command == "выключи подсветку" or command == "выключи свет":
        await client.publish("/devices/wb-led_39/controls/RGB Strip/on", payload=0)
        await confirm(client)
        return

    if command == "включи вентилятор" or command == "включи обдув":
        await client.publish("/devices/wb-mdm3_57/controls/K2/on", payload=1)
        await confirm(client)
        return

    if command == "выключи вентилятор" or command == "выключи обдув":
        await client.publish("/devices/wb-mdm3_57/controls/K2/on", payload=0)
        await confirm(client)
        return

    if command == "включи лампу" or command == "включи лампочку":
        await client.publish("/devices/wb-mdm3_57/controls/K1/on", payload=1)
        await confirm(client)
        return

    if command == "выключи лампу" or command == "выключи лампочку":
        await client.publish("/devices/wb-mdm3_57/controls/K1/on", payload=0)
        await confirm(client)
        return

    if command == "включи лампу и вентилятор":
        await client.publish("/devices/wb-mdm3_57/controls/K1/on", payload=1)
        await client.publish("/devices/wb-mdm3_57/controls/K2/on", payload=1)
        await confirm(client)
        return

    if command == "выключи лампу и вентилятор":
        await client.publish("/devices/wb-mdm3_57/controls/K1/on", payload=0)
        await client.publish("/devices/wb-mdm3_57/controls/K2/on", payload=0)
        await confirm(client)
        return

    mt = re.match(r"включи (синий|жёлтый|зелёный|белый|красный)( свет)?", command)
    if mt != None:
        await set_rgb(client, mt.groups()[0])
        await confirm(client)
        return

    if command != "":
        await deny(client)

async def main():

    async with aiomqtt.Client("localhost") as client:

        with sd.RawInputStream(samplerate=samplerate, blocksize = 8000, device=0,
            dtype="int16", channels=1, callback=callback):

            while True:
                try:
                    data = q.get_nowait()
                    if rec.AcceptWaveform(data):
                        jres = json.loads(rec.Result())
                        print (jres)
                        await process(client, jres['text'])
                except Exception as e:
                    await asyncio.sleep(0.05)

asyncio.run(main())
