# SMSTunnel for Home Assistant

Send SMS from Home Assistant through **your own Android phone**, using **your own SIM card**.

<a href="https://play.google.com/store/apps/details?id=io.smstunnel.app"><img src="https://smstunnel.io/google-play-badge.png" alt="Get it on Google Play" height="56"></a>

No per-message fees and no SMS provider in between: the phone you already own sends the texts, from your number. And a text reaches the person you alert even when their phone has no mobile data and no app.

## Why this fits Home Assistant

Push notifications can fail when you need them most: no data connection, battery saver, an app the phone's system has closed. A text needs none of that on the receiving phone. Home Assistant and the phone that sends still need to reach SMSTunnel over the internet.

Typical uses:

- Water leak, smoke or intrusion alerts
- Power outage detected by a UPS sensor
- Freezer temperature rising
- Someone at the door while you're away
- Home Assistant itself losing connection to a critical device

## Installation

### HACS (recommended)

SMSTunnel is in the HACS default list, so there is no custom repository to add.

1. Open HACS and search for **SMSTunnel**
2. Open it and click **Download**
3. Restart Home Assistant

[![Open your Home Assistant instance and open this repository in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=narcisbodea&repository=hass-smstunnel&category=integration)

### Manual

1. Copy the `custom_components/smstunnel` folder into your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant

## Configuration

1. Install the [SMSTunnel app from Google Play](https://play.google.com/store/apps/details?id=io.smstunnel.app) on your Android phone and sign in with your SMSTunnel account
2. In your [SMSTunnel dashboard](https://dashboard.smstunnel.io/apps), open **Apps** → **Add an app**, choose **Home Assistant** and copy its key
3. In Home Assistant: **Settings → Devices & Services → Add Integration → SMSTunnel**

| Field | Notes |
| --- | --- |
| **API key** | Validated during setup, so you find out immediately if it's wrong |
| **Recipients** | One or more numbers, comma separated |
| **Server URL** | `https://smstunnel.io` unless you self-host |
| **Default country code** | e.g. `+40`, so local numbers without a prefix still work |
| **Device ID** | Optional — pin sending to one specific phone |

### Change the settings later

**Settings → Devices & Services → SMSTunnel → ⋮ → Reconfigure** opens the same fields with their current values. Change the recipients, the phone or the server and save: `notify.smstunnel` uses the new settings at once, with no restart. Leave the API key empty to keep the current one. The key is checked again before anything is saved.

This needs Home Assistant 2024.4 or newer. On an older version, remove the integration and add it again.

If you added SMSTunnel more than once, the menu asks you to remove the extra entries first: they all share the one action, and only one of them answers it.

## Usage

The integration adds the action `notify.smstunnel` (YAML written before Home Assistant 2024.8 calls it `service:`; both work).

```yaml
action: notify.smstunnel
data:
  message: "Water leak detected in the basement!"
```

### Override the recipient

```yaml
action: notify.smstunnel
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
    triggers:
      - trigger: state
        entity_id: binary_sensor.basement_water_leak
        to: "on"
    actions:
      - action: notify.smstunnel
        data:
          title: "Home Assistant"
          message: "Water leak detected in the basement!"
```

A `title` is prepended to the message, since SMS has no separate title field.

## Good to know

- **Rate limit**: the API allows 30 texts a minute per API key. If you hit it, the log says so explicitly rather than silently dropping the message.
- **Message length**: up to 1600 characters. Longer messages are truncated before sending, so a too-long message never fails validation outright.
- **One failure doesn't block the rest**: if sending to one recipient fails, the others still go out.
- **Add it once**: every SMSTunnel entry shares the one action `notify.smstunnel`, and only one entry answers it. To text different people from different automations, use `target`.
- **Automation loops**: be careful with triggers that can fire repeatedly (a flapping sensor). Add `for:` or a condition, otherwise you can burn through your quota — and your carrier's patience — in minutes.

## Build it with an AI assistant

Paste this into Claude, ChatGPT, Cursor or Copilot and replace the part in brackets. Don't paste your API key into the chat: the prompt doesn't need it.

```text
Help me write Home Assistant automations (YAML) that send text messages from my own phone with
SMSTunnel.

About SMSTunnel (https://smstunnel.io): my own apps and tools hand text messages (SMS) to my
SMSTunnel account, and my own Android phone sends them from my own number, on my own SIM and plan.
The phone runs the SMSTunnel app from Google Play
(https://play.google.com/store/apps/details?id=io.smstunnel.app), signed in to my account.

What I want: [describe what should send a text, to whom, and when]

How it works:
- Install the SMSTunnel integration with HACS, where it is in the default list: HACS → search for
  SMSTunnel → Download → restart Home Assistant. Or copy custom_components/smstunnel from
  https://github.com/narcisbodea/hass-smstunnel into config/custom_components/ and restart.
- Settings → Devices & Services → Add Integration → SMSTunnel: "API key", "Recipients (comma
  separated)", "Server URL" (https://smstunnel.io), "Default country code", "Device ID (optional)".
  The key is checked during setup. To change the settings later: SMSTunnel's menu on that page →
  Reconfigure (Home Assistant 2024.4 or newer; an empty key field keeps the current key).
- Action notify.smstunnel ("action:" in YAML; "service:" before Home Assistant 2024.8): message
  (required), title (the text becomes "title: message"), target (a number or a list; replaces the
  configured recipients for that call), and data: device_id or default_country_code for one call.
  Each recipient gets its own text.
- Texts over 1600 characters are cut. SMSTunnel allows 30 send requests a minute; past that the text
  is not sent and the log says so (no retry). Errors are written to the log, not raised to the
  automation. If my phone is offline, the text waits and goes out when it is back.
- The API key comes from my SMSTunnel dashboard (https://dashboard.smstunnel.io): Apps → Add an app
  → Create the key. It is shown only once and can send texts and check whether they went out.

Rules for your answer:
- Do not ask for my SMSTunnel password or API key and do not put a real key in your answer; I will
  not paste it in this chat.
- Phone numbers must be in international format (+ and the country code).
- Help me test it with my own number first.
- Only send texts people expect from me. No unsolicited texts.
- Help me avoid repeated texts from a sensor that flips on and off (for:, conditions, a cooldown).
```

## Responsible use

Built for **low-volume, transactional messaging** — alerts and notifications to yourself and your household. Unsolicited texts from a personal SIM break most mobile carriers' terms of service.

## Links

- [SMSTunnel](https://smstunnel.io)
- [Documentation](https://smstunnel.io/integrations/home-assistant)

## Changelog

- **1.1.0**: change the recipients, the phone, the server or the API key from the integration's **Reconfigure** menu, without removing it. Nothing else changes: `notify.smstunnel` sends exactly as before.
- **1.0.2**: passes the HACS and hassfest checks, and the README says plainly what still needs an internet connection.
- **1.0.1**: the API key is typed into a password field, removing the integration stops `notify.smstunnel` at once (no restart), and SMSTunnel's icon shows in Home Assistant.
- **1.0.0**: first release.

## License

MIT
