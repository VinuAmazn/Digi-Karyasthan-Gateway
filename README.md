# Digi Karyasthan Gateway for Home Assistant

This repository installs the Digi Karyasthan Gateway app on Home Assistant OS or Home Assistant Supervised. It connects Home Assistant to the customer's Ente Karyasthan property through outbound HTTPS. No router port, Azure credential, Home Assistant address, or Home Assistant access token is entered in the Ente Karyasthan portal.

[![Add the Digi Karyasthan repository to Home Assistant](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FVinuAmazn%2FDigi-Karyasthan-Gateway)

## Customer installation

1. In Home Assistant, open **Settings → Apps → Install app**.
2. Open the three-dot menu, choose **Repositories**, and add `https://github.com/VinuAmazn/Digi-Karyasthan-Gateway`.
3. Open **Digi Karyasthan Gateway** and choose **Install**.
4. In the Ente Karyasthan Smart portal, choose **Create activation code** for the property.
5. In the app configuration, enter the displayed Gateway ID and one-time activation code.
6. Enable **Start on boot** and **Watchdog**, then choose **Start**.
7. Return to Ente Karyasthan Smart. The gateway should report online within one minute.

The activation code expires after 24 hours and can be used once. Creating another code revokes the previous gateway credential for that property.

## Supported installations

The app requires Home Assistant OS or Home Assistant Supervised because it uses the Supervisor API. Home Assistant Container users should use the standalone Digi Karyasthan Linux gateway package.

Matter pairing requires the Home Assistant Matter integration and compatible Matter radio/network support. Zigbee pairing requires ZHA and a compatible Zigbee coordinator. Manufacturer-cloud-only products require a supported vendor integration.

## Privacy and control

The gateway reports supported device state to the customer's Ente Karyasthan property. Newly discovered devices remain disabled for control until the customer reviews and enables them. Cameras, doorbells, and locks are excluded from automatic control.

Support: https://entekaryasthan.com
