# Installation

1. Install this repository in Home Assistant as a custom add-on repository.
2. Open **Digi Karyasthan Gateway** and choose **Install**.
3. In the Ente Karyasthan Smart portal, open the property and choose **Create activation code**.
4. Copy the Gateway ID and one-time activation code into the add-on Configuration page.
5. Start the add-on and enable **Start on boot** and **Watchdog**.
6. Return to Ente Karyasthan Smart. The gateway becomes online after its first heartbeat.

No Home Assistant token, local IP address, Azure key, or router port forwarding is required. Each gateway receives its own portal credential. Matter commissioning needs the Home Assistant Matter integration; Zigbee commissioning needs ZHA.

If activation fails, create a new code in the portal and replace the old code. Creating a new code revokes the previous gateway credential for that property.
