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
4. Enter the Matter numeric setup code when requested, or press the Zigbee product pairing button.
5. Select **Start pairing**, keep the product near the gateway, and wait for it to appear.
6. Review the product in the portal before enabling its controls.

## Troubleshooting

If the gateway stays offline, confirm this app is running and check its **Log** tab. Verify internet access and correct date and time. If activation failed, create a new code in the portal, replace both activation values, save, and restart the app. Creating a new code revokes the previous gateway credential.

Do not share activation codes or logs containing credentials. Contact Ente Karyasthan support through https://entekaryasthan.com.
