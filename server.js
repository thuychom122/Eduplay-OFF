/**
 * Root proxy for Northflank deployment
 * The Northflank service runs `node server.js` from /workspace,
 * but the actual gateway is in northflank_ai_gateway/server.js
 * This file forwards to the real gateway and ensures correct startup.
 */
const path = require('path');
const gatewayPath = path.join(__dirname, 'northflank_ai_gateway', 'server.js');

try {
  // Try to load the gateway and start it if this is the main module
  const gateway = require(gatewayPath);
  if (require.main === module) {
    // If gateway exports startServer, call it
    if (gateway && typeof gateway.startServer === 'function') {
      gateway.startServer().catch((err) => {
        console.error('Failed to start gateway via root proxy', err);
        process.exit(1);
      });
    } else if (typeof gateway === 'function') {
      // Fallback
      gateway();
    }
  }
  module.exports = gateway;
} catch (err) {
  console.error('Root server.js failed to load gateway at', gatewayPath, err);
  throw err;
}
