# Digi Karyasthan Gateway for Home Assistant

Digi Karyasthan Gateway securely connects the smart products in your Home Assistant system to your Ente Karyasthan property. It uses an outbound encrypted connection. You do not need to open router ports or share Azure or Home Assistant credentials with the portal.

[![Add Digi Karyasthan to Home Assistant](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FVinuAmazn%2FDigi-Karyasthan-Gateway)

## Before you start

You need:

- Home Assistant OS or Home Assistant Supervised.
- Administrator access to Home Assistant.
- An Ente Karyasthan property with Digi Karyasthan Smart enabled.
- Internet access for Home Assistant.
- For Matter products: the Home Assistant Matter integration and compatible Matter or Thread hardware.
- For Zigbee products: ZHA and a compatible Zigbee coordinator.

Home Assistant Container does not have the Apps store. Ask Ente Karyasthan support to install the standalone gateway service for that installation type.

## Install and activate the gateway

1. Select **Add Digi Karyasthan to Home Assistant** above.
2. Choose your Home Assistant address when My Home Assistant opens.
3. Confirm **Add repository**. If nothing opens, use the manual repository steps below.
4. In Home Assistant, open **Settings → Apps → Install app**.
5. Find **Digi Karyasthan Gateway**, open it, and select **Install**.
6. In the Ente Karyasthan Smart portal, open your property and select **Create activation code**.
7. Keep that page open. The Gateway ID and activation code are shown only once, and the code expires after 24 hours.
8. In Home Assistant, open **Digi Karyasthan Gateway → Configuration**.
9. Paste the Gateway ID into `gateway_uuid` and the activation code into `claim_code`. Do not change `karyasthan_origin`.
10. Select **Save**.
11. Open the app's **Info** page. Enable **Start on boot** and **Watchdog**, then select **Start**.
12. Wait up to one minute, return to the Ente Karyasthan portal, and select **Refresh devices**. The gateway should show **Online**.

## Manual repository method

If the installation button does not open Home Assistant:

1. Open **Home Assistant → Settings → Apps → Install app**.
2. Open the three-dot menu and select **Repositories**.
3. Paste `https://github.com/VinuAmazn/Digi-Karyasthan-Gateway` and select **Add**.
4. Refresh the Apps page, find **Digi Karyasthan Gateway**, and continue from step 5 above.

## Add a smart product

1. For a new Matter product, commission it with the Home Assistant mobile app, then refresh devices in the Ente Karyasthan portal. No second pairing is needed.
2. To import a Matter product already connected to another controller, open that controller's sharing window and enter its fresh numeric sharing code in the portal. The gateway can join a product already on the local network; it cannot perform initial Bluetooth or Thread network setup.
3. For Zigbee, configure a compatible ZHA coordinator first, put the product into pairing mode, and choose **Add a product** in the portal.
4. For Wi-Fi, add a supported manufacturer integration in Home Assistant, then refresh devices in the portal.
5. Review the product's name and room before enabling control. New devices start with control disabled.

Cameras, doorbells, and locks require assisted setup and are excluded from automatic control.

## If the gateway stays offline

- Confirm the Digi Karyasthan Gateway app is running.
- Open its **Log** tab and check the latest message.
- Confirm Home Assistant has internet access and its date and time are correct.
- If the code is expired, already used, or entered incorrectly, create a new activation code in the portal and replace both values in the app configuration. Creating a new code revokes the previous gateway credential for that property.
- Restart the app and wait one minute.

Do not post Gateway IDs, activation codes, app logs containing credentials, or customer information in a public GitHub issue. Contact Ente Karyasthan support through https://entekaryasthan.com.
