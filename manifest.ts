import { Manifest } from "deno-slack-sdk/mod.ts";

/**
 * The app manifest contains the app's configuration.
 * This file defines attributes like app name and description.
 * https://api.slack.com/automation/manifest
 */
const manifest = Manifest({
  name: "coffee-bot",
  description: "A blank template for building Slack apps with Deno",
  icon: "assets/default_new_app_icon.png",
  functions: [],
  workflows: [],
  outgoingDomains: [],
  botScopes: ["commands", "chat:write", "users:read", "chat:write.public", "channels:read"],
});

// Output the manifest as JSON
console.log(JSON.stringify(manifest, null, 2));
