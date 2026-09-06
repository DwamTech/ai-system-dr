# Browser tests

Run `node tests/e2e/browser_smoke.js` with the `playwright` Node package
available. Set `APP_URL` and `BROWSER_PATH` when the defaults do not match the
deployment. The test covers the seven tabs, page geometry, console/page errors,
and horizontal overflow at 1440, 768, 390, and 375 pixels.
