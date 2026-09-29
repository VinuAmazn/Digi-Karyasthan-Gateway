# Customer setup guide

## What you need

- Home Assistant OS or Home Assistant Supervised with administrator access.
- An Ente Karyasthan property with Digi Karyasthan Smart enabled.
- Internet access.
- Matter integration and compatible hardware for Matter products, or ZHA and a Zigbee coordinator for Zigbee products.

## Activate

1. In the Ente Karyasthan Smart portal, open the property and select **Create activation code**.
2. Keep the portal page open because the details are shown only once.
3. On this app's **Configuration** page, paste the displayed Gateway ID into `gateway_uuid` and the activation code into `claim_code`.
4. Leave `karyasthan_origin` unchanged and select **Save**.
5. On the **Info** page, enable **Start on boot** and **Watchdog**, then select **Start**.
6. Wait up to one minute. Return to Ente Karyasthan Smart and select **Refresh devices**. The gateway should show **Online**.

The activation code expires after 24 hours and works once. The app exchanges it for a private gateway credential stored inside Home Assistant. No Home Assistant token, local IP address, Azure key, or router port forwarding is required.

## Add products

1. Put the product into pairing mode.
2. In Ente Karyasthan Smart, select **Add a product**.
3. Choose the product type and connection method.
4. For a new Matter product, use the Home Assistant mobile app to commission it, then refresh devices in the portal; no second pairing is needed. To import a product already connected to another Matter controller, open that controller's sharing window and enter its fresh numeric sharing code in the portal. The gateway joins a product already on the local network; it does not perform Bluetooth or Thread network setup. For Zigbee, a supported ZHA coordinator must already be configured. For Wi-Fi, add the manufacturer's supported integration in Home Assistant first.
5. For a shared Matter code or Zigbee product, select **Start pairing** and wait for it to appear. For a newly commissioned Matter or integrated Wi-Fi product, select **Refresh devices** instead.
6. Review the product in the portal before enabling its controls.

## Troubleshooting

If the gateway stays offline, confirm this app is running and check its **Log** tab. Verify internet access and correct date and time. If activation failed, create a new code in the portal, replace both activation values, save, and restart the app. Creating a new code revokes the previous gateway credential.

Do not share activation codes or logs containing credentials. Contact Ente Karyasthan support through https://entekaryasthan.com.

## Update to 1.2.0

Refresh the app store repository, open Digi Karyasthan Gateway, and select Update. Existing per-gateway credentials are retained. Confirm the portal gateway version and a recent device reading before testing one approved low-risk device while at the property.

The current portal supports Celsius thermostat setpoints from 16–32 °C. Fahrenheit thermostats remain read-only. Locks, pumps, garage doors, cameras and unsupported device types need a separate commissioned adapter. Discovery is limited to 100 entities per snapshot; a larger installation reports a warning and needs a commissioned entity list. Initial Matter/Thread commissioning, Zigbee radio compatibility and physical actuation require on-site verification.
