# Digi Karyasthan Gateway

This app runs automatically and connects Home Assistant to the customer's Ente Karyasthan property using outbound HTTPS. It obtains Home Assistant access from the Supervisor and never asks the customer for an IP address, endpoint or Home Assistant token.

The gateway ID and one-time claim code are provisioned with the property gateway. On first start, the code is exchanged for a unique gateway token and becomes unusable. Matter, Zigbee and local Wi-Fi pairing requests then originate from the Ente Karyasthan portal.
