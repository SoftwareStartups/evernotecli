export const SERVICE_HOST = 'www.evernote.com';
export const OAUTH_PORT = 10500;
export const CALLBACK_HOST = 'localhost';
export const CALLBACK_TIMEOUT = 300_000; // 5 minutes in ms

interface CallbackResult {
  fullUrl: string;
}

export function waitForCallback(): Promise<CallbackResult> {
  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => {
      server.stop();
      reject(new Error(`OAuth callback not received within ${CALLBACK_TIMEOUT / 1000}s`));
    }, CALLBACK_TIMEOUT);

    const server = Bun.serve({
      hostname: CALLBACK_HOST,
      port: OAUTH_PORT,
      fetch(req) {
        const url = new URL(req.url);
        if (!url.pathname.startsWith('/oauth_callback')) {
          return new Response('Not Found', { status: 404 });
        }

        clearTimeout(timeout);
        // Reconstruct the callback URL with query params
        const fullUrl = `http://${CALLBACK_HOST}:${OAUTH_PORT}${url.pathname}${url.search}`;
        resolve({ fullUrl });

        // Delay shutdown to ensure response is sent
        setTimeout(() => server.stop(), 100);

        return new Response(
          '<html><body>Authentication complete. You can close this tab.</body></html>',
          { headers: { 'Content-Type': 'text/html' } }
        );
      },
    });
  });
}
