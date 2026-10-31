# SMSTunnel for Home Assistant

Send SMS from Home Assistant through **your own Android phone**, using **your own SIM card**.

<a href="https://play.google.com/store/apps/details?id=io.smstunnel.app"><img src="https://smstunnel.io/google-play-badge.png" alt="Get it on Google Play" height="56"></a>

No per-message fees, no third-party SMS gateway seeing your messages — the phone you already own does the sending. And because SMS doesn't need the recipient to have internet, alerts still arrive when everything else is down.

## Why this fits Home Assistant

Push notifications fail exactly when you need them most: no data connection, phone on battery saver, app killed by the OS, or the internet at home being the very thing that broke. An SMS gets through.

Typical uses:

- Water leak, smoke or intrusion alerts
- Power outage detected by a UPS sensor
- Freezer temperature rising
- Someone at the door while you're away
- Home Assistant itself losing connection to a critical device

## Installation

### HACS (recommended)

1. In HACS, open the three-dot menu → **Custom repositories**
2. Add `https://github.com/narcisbodea/hass-smstunnel` with category **Integration**
3. Install **SMSTunnel**
4. Restart Home Assistant

### Manual

1. Copy the `custom_components/smstunnel` folder into your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant

## Configuration

1. Install the [SMSTunnel app from Google Play](https://play.google.com/store/apps/details?id=io.smstunnel.app) and pair your Android phone in it (scan the QR code)
2. In your SMSTunnel dashboard, create an API key with the `sms:send` permission
3. In Home Assistant: **Settings → Devices & Services → Add Integration → SMSTunnel**

| Field | Notes |
| --- | --- |
| **API key** | Validated during setup, so you find out immediately if it's wrong |
| **Recipients** | One or more numbers, comma separated |
| **Server URL** | `https://smstunnel.io` unless you self-host |
| **Default country code** | e.g. `+40`, so local numbers without a prefix still work |
| **Device ID** | Optional — pin sending to one specific phone |

## Usage

The integration creates a `notify.smstunnel` service.

```yaml
service: notify.smstunnel
data:
  message: "Water leak detected in the basement!"
```

### Override the recipient

```yaml
service: notify.smstunnel
data:
  message: "The alarm was triggered"
  target:
    - "+40712345678"
    - "+40787654321"
```

### Example automation

```yaml
automation:
  - alias: "SMS on water leak"
    trigger:
      - platform: state
        entity_id: binary_sensor.basement_water_leak
        to: "on"
    action:
      - service: notify.smstunnel
        data:
          title: "Home Assistant"
          message: "Water leak detected in the basement!"
```

A `title` is prepended to the message, since SMS has no separate title field.

## Good to know

- **Rate limit**: the API allows 30 requests per minute. If you hit it, the log says so explicitly rather than silently dropping the message.
- **Message length**: up to 1600 characters. Longer messages are truncated before sending, so a too-long message never fails validation outright.
- **One failure doesn't block the rest**: if sending to one recipient fails, the others still go out.
- **Automation loops**: be careful with triggers that can fire repeatedly (a flapping sensor). Add `for:` or a condition, otherwise you can burn through your quota — and your carrier's patience — in minutes.

## Responsible use

Built for **low-volume, transactional messaging** — alerts and notifications to yourself and your household. Sending unsolicited bulk messages from a consumer SIM generally breaches mobile carrier terms of service.

## Links

- [SMSTunnel](https://smstunnel.io)
- [Documentation](https://smstunnel.io/integrations/home-assistant)

## License

MIT
