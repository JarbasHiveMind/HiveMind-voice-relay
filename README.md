### HiveMind Server Setups

When building your HiveMind servers there are many ways to go about it, with many optional components

Common setups:

- **OVOS Device**, a full OVOS install without hivemind
- **Hivemind Device**, a OVOS device also running hivemind, eg. a Mark2 with it's own satellites.
- **Hivemind Skills Server**, a minimal HiveMind server that satellites can connect to, supports **text** utterances
  only
- **Hivemind Sound Server**, a HiveMind server that supports **text** utterances and **streaming audio**
- **Hivemind Persona Server**, exposes a `ovos-persona` (eg. an LLM) that satellites can connect to, without
  running `ovos-core`.

The table below illustrates the most common setups for a OVOS based Mind, each column represents a running OVOS/HiveMind
service on your server

|                             | **hivemind-core** | **hivemind-listener** | **ovos-core** | **ovos-audio** | **ovos-listener** | **hivemind-persona** |
|-----------------------------|-------------------|-----------------------|---------------|----------------|-------------------|----------------------|
| **OVOS Device**             | ❌                 | ❌                     | ✔️            | ✔️             | ✔️                | ❌                    | 
| **Hivemind Device**         | ✔️                | ❌                     | ✔️            | ✔️             | ✔️                | ❌                    | 
| **Hivemind Skills Server**  | ✔️                | ❌                     | ✔️            | ❌              | ❌                 | ❌                    | 
| **Hivemind Sound Server**   | ❌                 | ✔️                    | ✔️            | ❌              | ❌                 | ❌                    | 
| **Hivemind Persona Server** | ❌                 | ❌                     | ❌             | ❌              | ❌                 | ✔️                   | 

The table below indicates compatibility for each of the setups described above with the most common voice satellites,
each column corresponds to a different satellite

|                             | **voice satellite** | **voice relay** | **mic satellite** |
|-----------------------------|---------------------|-----------------|-------------------|
| **OVOS Device**             | ❌                   | ❌               | ❌                 |
| **Hivemind Device**         | ✔️                  | ✔️              | ❌                 |
| **Hivemind Skills Server**  | ✔️                  | ❌               | ❌                 |
| **Hivemind Sound Server**   | ✔️                  | ✔️              | ✔️                |
| **Hivemind Persona Server** | ✔️                  | ❌               | ❌                 |

### HiveMind Satellites

The table below illustrates how plugins from the OVOS ecosystem relate to the various satellites

**Emoji Key**

- ✔️: Local (on device)
- 📡: Remote (hivemind-listener)
- ❌: Unsupported

| Supported Plugins                 | **Microphone**   | **VAD**          | **Wake Word**    | **STT**          | **TTS**          | **Media Playback** | **Transformers**   | **PHAL**           |
|-----------------------------------|------------------|------------------|------------------|------------------|------------------|--------------------|--------------------|--------------------|
| **HiveMind Voice Satellite**      | ✔️<br>(Required) | ✔️<br>(Required) | ✔️<br>(Required) | ✔️<br>(Required) | ✔️<br>(Required) | ✔️<br>(Optional)   | ✔️<br>(Optional)   | ✔️<br>(Optional)   |
| **HiveMind Voice Relay**          | ✔️<br>(Required) | ✔️<br>(Required) | ✔️<br>(Required) | 📡<br>(Remote)   | 📡<br>(Remote)   | ✔️<br>(Optional)   | ✔️<br>(Optional)   | ✔️<br>(Optional)   |
| **HiveMind Microphone Satellite** | ✔️<br>(Required) | ✔️<br>(Required) | 📡<br>(Remote)   | 📡<br>(Remote)   | 📡<br>(Remote)   | ❌<br>(Unsupported) | ❌<br>(Unsupported) | ❌<br>(Unsupported) |
